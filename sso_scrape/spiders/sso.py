import scrapy
from scrapy.exceptions import CloseSpider
import datetime
import requests
import json 
from sso_scrape.items import legisItem, subsidItem
from ..lib import filemgr


# Scrapy spider that retrieves either a single Act or all Acts from a contents page and downloads them into a specified folder. 
# If the user requests all Acts, the response is passed to scrape_all(), which subsequently calls scrape_one() to retrieve the content of the Act.
# If the user requests a specific Act, the content of the Act is directly retrieved and written to file. 



class SsoSpider(scrapy.Spider):
  name = 'sso'
  allowed_domains = ['sso.agc.gov.sg']

  def __init__(self, retrieve="ALL", sl=False, date=datetime.date.today().strftime("%Y%m%d"), pdf=False, saveTo="./data"):
    self.retrieve = retrieve
    self.include_subsid = sl
    self.date = date
    self.pdf = pdf
    self.saveTo = saveTo                # folder name with no slash at the back, e.g. "./data"

  # Scrapy function that defines where the first HTTP request is sent
  def start_requests(self):
    # check user-defined save location 
    if not filemgr.check_save_location(self.saveTo):
      raise CloseSpider("User abort")

    if self.retrieve == "ALL":
      # if user does not specify which Act to retrieve, start from the contents page.
      # TODO: handle date 
      url = 'https://sso.agc.gov.sg/Browse/Act/Current/All?PageSize=500&SortBy=Title&SortOrder=ASC'

    else:   
      # if the user has specified a particular Act based on shorthand, start directly at the specified Act.
      # TODO: handle date 
      url = f"https://sso.agc.gov.sg/Act/{self.retrieve}"
      
      # note on error handling: scrapy automatically skips scraping if the server returns 404, so we don't need to handle that situation for now
    
    yield scrapy.http.request.Request(url, self.parse)

  # This parses the initial http response. It is broken up into two main blocks, depending on whether the user requests all Acts or a specific Act.
  def parse(self, response):
    # If all Acts are requested, pass the response to scrape_all() to scrape the links to each Act from the contents page
    # TODO: I think the code from scrape_all can be moved here without a problem but this may be better for readability
    if self.retrieve == "ALL":
      yield from self.scrape_all(response)

      # navigate to next page of legislation table of contents
      relative_url = response.xpath("//a[@aria-label='Next Page']/@href").get()
      next_page = response.urljoin(relative_url)
      if next_page:
        yield scrapy.Request(url=next_page, callback=self.parse)
    
    # if user has requested specific Act by shorthand, generate the legisItem directly
    else:   
      item = legisItem()
      link = f"https://sso.agc.gov.sg/Act/{self.retrieve}"
      item["title"] = response.xpath("//div[@class='legis-title']/div/text()").get()
      item["shorthand"] = self.retrieve
      item["link"] = link
      
      #finds pdf link
      pdf_link = response.xpath("//div[@class='legis-title']/a/@href").get()
      if pdf_link:
        item["pdf"] = 'Yes'
      else:
        item['pdf'] = 'No'

      # grab the desired html and put it in the html attribute of the legisItem (TODO - handle situation where self.pdf == True)
      item["html"] = self.get_body(response)

      # write to file in folder (defined in CLI argument)
      self.write_to_file(self.saveTo, item)

      if self.include_subsid:
        subsid_link = f"https://sso.agc.gov.sg/Act/{self.retrieve}?DocType=Act&ViewType=Sl&PageIndex=0&PageSize=500"
        yield scrapy.Request(url=subsid_link, meta= item, callback = self.parse_subsid)

      yield item

  def parse_subsid(self, response):
    all_subsid = response.xpath("//table[@class='table browse-list']/tbody/tr")
    for sub in all_subsid:
      item = subsidItem()
      item["short_title"] = sub.xpath("td/a/text()").get()
      item["order_number"] = sub.xpath("td/text()")[3].get().strip().replace("/", "-")    # no idea why it's 3
      item["shorthand"] = item["short_title"] + " " + item["order_number"]
      item["link"] = sub.xpath("td/a/@href").get()
    
      request = scrapy.Request(response.urljoin(item["link"]), self.get_subsid)
      request.meta["subsidItem"] = item
      yield request
  
  def get_subsid(self, response):
    item = response.meta["subsidItem"]
    item["html"] = response.xpath("//*[@id='legis']").get()
    # TODO - ^ get data more cleanly without all the headers (figure out selectors) 
    self.write_to_file(self.saveTo, item)
    yield item
    

  # Scrape links to individual Acts from contents page, creating a legisItem for each. 
  # Then pass each legisItem to scrape_one() to obtain their contents
  def scrape_all(self, response):   
    acts =  response.xpath("//table[@class='table browse-list']/tbody/tr")

    # FOR TESTING PURPOSES - to shorten testing process. Remove when finished with testing. 
    acts = acts[:5]

    # Create legisItem for each link to an Act in the response, set attributes of legisItem. 
    for act in acts:
      item = legisItem()
      item["title"] = act.xpath(".//td[1]/a[@class='non-ajax']/text()").get()
      link = f"https://sso.agc.gov.sg{act.xpath('.//a/@href').get()}"     # link to the specific Act
      item["shorthand"] = link.split("/")[-1]
      item["link"] = link

      #finds pdf link - not working in for loop
      pdf_link = act.xpath("//div[@class='legis-title']/a/@href").get()
      if pdf_link:
        item["pdf"] = 'Yes'
      
      #finds subsid link - not working in for loop
      subsid_link = act.xpath("//ul[@class='nav nav-pills float-start']/li/a/@href").get()
      if subsid_link:
        subsid_link = act.xpath("//ul[@class='nav nav-pills float-start']/li/a/@href")[0].get()
        if subsid_link != '#':        
          item["subsid"] = f"https://sso.agc.gov.sg{subsid_link}"
        else:
          subsid_link = act.xpath("//ul[@class='nav nav-pills float-start']/li/a/@href")[1].get()
          item["subsid"] = f"https://sso.agc.gov.sg{subsid_link}"

      # pass each legisItem to scrape_one() to write the contents of the Act to a file
      request = scrapy.Request(url=link, callback=self.scrape_one)
      request.meta["item"] = item
      yield request


  # Handles response from page of a given Act. Fills in the html attribute of the relevant legisItem and writes the contents to file.
  # Yields the items so scrapy knows we're done
  def scrape_one(self, response):   
    item = response.meta["item"]
    item["html"] = self.get_body(response)
    self.write_to_file(self.saveTo, item)
    yield item


  # Grabs the relevant parts from a given response.
  # For pages that use lazyload, takes the data and makes HTTP calls to get the information, then stitches the retrieved parts together. 
  # TODO: pages that directly include the content of the Act. 
  def get_body(self, response):   
    # TODO: Change the headers here before completion! 
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:62.0) Gecko/20100101 Firefox/62.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }  

    # Gets non-lazy loaded content
    data = response.xpath("//div[@class='prov1']").extract()
    non_lazy_load =''
    for i in data:
      non_lazy_load += i
    # Get the parameters with which to request lazyload content
    data = json.loads(response.xpath("//div[@class='global-vars']/@data-json")[1].get())
    toc_sys_id = data["tocSysId"]
    series_ids = [div.attrib["data-term"] for div in response.xpath("//div[@class='dms']")]

    parts = [non_lazy_load]

    # Request content in parts
    for series_id in series_ids:
      frag_sys_id = data["fragments"][series_id]["Item1"]
      dt_id = data["fragments"][series_id]["Item2"]
      url = "https://sso.agc.gov.sg/Details/GetLazyLoadContent?TocSysId={}&SeriesId={}".format(toc_sys_id, series_id) + \
        "&ValidTime=&TransactionTime=&ViewType=&V=25&Phrase=&Exact=&Any=&Without=&WiAl=&WiPr=&WiLT=&WiSc=" + \
        "&WiDT=&WiDH=&WiES=&WiPH=&RefinePhrase=&RefineWithin=&CustomSearchId=&FragSysId={}&_={}".format(frag_sys_id, dt_id)
      
      parts.append(download_part(url, headers))
    
    return stitch_parts(parts)

  # write contents of Act to file
  def write_to_file(self, saveTo, item):
    with open(f"{saveTo}/{item['shorthand']}.html", "w") as f:
      #prints subsid link at the top of .html file
      if 'subsid' in item:
        f.write(f"Subsidiary Legislation Link: {item['subsid']}")
      #handles unicode encode error
      f.write(item["html"].encode('ascii', errors='ignore').decode('unicode-escape'))

# Downloads additional HTML parts
# (Not sure whether to put these inside the spider definition or leave them out here)
def download_part(url, headers):
    r = requests.get(url, headers=headers)
    if r.status_code != requests.status_codes.codes.ok:
        print('URL not found: ' + url)
        return ''
    return r.text

# Takes a list of HTML parts and joins them into a single string
def stitch_parts(parts):
    first, *remaining = parts
    insert_idx = first.find('<div class="dms"')
    return first[:insert_idx] + ''.join(remaining) + first[insert_idx:]

