from datetime import date
from datetime import datetime
import math
import requests
from lxml import etree
import sys
reload(sys)
priceDic = {}

def getNews(ticker):
    url = 'https://www.google.com/finance/company_news?q=' + ticker + '&start=0&num=1000'
    r = requests.get(url)
    dom = etree.HTML(r.content)
    nameList = dom.xpath("//div[@id='news-main']//span[@class='name']/a/text()")
    dateList = dom.xpath("//div[@id='news-main']//span[@class='date']/text()")
    #print(nameList)
    #print(dateList)
    rtn = []
    for i in range(len(nameList)):
        d = dateList[i]
        #print(dateList[i])
        #print(nameList[i])
        print("hehe")
        n = nameList[i].encode("utf8").replace("\xa0", " ").replace("\xc2", " ")
        #n = nameList[i]
        if "ago" in d:
            d = date.today()
        else:
            d = datetime.strptime(d, "%b %d, %Y").date()
        rtn.append({'title': n, 'date': d})

    return rtn

def getHistoricalPrice(ticker):
    if ticker in priceDic:
        # print("using cache price series for " + ticker)
        return priceDic[ticker]

    print("fetching price series for " + ticker + "...")
    url = "http://www.google.com/finance/historical?q=" + ticker + "&startdate=Jan+1%2C+2014&output=csv"
    r = requests.get(url)
    print("fetching price series done")
    lines = r.content.decode('utf-8').split("\n")
    lines.pop(0)
    raw = [ l.split(",") for l in lines ]
    data = []
    for d in raw:
        if d[0] == '':
            continue
        data.append({
            'date': datetime.strptime(d[0], "%d-%b-%y").date(),
            'open': float( d[1] ),
            'high': float( d[2] ),
            'low': float( d[3] ),
            'close': float( d[4] ),
            'volume': int( d[5] )
        })
    data.sort(key=lambda i: i['date'], reverse = True)
    priceDic[ticker] = data
    return data

def getPriceByDate(ticker, date, offset):
    # offset is for choosing the price of date relative to
    # the specified date, 1 for future 1 date, -1 for past 1 date
    data = getHistoricalPrice(ticker)
    pos = None
    i = 0
    for d in data:
        if date == d['date']:
            pos = 0
            break
        elif date > d['date']:
            pos = -0.5
            break
        i = i + 1

    if pos == None or ( offset==0 and pos != 0 ):
        return None

    finalpos = int( i + pos - offset )
    if finalpos < 0 or finalpos >= len(data):
        return None

    return data[finalpos]

def getStockSymbol(source):
    if source.startswith('http://') or source.startswith('https://'):
        self.data = urllib2.urlopen(filename)
    elif source.startswith('file://'):
        directory = os.path.realpath(source[7:])
        if not os.path.isdir(directory):
            fatal("%s is not a directory." % directory)

        path = '%s/#%s.csv' % (directory, company)
        if not os.path.exists(path):
            fatal("%s does not exist." % path)
        if not os.path.isfile(path):
            fatal("%s is not a regular file." % path)

        info(" read: file://%s" % path)
        self.data = open(path, 'r')
    elif source == '-':
        self.data = fileinput.input('-')

if __name__ == "__main__":
    print(getNews("AAPL"))
    print(getPriceByDate("AAPL", 1, 100))
