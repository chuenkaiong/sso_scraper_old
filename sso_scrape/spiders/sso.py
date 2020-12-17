import scrapy
import datetime
import requests
from sso_scrape.items import legisItem

class SsoSpider(scrapy.Spider):
  name = 'sso'
  allowed_domains = ['sso.agc.gov.sg']
  start_urls = ['https://sso.agc.gov.sg/Browse/Act/Current']

  def __init__(self, retrieve="ALL", sl=False, date=datetime.date.today().strftime("%Y%m%d"), pdf=False, saveTo="./"):
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
      acts = response.xpath("//table[@class='table browse-list']/tbody/tr")
      
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
      item["link"] = link
      
      if self.pdf:
        pdf_link = response.xpath("//a[@class='file-download']/@href").get()
        item["pdf"] = f"https://sso.agc.gov.sg{pdf_link}" if pdf_link else None

      if self.include_subsid:
        subsid_link = response.xpath("//ul[@class='dropdown-menu dropdown-menu-right']/li/a/@href").get()
        item["subsid"] = f"https://sso.agc.gov.sg{subsid_link}" if subsid_link else None

      item["content"] = self.get_body(response)
      yield item

  def scrape_all(self, response):   # create item for each piece of legislation, for further parsing 
    acts =  response.xpath("//table[@class='table browse-list']/tbody/tr")
    for act in acts:
      item = legisItem()
      item["title"] = act.xpath(".//td[1]/a[@class='non-ajax']/text()").get()
      link = f"https://sso.agc.gov.sg{act.xpath('.//a/@href').get()}"
      item["link"] = link

      # if options are set 
      if self.pdf:
        pdf_link = act.xpath("./td/a[@class='non-ajax file-download']/@href").get()
        item["pdf"] = f"https://sso.agc.gov.sg{pdf_link}" if pdf_link else None

      if self.include_subsid:
        subsid_link = act.xpath("./td/a[@class='non-ajax sl']/@href").get()
        item["subsid"] = f"https://sso.agc.gov.sg{subsid_link}" if subsid_link else None

      yield item 

  def scrape_one(self, response):   # Handles individual responses when crawling URLs from the /All page
    item = response.meta["item"]
    item["content"] = self.get_body(response)
    yield item
  
  def get_body(self, response):   # function to grab the relevant parts from a given response
    return "PLACEHOLDER PLACEHOLDER PLACEHOLDER PLACEHOLDER PLACEHOLDER"

