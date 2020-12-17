import scrapy
import datetime
from sso_scrape.items import legisItem

class SsoSpider(scrapy.Spider):
  name = 'sso'
  allowed_domains = ['sso.agc.gov.sg']
  start_urls = ['https://sso.agc.gov.sg/Browse/Act/Current']

  def __init__(self, retrieve="ALL", sl=False, date=datetime.date.today().strftime("%Y%m%d"), pdf=False):
    self.retrieve = retrieve
    self.include_subsid = sl
    self.date = date
    self.pdf = pdf

  def start_requests(self):
    if self.retrieve == "ALL":
      url = 'https://sso.agc.gov.sg/Browse/Act/Current/All?PageSize=500?SortBy=Title&SordOrder=ASC'
      # TODO: handle date by inserting into url here

    else:   # if the user has specified a particular piece of legislation based on 
      url = f"https://sso.agc.gov.sg/Act/{self.retrieve}"
      
      # note on error handling: scrapy automatically skips scraping if the server returns 404, so we don't need to handle that situation for now
    
    yield scrapy.http.request.Request(url, self.parse)



  def parse(self, response):
    if self.retrieve == "ALL":
      acts = response.xpath("//table[@class='table browse-list']/tbody/tr")
      
      for act in acts:
        yield from self.scrape_all(response)


      # navigate to next page
      relative_url = response.xpath("//a[@aria-label='Next Page']/@href").get()
      next_page = response.urljoin(relative_url)
      if next_page:
        yield scrapy.Request(url=next_page, callback=self.parse)
    

    else:   # if user has requested legislation by shorthand instead of all 
      item = legisItem()
      item["title"] = response.xpath("//div[@class='legis-title']/div/text()").get()
      
      if self.pdf:
        pdf_link = response.xpath("//a[@class='file-download']/@href").get()
        item["pdf"] = f"https://sso.agc.gov.sg{pdf_link}" if pdf_link else None

      if self.include_subsid:
        subsid_link = response.xpath("//ul[@class='dropdown-menu dropdown-menu-right']/li/a/@href").get()
        item["subsid"] = f"https://sso.agc.gov.sg{subsid_link}" if subsid_link else None
      
      yield item


  def scrape_all(self, response):   # create item for each piece of legislation, for further parsing 
    acts =  response.xpath("//table[@class='table browse-list']/tbody/tr")
    for act in acts:
      item = legisItem()
      item["title"] = act.xpath(".//td[1]/a[@class='non-ajax']/text()").get()
      item["link"] = f"https://sso.agc.gov.sg{act.xpath('//tbody/tr/td/a/@href').get()}"

      # if options are set 
      if self.pdf:
        pdf_link = act.xpath("./td/a[@class='non-ajax file-download']/@href").get()
        item["pdf"] = f"https://sso.agc.gov.sg{pdf_link}" if pdf_link else None

      if self.include_subsid:
        subsid_link = act.xpath("./td/a[@class='non-ajax sl']/@href").get()
        item["subsid"] = f"https://sso.agc.gov.sg{subsid_link}" if subsid_link else None

      yield item 

def get_body(self, response):
  # We call this function for each piece of legislation, this should scrape the html from
    # refer to prof's sso notebook for some idea on how the page works - in addition to scraping
    # the raw html, we have to make some requests according to the toc_sys_id and series_id etc. to get the full legislation. 

  # TODO: fill in this function and ensure that it is called properly from either scrape_all (in the case where we're scraping all legislation)
    #   or from parse() (in the case where the user wants a single piece of legislation)
  return 
