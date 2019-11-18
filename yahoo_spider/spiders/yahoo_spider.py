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
        self.base_category = 'Yahoo 購物'

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
        '''
            Parse product under 2 group.
            
            1. TV 
            2. Phone 
        '''
        tv_url = response.xpath("//a[@data-vars-category-id = '4387481']/@href").extract_first()
        phone_url = response.xpath("//a[@data-vars-category-id = '4385981']/@href").extract_first()

        for url in [tv_url, phone_url]:
            # 5 pages for each group
            for page_id in range(1, 6):
                request = scrapy.Request('{}?pg={}'.format(url, page_id), callback=self.parse_product_list, errback=self.errback_httpbin)
                yield request
        
    def parse_product_list(self, response):
        '''
            Parse all product on a page.
        '''
        # get all product url on a page
        products = response.xpath("//li[contains(@class,'BaseGridItem__multipleImage')]/a[contains(@class,'hover')]/@href")

        for product in products:
            product_url = product.extract()
            # store product id for amp crawling
            product_id = re.search(r'(.*-)?(.*).html', product_url).group(2)
            request = scrapy.Request(product_url, callback=self.parse_normal, meta={'product_url': self.base_url + product_id}, errback=self.errback_httpbin)
            yield request

    def parse_amp(self, response):
        '''
            Parse information for product amp page.

            Information to be crawled:
            1. Image URL
            2. Product Spec
            3. Product Category e.g(Yahoo 購物 > 家電/電視/冷氣/冰箱 > 生活家電 > 電話/對講機)
        '''
        product = response.meta['product']

        product['img_url'] = response.xpath("//amp-carousel/amp-img/@src").extract() 

        spec = response.xpath("//div[@class = 'spec']//tr//text()").extract()
        # For each row in spec table, 
        # combine it using ':'
        spec = ['{}: {}'.format(x, y) for x, y in zip(spec[0::2], spec[1::2])]
        product['spec'] = spec

        category = response.xpath("//div[@id = 'iCategory']//a/text()")[0:3].extract()
        category = '{} > {}'.format(self.base_category, ' > '.join(category))
        product['category'] = category

        yield product
        

    def parse_normal(self, response):
        '''
            Parse information for product page.

            Information to be crawled:
            1. Product title
            2. Product feature
        '''
        product = Product()
        product_url = response.meta['product_url']

        product['title'] = response.xpath("//h1[contains(@class, 'title')]/text()").extract_first()
        product['feature'] = response.xpath("//div[contains(@class, 'ShoppingProductFeatures__productFeatureWrapper')]/ul//li/text()").extract()
      
        request = scrapy.Request(product_url, callback=self.parse_amp, meta={'product': product})

        yield request
        
    