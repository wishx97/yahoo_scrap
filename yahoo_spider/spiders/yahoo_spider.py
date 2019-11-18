import re
import scrapy
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError
from twisted.internet.error import TimeoutError, TCPTimedOutError

from yahoo_spider.items import Product

class YahooSpider(scrapy.Spider):
    name = "yahoo"
    start_urls = [
        'https://tw.buy.yahoo.com/category/4387479',
    ]

    def __init__(self):
        self.base_url = 'https://tw.buy.yahoo.com/amp/item/'

    def errback_httpbin(self, failure):
        # log all failures
        self.logger.error(repr(failure))

        # in case you want to do something special for some errors,
        # you may need the failure's type:

        if failure.check(HttpError):
            # these exceptions come from HttpError spider middleware
            # you can get the non-200 response
            response = failure.value.response
            self.logger.error('HttpError on %s', response.url)

        elif failure.check(DNSLookupError):
            # this is the original request
            request = failure.request
            self.logger.error('DNSLookupError on %s', request.url)

        elif failure.check(TimeoutError, TCPTimedOutError):
            request = failure.request
            self.logger.error('TimeoutError on %s', request.url)


    def parse(self, response):
        tv_url = response.xpath("//a[@data-vars-category-id = '4387481']/@href").extract_first()
        phone_url = response.xpath("//a[@data-vars-category-id = '4385981']/@href").extract_first()
        for url in [tv_url, phone_url]:
            for page_id in range(1, 6):
                request = scrapy.Request('{}?pg={}'.format(url, page_id), callback=self.parse_product_list, errback=self.errback_httpbin)
                yield request
        
    def parse_product_list(self, response):
        products = response.xpath("//li[contains(@class,'BaseGridItem__multipleImage')]/a[contains(@class,'hover')]/@href")
        for product in products:
            product_url = product.extract()
            product_id = re.search(r'(.*-)?(.*).html', product_url).group(2)
            request = scrapy.Request(product_url, callback=self.parse_normal, meta={'product_url': self.base_url + product_id}, errback=self.errback_httpbin)
            yield request

    def parse_amp(self, response):
        product = response.meta['product']
        #title = response.xpath("//div/h1/text()").extract_first()
        img_url = response.xpath("//amp-carousel/amp-img/@src").extract() 
        spec = response.xpath("//div[@class = 'spec']//tr//text()").extract()
        spec = ['{}: {}'.format(x, y) for x, y in zip(spec[0::2], spec[1::2])]
        try:
            product['category'] = response.xpath("//div[@id = 'iCategory']//a/text()")[2].extract()
        except:
            self.logger.error('Error for selector %s', response.xpath("//div[@id = 'iCategory']").extract())
        product['img_url'] = img_url
        product['spec'] = spec
        yield product
        

    def parse_normal(self, response):
        product = Product()
        product_url = response.meta['product_url']
        title = response.xpath("//h1[contains(@class, 'title')]/text()").extract_first()
        feature = response.xpath("//div[contains(@class, 'ShoppingProductFeatures__productFeatureWrapper')]/ul//li/text()").extract()
        
        product['title'] = title
        #product['category'] = category
        product['feature'] = feature
        request = scrapy.Request(product_url, callback=self.parse_amp, meta={'product': product})
        yield request
        
    