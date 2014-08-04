import sys
sys.path.insert(0,'libs')
from bs4 import BeautifulSoup
from google.appengine.api import urlfetch
from google.appengine.api.urlfetch import DeadlineExceededError
from google.appengine.api.urlfetch import DownloadError
from lxml import etree
import re
import json
import logging
import langcountry

def handle_bookstw_searchresult(bookitem, rpc):
    try:
        result = rpc.get_result()
    except DeadlineExceededError:
        logging.error("Deadline Exceeded While Fetching Books.com.tw Search Result\n\n\n")
        return
    except DownloadError:
        logging.error("Download Error. Check network connections.")
        return

    if result.status_code == 200:
        tree = etree.HTML(result.content)
        urls = tree.xpath('//form[@id="searchlist"]/ul[@class="searchbook"]/li/h3/a[contains(@href, "prod_search_redir")]/@href')
        if urls:
            crawl(bookitem, urls[0], create_bookstw_bookresult_callback, None, None)

def handle_bookstw_bookresult(bookitem, rpc):
    try:
        result = rpc.get_result()
    except DeadlineExceededError:
        logging.error("Deadline Exceeded While Fetching Books.com.tw Book Result\n\n\n")
        return
    except DownloadError:
        logging.error("Download Error. Check network connections.")
        return

    if result.status_code == 200:
        tree = etree.HTML(result.content)
        bookitem.language = u'\u4e2d\u6587'
        names = tree.xpath('//div[contains(@class,"type02_p002")]/h1/text()')
        if names:
            bookitem.name = unicode(names[0])
            prd002li = tree.xpath('//div[contains(@class,"type02_p003")]//li')


            for listitem in prd002li:
                # listitemtext = unicode(listitem.extract())
                logging.error('LISTITEM.XPATH(TEXT): %s' % listitem.xpath('.//text()'))
                listitemtext = ' '.join(map(unicode.strip, map(unicode,listitem.xpath('.//text()'))))

                # logging.error("LISTITEMTEXT: %s" % listitemtext)

                if u"\u4f5c\u8005" in listitemtext:
                    # item['author'] = ' '.join(map(unicode.strip, listitem.select('.//text()').extract()))
                    validauthor = re.compile(u"^\u4f5c\u8005\uff1a\s*(.*?)(?:/.*)?$")
                    author = re.findall(validauthor, listitemtext)
                    # logging.error("author: %s" % author)
                    if author:
                        bookitem.author = author     # note that bookitem.author expects a list
                elif u"\u7e6a\u8005" in listitemtext:
                    # item['illustrator'] = listitem.select('a//text()').extract()[0]
                    validillustrator = re.compile(u"\u7e6a\u8005\uff1a\s*(.*?)(?:/.*)?$")
                    illustrator = re.findall(validillustrator, listitemtext)
                    if illustrator:
                        bookitem.illustrator = illustrator[0]
                elif u"\u8b6f\u8005" in listitemtext:
                    # item['translator'] = listitem.select('a//text()').extract()[0]
                    validtranslator = re.compile(u"\u8b6f\u8005\uff1a\s*(.*?)(?:/.*)?$")
                    translator = re.findall(validtranslator, listitemtext)
                    if translator:
                        bookitem.translator = translator[0]
                elif u"\u51fa\u7248\u793e" in listitemtext:
                    # item['publisher'] = listitem.select('a//text()').extract()[0]
                    validpublisher = re.compile(u"\u51fa\u7248\u793e\uff1a\s*(.*?)(?:/.*)?$")
                    publisher = re.findall(validpublisher, listitemtext)
                    if publisher:
                        bookitem.publisher = publisher[0]
                elif u"\u51fa\u7248\u65e5\u671f" in listitemtext:
                    valid_date = re.compile(u'\u51fa\u7248\u65e5\u671f\uff1a\s*(\d+)\/(\d+)\/\d+')
                    rematchresult = re.match(valid_date, listitemtext)
                    if rematchresult:
                        bookitem.publication_date = ''.join(list(rematchresult.groups()))

            # prd003li = tree.xpath('//ul[@class="price"]/li')
            # for listitem in prd003li:
            #     listitemtext = unicode(listitem.text)
            #     if u"\u5b9a\u50f9" in listitemtext:
            #         bookitem.list_price_ccy = u"TWD"
            #         prices = listitem.xpath('em')
            #         if prices:
            #             bookitem.list_price_amt = float(prices[0].text.strip())

            details = tree.xpath('//div[contains(@class, "type02_m058")]//li')
            for listitem in details:
                listitemtext = unicode(listitem.text)
                if u"\u7cfb\u5217" in listitemtext:
                    valid_series = re.compile(u'\u7cfb\u5217\uff1a(.*)')
                    rematchresults = re.findall(valid_series, listitemtext)
                    if rematchresults:
                        bookitem.series = rematchresults[0]

                elif u"\u898F\u683C" in listitemtext:
                    if u"\u7cbe\u88dd" in listitemtext:
                        bookitem.book_format = u"Hardback"
                    elif u"\u5e73\u88dd" in listitemtext:
                        bookitem.book_format = u"Paperback"

                    if u"\u5168\u5f69" in listitemtext:
                        bookitem.colour = "Colour"

                    valid_dim =re.compile(u"((?:\d+(?:\.\d+)?)(?:\s*x\s*(?:\d+(?:\.\d+)?)){1,2})\s*(?:cm)?")
                    rematchresults = re.findall(valid_dim, listitemtext)
                    if rematchresults:
                        bookitem.dimensions = re.sub(ur'\s*x\s*', u" \u00d7 ", rematchresults[0])

                    valid_extent = re.compile(u"(\d+)\s*\u9801")
                    rematchresults = re.findall(valid_extent, listitemtext)
                    if rematchresults:
                        bookitem.extent = int(rematchresults[0].strip())

                elif u"\u51FA\u7248\u5730" in listitemtext:
                    valid_origin = re.compile(u"\u51fa\u7248\u5730\uff1a(\S*)")
                    rematchresults = re.findall(valid_origin, listitemtext)
                    if rematchresults:
                        bookitem.origin = rematchresults[0]

            video_links = tree.xpath('//iframe[contains(@src,"youtube")]/@src')
            if video_links:
                bookitem.video_links = video_links

            desc = tree.xpath('//div[contains(@itemprop,"description")]')
            if desc:
                # bookitem.desc = unicode(etree.tostring(desc[0]))
                bookitem.desc = ''.join([etree.tostring(child) for child in desc[0].iterdescendants()])


