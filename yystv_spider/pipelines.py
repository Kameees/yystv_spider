# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
from yystv_spider.items import YystvSpiderItem
import pymongo
import csv


class MongoPipeline(object):

    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get('MONGO_URI'),
            mongo_db=crawler.settings.get('MONGO_DATABASE')
        )

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]
        self.db[YystvSpiderItem.collection].create_index([('id', pymongo.ASCENDING)])

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        if isinstance(item, YystvSpiderItem):
            self.db[item.collection].update({'id': item.get('id')}, {'$set': item}, True)
        return item


class CsvPipeline(object):

    def open_spider(self, spider):
        self.file = open('yystv_history.csv', 'w', newline='', encoding='utf-8-sig')
        self.writer = csv.writer(self.file)
        self.writer.writerow(['id', 'title', 'author', 'createtime', 'context'])

    def process_item(self, item, spider):
        self.writer.writerow([item['id'], item['title'], item['author'], item['createtime'], item['context']])
        return item

    def close_spider(self, spider):
        self.file.close()
