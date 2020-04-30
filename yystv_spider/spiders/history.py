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
            yield scrapy.Request(url=url, callback=self.history_page, dont_filter=True)

    def history_page(self, response):
        '''
        解析文章页面(使用xpath)
        :param response:
        :return: 存有文章信息的item
        '''
        item = YystvSpiderItem()
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
        item['context'] = '<br>'.join(context)
        yield item