def handle_eslitetw_searchresult(bookitem, rpc):
    try:
        result = rpc.get_result()
    except DeadlineExceededError:
        logging.error("Deadline Exceeded While Fetching Eslite Search Result\n\n\n")
        return
    except DownloadError:
        logging.error("Download Error. Check network connections.")
        return

    if result.status_code == 200:
        tree = etree.HTML(result.content)
        urls = tree.xpath('//span[@id="ctl00_ContentPlaceHolder1_rptProducts_ctl00_LblName"]/../@href')
        if urls:
            crawl(bookitem, urls[0], create_eslitetw_bookresult_callback, None, None)

def handle_eslitetw_bookresult(bookitem, rpc):
    try:
        result = rpc.get_result()
    except DeadlineExceededError:
        logging.error("Deadline Exceeded While Fetching Eslite Book Result\n\n\n")
        return
    except DownloadError:
        logging.error("Download Error. Check network connections.")
        return

    if result.status_code == 200:
        tree = etree.HTML(result.content)
        soup = BeautifulSoup(result.content)
        intro = soup.select('#ctl00_ContentPlaceHolder1_Product_info_more1_introduction')[0]
        intro.h2.extract()
        intro.select("a.top_line")[0].extract()
        bookitem.desc = re.sub(r'(^\s*)|(\s*$)', '', ''.join(map(unicode, intro.contents)))

        price_tag = tree.xpath('//div[@class="PI_info"]//span[@class="price"]')
        if price_tag:
            price_tag_desc = price_tag[0].xpath('../text()')[0]
            if u'NT$' in price_tag_desc:
                bookitem.list_price_ccy = u'TWD'
            if u'\u5b9a\u50f9' in price_tag_desc:
                bookitem.list_price_amt = int(price_tag[0].text)

        # rows = tree.xpath('//table[@id="ctl00_ContentPlaceHolder1_Product_detail_book1_dlSpec"]/tr/td')
        # for row in rows:
        #     fieldname = row.xpath('span[1]/text()')
        #     fieldcontent = row.xpath('span[2]/text()')
        #     if u'\u5c3a\u5bf8' in fieldname[0]:
        #         if fieldcontent:
        #             bookitem.dimensions = fieldcontent[0]
        #     elif u'\u9801\u6578' in fieldname[0]:
        #         if fieldcontent:
        #             bookitem.extent = fieldcontent[0]
        #     elif u'\u88dd\u8a02' in fieldname[0]:
        #         if fieldcontent:
        #             if u'\u539a\u7d19\u7248\u66f8' in fieldcontent[0]:
        #                 bookitem.book_format = "Board Book"
        #             elif u'\u5e73\u88dd' in fieldcontent[0]:
        #                 bookitem.book_format = "Paperback"
        #             elif u'\u7cbe\u88dd' in fieldcontent[0]:
        #                 bookitem.book_format = "Hardback"

        titles = tree.xpath('//div[@id="photos"]//a[@class="PI_img-s"]/@title')
        bookitem.image_urls = [BeautifulSoup(img_links).a['href'] for img_links in titles]
        bookitem.num_images = len(titles)

