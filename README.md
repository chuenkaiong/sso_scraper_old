# SSO Scraper
## Description
Scraper for legislation from [sso.agc.gov.sg](sso.agc.gov.sg).

## Requirements 
Package requirements:
* scrapy
* requests

## TODOs
### Passing arguments
Find a better way to pass arguments into scrapy. 
Right now you have to pass in with the -a flag, (e.g. `scrapy crawl sso -a sl=True`) which is a bit cumbersome.  
See if there is a way to do something more like `scrapy crawl sso -sl -pdf`.

### Save PDF 
Current default is .html
Consider further dividing the /data folder into /pdf and /html 

### Date filtering 
* Where retrieving all legislation – only legislation in force at the time should be returned, AND each piece of legislation should be the version in force at that date.
* Where retrieving single legislation by shorthand – legislation returned should be the version in force at that date.

### Inconsistent Lazyload usage
Some pieces of legislation (particularly those that are shorter) are returned directly through the main html document instead of being retrieved through lazyload. 
* To figure out any indicators on the html page that this is the case, and in such instances grab the main body by the correct selectors and skip the download_part() and stitch_parts() functions. 