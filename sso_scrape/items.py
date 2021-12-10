# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class legisItem(scrapy.Item):
  title = scrapy.Field()
  shorthand = scrapy.Field()
  link = scrapy.Field()
  html = scrapy.Field()
  pdf = scrapy.Field()
  subsid = scrapy.Field()

class subsidItem(scrapy.Item):
  short_title = scrapy.Field()
  order_number = scrapy.Field()
  shorthand = scrapy.Field()
  link = scrapy.Field()
  html = scrapy.Field()