def handle_google_bookresult(bookitem, js):
    try:
        bookitem.name = js[u'items'][0][u'volumeInfo'][u'title']
    except KeyError:
        pass

    try:
        bookitem.author = js[u'items'][0][u'volumeInfo'][u'authors']
    except KeyError:
        pass

    try:
        if u'publisher' in js[u'items'][0][u'volumeInfo']:
            bookitem.publisher = js[u'items'][0][u'volumeInfo'][u'publisher']
    except KeyError:
        pass

    try:
        valid_date = ur"(\d{4})-(\d{2})-\d{2}"
        matchresult = re.match(valid_date, js[u'items'][0][u'volumeInfo'][u'publishedDate'])
        if matchresult:
            bookitem.publication_date = ''.join(matchresult.groups())
    except KeyError:
        pass

    try:
        lang = js[u'items'][0][u'volumeInfo'][u'language']
        bookitem.language = langcountry.languages[lang[:2]]
        if len(lang) > 2:
            bookitem.origin = langcountry.countries[lang[-2:]]
    except KeyError:
        pass

    try:
        if u'dimensions' in js[u'items'][0][u'volumeInfo']:
            bookitem.dimensions = u" \u00d7 ".join([js[u'items'][0][u'volumeInfo']['dimensions']['height'],
                                                    js[u'items'][0][u'volumeInfo']['dimensions']['width'],
                                                    js[u'items'][0][u'volumeInfo']['dimensions']['thickness']])
    except KeyError:
        pass
        # bookitem.colour = 
        # bookitem.series = 
        # video_links = 

    try:
        bookitem.extent = js['items'][0]['volumeInfo']['pageCount']
    except KeyError:
        pass
        # book_format = 

    try:
        bookitem.desc = js['items'][0]['volumeInfo']['description']
    except KeyError:
        pass
        # bookitem.list_price_ccy = 
        # bookitem.list_price_amt =
        
    try:
        if u'imageLinks' in js['items'][0]['volumeInfo']:
            if u'thumbnail' in js['items'][0]['volumeInfo']['imageLinks']:
                bookitem.image_urls = [js['items'][0]['volumeInfo']['imageLinks']['thumbnail']]
                bookitem.num_images = 1
    except KeyError:
        pass

        # bookitem.price =

# Use a helper function to define the scope of the callback.
def create_bookstw_searchresult_callback(bookitem, rpc):
    return lambda: handle_bookstw_searchresult(bookitem, rpc)

def create_bookstw_bookresult_callback(bookitem, rpc):
    return lambda: handle_bookstw_bookresult(bookitem, rpc)

def create_eslitetw_searchresult_callback(bookitem, rpc):
    return lambda: handle_eslitetw_searchresult(bookitem, rpc)

def create_eslitetw_bookresult_callback(bookitem, rpc):
    return lambda: handle_eslitetw_bookresult(bookitem, rpc)

def crawl(bookitem, url, callbackfunc, url2, callbackfunc2, googlebooksjs = False):
    """creates asynchronous crawler"""

    # logging.error("crawler started")
    crawl_tw = not googlebooksjs

    if googlebooksjs:
        # logging.error("google crawler started")
        googlebooksapiurl = ''.join(["https://www.googleapis.com/books/v1/volumes?q=isbn:", bookitem.isbn, "&country=US"])
        try:
            result = urlfetch.fetch(googlebooksapiurl)
        except DownloadError:
            logging.error("Download Error. Check network connections.")
            return

        # logging.error(result)
        # logging.error(json.dumps(result.content))
        if result.status_code == 200:
            js = json.loads(result.content)
            if js['totalItems'] == 0:
                crawl_tw = True
            else:
                handle_google_bookresult(bookitem, js)
                if bookitem.origin == u'Taiwan' or bookitem.isbn[3:6] == '957' or bookitem.isbn[3:6] == '986':
                    crawl_tw = True

    if crawl_tw:
        # logging.error("tw crawler started")
        rpcs = []
        rpc = urlfetch.create_rpc(deadline=20)
        rpc.callback = callbackfunc(bookitem, rpc)
        urlfetch.make_fetch_call(rpc, url)
        rpcs.append(rpc)

        if url2:
            rpc2 = urlfetch.create_rpc(deadline=20)
            rpc2.callback = callbackfunc2(bookitem, rpc2)
            urlfetch.make_fetch_call(rpc2, url2)
            rpcs.append(rpc2)

        for c in rpcs:
            c.wait()
