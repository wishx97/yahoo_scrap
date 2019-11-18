# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class Product(scrapy.Item):
    title = scrapy.Field()
    feature = scrapy.Field()
    img_url = scrapy.Field()
    spec = scrapy.Field()
    category = scrapy.Field()

    def __str__(self):
        return ''
