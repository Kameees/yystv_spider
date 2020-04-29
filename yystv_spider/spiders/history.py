# -*- coding: utf-8 -*-
import json
import scrapy
from yystv_spider.items import YystvSpiderItem


class HistorySpider(scrapy.Spider):
    name = 'history'
    #allowed_domains = ['yystv.cn']
    start_urls = ['https://www.yystv.cn/boards/get_board_list_by_page?page=%s&value=history' % i for i in range(0, 21)]

    def parse(self, response):
        result = json.loads(response.text)
        data_list = result.get('data')
        for data in data_list:
            id = data.get('id')
            url = 'https://www.yystv.cn/p/' + str(id)
            yield scrapy.Request(url=url, callback=self.history_page, dont_filter=True)

    def history_page(self, response):
        item = YystvSpiderItem()
        item['title'] = response.xpath('//div[@class="doc-title"]//text()').extract_first()
        content = response.xpath('//div[@class="content-block rel"]')
        item['author'] = content.xpath('//a[@class="block-a a-red"]/text()').extract_first()
        item['createtime'] = content.xpath('//span[@class="doc-createtime fl"]/text()').extract_first()
        context = []
        p_list = content.xpath('//div[@class="doc-content rel"]/div[1]//p')
        for p in p_list:
            img_addr = p.xpath('img/@data-original').extract_first()
            if img_addr:
                cont = '<p><img src="%s"/></p>' % (img_addr)
                context.append(cont)
            else:
                cont = p.xpath('text()').extract_first()
                context.append(cont)
        item['context'] = '<br>'.join(context)
        yield item

