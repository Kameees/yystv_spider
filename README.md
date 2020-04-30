# yystv_spider
爬取游研社[游戏史页面](https://www.yystv.cn/b/history)所有文章。

> 本次爬取的数据仅供个人学习使用。
>
> 项目的Github地址为：[yystv_spider](https://github.com/Kameees/yystv_spider)

# Scrapy 介绍

>Scrapy是一个为了爬取网站数据，提取结构性数据而编写的应用框架。 可以应用在包括数据挖掘，信息处理或存储历史数据等一系列的程序中。
>
>其最初是为了 页面抓取 (更确切来说, 网络抓取)所设计的， 也可以应用在获取API所返回的数据(例如 Amazon Associates Web Services ) 或者通用的网络爬虫。

# 事前准备

推荐在Anaconda创建虚拟环境进行。请确保事先安装好Scrapy、PyMongo库。

可使用以下命令安装：

```
pip install scrapy
pip install pymongo
```

# 爬取思路

- 在游研社[游戏史页面](https://www.yystv.cn/b/history)获取每个文章的链接id

- 在文章页面获取文章标题、作者、创建时间、内容

# 爬取分析

打开游研社[游戏史页面](https://www.yystv.cn/b/history)，发现该页面包含了所有文章，下拉网页会加载新的文章。

打开开发者工具，切换到XHR过滤器下拉网页可以看到Ajax请求，这些请求就是获取文章信息的Ajax请求。

![yystvhistory1.png](https://kameee.top/upload/2020/04/yystv-history-1-fc7c62fa5563483a95bb2c6401a154d6.png)

可以看到请求链接为：https://www.yystv.cn/boards/get_board_list_by_page?page=1&value=history

第二页的请求链接为：https://www.yystv.cn/boards/get_board_list_by_page?page=2&value=history

可知获取下一页的请求参数为page，修改page可获得所有请求链接。

文章页面的信息可以直接通过xpath定位获取，需要爬取的参数为：

```
id：文章id
title： 文章标题
author： 文章作者
createtime： 发表时间
context： 文章内容
```

# 开始爬取

使用Scrapy。

创建yystv_spider项目。

```
scrapy startproject yystv_spider
```

进入项目文件夹新建spider。

```
scrapy genspider yystv_spider yystv.cn
```

修改item,设置需要爬取的数据参数。

代码如下：

```
# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class YystvSpiderItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    collection = 'yystv_history'
    id = scrapy.Field()
    title = scrapy.Field()
    author = scrapy.Field()
    createtime = scrapy.Field()
    context = scrapy.Field()
```

修改spider文件夹history编写爬取规则。

代码如下：

```
# -*- coding: utf-8 -*-
import json
import scrapy
from yystv_spider.items import YystvSpiderItem


class HistorySpider(scrapy.Spider):
    name = 'history'
    allowed_domains = ['yystv.cn']
    start_urls = ['https://www.yystv.cn/boards/get_board_list_by_page?page=%s&value=history' % i for i in range(0, 21)]

    def parse(self, response):
        '''
        解析游戏史首页JSON请求
        :param response:
        :return: 各文章的id构成链接：https://www.yystv.cn/p/id
        '''
        result = json.loads(response.text)
        data_list = result.get('data')
        for data in data_list:
            id = data.get('id')
            url = 'https://www.yystv.cn/p/' + str(id)
            #   生成文章页面的Request
            yield scrapy.Request(url=url, callback=self.history_page, meta={'id': id}, dont_filter=True)

    def history_page(self, response):
        '''
        解析文章页面(使用xpath)
        :param response:
        :return: 存有文章信息的item
        '''
        item = YystvSpiderItem()
        #   文章id
        item['id'] = response.meta['id']
        #   文章标题
        item['title'] = response.xpath('//div[@class="doc-title"]//text()').extract_first()
        content = response.xpath('//div[@class="content-block rel"]')
        #   文章作者
        item['author'] = content.xpath('//a[@class="block-a a-red"]/text()').extract_first()
        #   创建时间
        item['createtime'] = content.xpath('//span[@class="doc-createtime fl"]/text()').extract_first()
        #   文章内容
        context = []
        p_list = content.xpath('//div[@class="doc-content rel"]/div[1]//p')
        for p in p_list:
            #   判断p标签内的img标签是否存在，存在就存入context列表，不存在就获取文字
            img_addr = p.xpath('img/@data-original').extract_first()
            if img_addr:
                cont = '<p><img src="%s"/></p>' % (img_addr)
                context.append(cont)
            else:
                cont = p.xpath('text()').extract_first()
                context.append(cont)
        if context:
            item['context'] = '<br>'.join(context)
        else:
            item['context'] = ''
        yield item
```

# 数据存储

将爬取的数据存入MongoDB和保存为CSV文件。具体代码实现在pipelines中。

```
MongoPipeline():存入MongoDB
CsvPipeline():存入CSV文件
```

代码如下：

```
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
```

下载中间件Middlewares不需要修改，使用默认配置。

# 启用设置,修改settings

启用pipelines。

```
# -*- coding: utf-8 -*-

# Scrapy settings for yystv_spider project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://doc.scrapy.org/en/latest/topics/settings.html
#     https://doc.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://doc.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = 'yystv_spider'

SPIDER_MODULES = ['yystv_spider.spiders']
NEWSPIDER_MODULE = 'yystv_spider.spiders'


# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'yystv_spider (+http://www.yourdomain.com)'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
#CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See https://doc.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
DOWNLOAD_DELAY = 2
# The download delay setting will honor only one of:
#CONCURRENT_REQUESTS_PER_DOMAIN = 16
#CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
#}

# Enable or disable spider middlewares
# See https://doc.scrapy.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    'yystv_spider.middlewares.YystvSpiderSpiderMiddleware': 543,
#}

# Enable or disable downloader middlewares
# See https://doc.scrapy.org/en/latest/topics/downloader-middleware.html
#DOWNLOADER_MIDDLEWARES = {
#    'yystv_spider.middlewares.YystvSpiderDownloaderMiddleware': 543,
#}

# Enable or disable extensions
# See https://doc.scrapy.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
#}

# Configure item pipelines
# See https://doc.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    'yystv_spider.pipelines.MongoPipeline': 300,
    'yystv_spider.pipelines.CsvPipeline': 301,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://doc.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://doc.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = 'httpcache'
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'

#   MONGO配置
#   数据库地址
MONGO_URI = 'localhost'
#   数据库名
MONGO_DATABASE = 'yystv'
```

# 运行scrapy项目

```
scrapy crawl history
```

运行一段时间后可查看爬取的数据。

![yystvhistory2.png](https://kameee.top/upload/2020/04/yystv-history-2-a736b090ca104854a867ded366336618.png)

![yystvhistory3.png](https://kameee.top/upload/2020/04/yystv-history-3-55cc92f636c9426faf967b02b22c5bcb.png)
