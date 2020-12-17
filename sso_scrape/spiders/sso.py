import scrapy
import datetime
import requests
import json 
from sso_scrape.items import legisItem

class SsoSpider(scrapy.Spider):
  name = 'sso'
  allowed_domains = ['sso.agc.gov.sg']
  start_urls = ['https://sso.agc.gov.sg/Browse/Act/Current']

  def __init__(self, retrieve="ALL", sl=False, date=datetime.date.today().strftime("%Y%m%d"), pdf=False, saveTo="./data"):
    self.retrieve = retrieve
    self.include_subsid = sl
    self.date = date
    self.pdf = pdf
    self.saveTo = saveTo

  def start_requests(self):
    if self.retrieve == "ALL":
      url = 'https://sso.agc.gov.sg/Browse/Act/Current/All?PageSize=500&SortBy=Title&SortOrder=ASC'
      # TODO: handle date by inserting into url here

    else:   # if the user has specified a particular piece of legislation based on 
      url = f"https://sso.agc.gov.sg/Act/{self.retrieve}"
      # TODO: handle date here too 
      # note on error handling: scrapy automatically skips scraping if the server returns 404, so we don't need to handle that situation for now
    
    yield scrapy.http.request.Request(url, self.parse)



  def parse(self, response):
    if self.retrieve == "ALL":
      yield from self.scrape_all(response)

      # navigate to next page
      relative_url = response.xpath("//a[@aria-label='Next Page']/@href").get()
      next_page = response.urljoin(relative_url)
      if next_page:
        yield scrapy.Request(url=next_page, callback=self.parse)
    

    else:   # if user has requested legislation by shorthand instead of all 
      item = legisItem()
      link = f"https://sso.agc.gov.sg/Act/{self.retrieve}"
      item["title"] = response.xpath("//div[@class='legis-title']/div/text()").get()
      item["shorthand"] = self.retrieve
      item["link"] = link
      
      if self.pdf:
        pdf_link = response.xpath("//a[@class='file-download']/@href").get()
        item["pdf"] = f"https://sso.agc.gov.sg{pdf_link}" if pdf_link else None

      if self.include_subsid:
        subsid_link = response.xpath("//ul[@class='dropdown-menu dropdown-menu-right']/li/a/@href").get()
        item["subsid"] = f"https://sso.agc.gov.sg{subsid_link}" if subsid_link else None

      item["html"] = self.get_body(response)

      self.write_to_file(self.saveTo, item)
      yield item

  def scrape_all(self, response):   # create item for each piece of legislation, for further parsing 
    acts =  response.xpath("//table[@class='table browse-list']/tbody/tr")

    # FOR TESTING PURPOSES - REMOVE WHEN DONE
    acts = acts[:3]
    # FOR TESTING PURPOSES

    for act in acts:
      item = legisItem()
      item["title"] = act.xpath(".//td[1]/a[@class='non-ajax']/text()").get()
      link = f"https://sso.agc.gov.sg{act.xpath('.//a/@href').get()}"
      item["shorthand"] = link.split("/")[-1]
      item["link"] = link

      # if options are set 
      if self.pdf:
        pdf_link = act.xpath("./td/a[@class='non-ajax file-download']/@href").get()
        item["pdf"] = f"https://sso.agc.gov.sg{pdf_link}" if pdf_link else None

      if self.include_subsid:
        subsid_link = act.xpath("./td/a[@class='non-ajax sl']/@href").get()
        item["subsid"] = f"https://sso.agc.gov.sg{subsid_link}" if subsid_link else None

      request = scrapy.Request(url=link, callback=self.scrape_one)
      request.meta["item"] = item
      yield request

  def scrape_one(self, response):   # Handles individual responses when crawling URLs from the /All page
    item = response.meta["item"]
    item["html"] = self.get_body(response)
    self.write_to_file(self.saveTo, item)
    yield item
  
  def get_body(self, response):   # function to grab the relevant parts from a given response
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:62.0) Gecko/20100101 Firefox/62.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }

    data = json.loads(response.xpath("//div[@class='global-vars']/@data-json")[1].get())
    toc_sys_id = data["tocSysId"]
    series_ids = [div.attrib["data-term"] for div in response.xpath("//div[@class='dms']")]

    parts = []

    for series_id in series_ids:
      frag_sys_id = data["fragments"][series_id]["Item1"]
      dt_id = data["fragments"][series_id]["Item2"]
      url = "https://sso.agc.gov.sg/Details/GetLazyLoadContent?TocSysId={}&SeriesId={}".format(toc_sys_id, series_id) + \
        "&ValidTime=&TransactionTime=&ViewType=&V=25&Phrase=&Exact=&Any=&Without=&WiAl=&WiPr=&WiLT=&WiSc=" + \
        "&WiDT=&WiDH=&WiES=&WiPH=&RefinePhrase=&RefineWithin=&CustomSearchId=&FragSysId={}&_={}".format(frag_sys_id, dt_id)
      
      parts.append(download_part(url, headers))
    
    return stitch_parts(parts)

  def write_to_file(self, saveTo, item):
    with open(f"{saveTo}/{item['shorthand']}.html", "w") as f:
      f.write(item["html"])

# Not sure whether to put these inside the spider definition or leave them out here 
def download_part(url, headers):
    r = requests.get(url, headers=headers)
    if r.status_code != requests.status_codes.codes.ok:
        print('URL not found: ' + url)
        return ''
    return r.text

def stitch_parts(parts):
    first, *remaining = parts
    insert_idx = first.find('<div class="dms"')
    return first[:insert_idx] + ''.join(remaining) + first[insert_idx:]