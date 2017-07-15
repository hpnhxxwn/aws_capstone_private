import dryscrape
from bs4 import BeautifulSoup
import time
import datetime
import re

#we visit the main page to initialise sessions and cookies
session = dryscrape.Session()
session.set_attribute('auto_load_images', False)
session.set_header('User-agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95     Safari/537.36')    

#call this once as it is slow(er) and then you can do multiple download, though there seems to be a limit after which you have to reinitialise...
session.visit("https://finance.yahoo.com/quote/AAPL/history?p=AAPL")
response = session.body()


#get the dowload link
soup = BeautifulSoup(response, 'lxml')
for taga in soup.findAll('a'):
    if taga.has_attr('download'):
        url_download = taga['href']
print(url_download)

#now replace the default end date end start date that yahoo provides
s = "2007-05-18"
period1 = '%.0f' % time.mktime(datetime.datetime.strptime(s, "%Y-%m-%d").timetuple())
e = "2017-05-18"
period2 = '%.0f' % time.mktime(datetime.datetime.strptime(e, "%Y-%m-%d").timetuple())

#now we replace the period download by our dates, please feel free to improve, I suck at regex
m = re.search('period1=(.+?)&', url_download)
if m:
    to_replace = m.group(m.lastindex)
    url_download = url_download.replace(to_replace, period1)        
m = re.search('period2=(.+?)&', url_download)
if m:
    to_replace = m.group(m.lastindex)
    url_download = url_download.replace(to_replace, period2)

#and now viti and get body and you have your csv
session.visit(url_download)
csv_data = session.body()

#and finally if you want to get a dataframe from it
import sys
if sys.version_info[0] < 3: 
    from StringIO import StringIO
else:
    from io import StringIO

import pandas as pd
df = pd.read_csv(StringIO(csv_data), index_col=[0], parse_dates=True)
df