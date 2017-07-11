from __future__ import print_function
import pandas as pd
import argparse
import calendar
import copy
import datetime
#from datetime import datetime
import dateutil
import fileinput
import os.path
import re
#import sys
import io
import urllib2
import multiprocessing

import bytebuffer
import botocore
import boto3
#from datetime import date
import logging
from common import *
import requests
import USTradingCalendar

from numpy import array
import nltk
import re
from nltk.stem.porter import PorterStemmer
from nltk.stem.snowball import SnowballStemmer
#import word2vec
from gensim.models import Word2Vec
from gensim.models.word2vec import LineSentence
import codecs
import sys
import json
import numpy as np

#reload(sys)
#sys.setdefaultencoding('utf8')

data = ""
sector = ""
date = ""
tweet = ""
stock = {}

logging.basicConfig()

def fatal(msg=''):
    if msg:
        sys.stderr.write('error: %s\n' % msg)
        sys.stderr.flush()
    sys.exit(1)

def warning(msg):
    sys.stderr.write('warning: %s\n' % msg)
    sys.stderr.flush()

def info(msg):
    sys.stderr.write('info: %s\n' % msg)
    sys.stderr.flush()

def parse_argv():
    o = Options()
    o.add('--src', metavar='URI', type=str,
        default='s3://aws-nyc-taxi-data', help="data source directory")
    o.add('--size', metavar='vector_size', type=str,
    	default=32, help="word vector dimention")
    #o.add('-s', '--start',  metavar='NUM', type=int,
    #    default=0, help="start record index")
    #o.add('-e', '--end',  metavar='NUM', type=int,
    #    default=4 * 1024 ** 3, help="end record index")
    #o.add('-r', '--report', action='store_true',
    #    default=False, help="report results")
    #o.add('-p', '--procs', type=int, dest='nprocs',
    #    default=1, help="number of concurrent processes")
    #o.add('-w', '--worker', action='store_true',
    #    default=False, help="worker mode")
    #o.add('--sleep', type=int,
    #    default=10, help="worker sleep time if no task")

    opts = o.load()

    #if opts.start < 0 or opts.start > opts.end:
    #    fatal("invalid range [%d, %d]" % (opts.start, opts.end))

    #opts.end = min(get_file_length(
    #    opts.src, opts.color, opts.year, opts.month), opts.end)

    #logger.setLevel(opts.verbose)
    return opts

class TweetPreProcess(object):
	def __init__(self, opts):
		self.source = opts.src
		self.opts = opts
		self.priceDic = {}
		self.holiday = {}
		self._offsets = (3, 1, 1, 1, 1, 1, 2)
		self.tweetDic = {}
		self.stemmer = SnowballStemmer("english")
		self.vecList = {}
		self.sents = {}
		self.model = None

	def tokenize_sentence(self):
		for symbol in self.tweetDic:
			self.sents[symbol] = {}
			for date in self.tweetDic[symbol]:
				sentStem = []
				self.sents[symbol][date] = []
				for t in self.tweetDic[symbol][date]:		
					sent = nltk.sent_tokenize(t)
					sentStem = self.tokenize_and_stem(sent)
					for s in sentStem:
						self.sents[symbol][date].append(s)
		
	def tokenize_and_stem(self, sentences):
		sents = []
		#stemmer = SnowballStemmer("english")
		for s in sentences:
			pattern = r"\w+(?:\w\.\w)*" 
			pat = re.compile(pattern)
			tokens = nltk.regexp_tokenize(s, pat)
			stems = [self.stemmer.stem(t) for t in tokens]
			sents.append(stems)

		return sents

	def load_word2vec_model(self, size=100):
		if self.model is None:
			self.train_word2vec(size)
		else:
			self.model = Word2Vec.load('tweet_model')

		return self.model

	def buildWordVector(self, text, size=32):
		#print(text)
		tmp = np.zeros(size)
		vec = tmp.reshape((1, size))
		count = 0.
		for word in text:
			try:
				vec += self.model[word].reshape((1, size))
				count += 1.
			except KeyError:
				continue
		if count != 0:
			vec /= count
		return vec

	def generate_tweet_vectors(self, size=32):
		for symbol in self.tweetDic:
			self.vecList[symbol] = {}
			for d in self.tweetDic[symbol]:
				if d not in self.vecList[symbol]:
					self.vecList[symbol][d] = []

				for sent in self.tweetDic[symbol][d]:
					#if d in self.priceDic[symbol]:
					#print(sent)
					#print(self.buildWordVector(sent))
					#print(self.priceDic[symbol][d]['increases'])
					self.vecList[symbol][d].append([self.buildWordVector(sent), self.priceDic[symbol][d]['increases']])

	def generate_vector_file(self):
		with open("vector.txt", 'w') as f: 
			for symbol in self.vecList:
				for d in self.vecList[symbol]:
					for v in self.vecList[symbol][d]:
						#for v in vecList:
						#print(v[0].reshape(1, 100))
						f.write("{")
						for item in v[0][0]:
							#print(item)
							f.write(str(item) + " ")
							f.write(": ")
							f.write(str(v[1]))
						f.write("}\n")

	def train_word2vec(self, size):
		sentences_tokens = []
		for symbol in self.sents:
			for d in self.sents[symbol]:
				for s in self.sents[symbol][d]:
					sentences_tokens.append(s)

		self.model = Word2Vec(sentences_tokens, size=size, window=5, min_count=5, workers=4)
		self.model.save("tweet_model")
		return self.model

	def date_is_holiday(self, date):
		# data[0] is year
		if date.year not in self.holiday: 
			self.holiday[date.year] = USTradingCalendar.get_trading_close_holidays(date.year)
		
		for d in self.holiday[date.year]:
			d_tmp = str(d).split(' ')[0]
			    		
			if str(date) == d_tmp:
				return True

		return False
			    			
	def getSymbolAndTweet(self, source, sep=';'):
		if source.startswith('http://') or source.startswith('https://'):
			data = urllib2.urlopen(filename)
		elif source.startswith('file://'):
			directory = os.path.realpath(source[7:])
	        if not os.path.isdir(directory):
	            fatal("%s is not a directory." % directory)

	        for file in os.listdir(directory):
	        	tweet_file = os.path.join(directory, file)
	        	symbol = file.split(".")[0]
	        	print("Processing tweets for stock %s", symbol)
	        	info(" read: file://%s" % tweet_file)

	        	# Create a symbol entry in tweets dictionary
	        	if symbol not in self.tweetDic:
	        		self.tweetDic[symbol] = {}

	        	data = codecs.open(tweet_file, 'r', encoding='utf-8', errors='ignore')
	        	data.readline()
	        	for line in data:
			    	list = line.split(sep);
			    	sector = list[0];
			    	date = list[1].split(' ')[0].split('-')
			    	tweet = list[4]
			    	#print(date)
			    	tweet_date = datetime.date(int(date[0]), int(date[1]), int(date[2]))
			    	if tweet_date.weekday() >= 5:
			    		#tweet_date = tweet_date - datetime.timedelta(tweet_date.weekday() - 5 + 1)
			    		continue

			    	is_holiday = self.date_is_holiday(tweet_date)
			    	if (is_holiday):
			    		continue

			    	if str(tweet_date) not in self.tweetDic[symbol]:
			    		self.tweetDic[symbol][str(tweet_date)] = []

			    	self.tweetDic[symbol][str(tweet_date)].append(tweet)

			    	today = datetime.date.today()
			    	
	        		self.getHistoricalPrice(symbol)

	def getHistoricalPrice(self, ticker):
	    if ticker in self.priceDic:
	        # print("using cache price series for " + ticker)
	        return self.priceDic[ticker]

	    self.priceDic[ticker] = {}
	    print("fetching price series for " + ticker + "...")
	    url = "http://www.google.com/finance/historical?q=" + ticker + "&startdate=Jan+1%2C+2007&output=csv"
	    r = requests.get(url)
	    print("fetching price series done")
	    lines = r.content.decode('utf-8').split("\n")
	    lines.pop(0)
	    raw = [ l.split(",") for l in lines ]
	    data = []
	    for d in reversed(raw):	
	        if d[0] == '':
	            continue
	        #if str(datetime.datetime.strptime(d[0], "%d-%b-%y").date()) not in self.stock_price[ticker]:
	        #	self.stock_price[ticker] = {}
	        if d[1] == '-':
	        	d[1] = d[4]
	        	d[2] = d[4]
	        	d[3] = d[4]

	        increases = -99
	        #print(d[0])
	        this_open_date = datetime.datetime.strptime(d[0], "%d-%b-%y").date()
	        last_open_date = this_open_date - datetime.timedelta(days = 1)
	        if (last_open_date.weekday() >= 5):
	        	#print("Get data from last week open date")
	        	last_open_date = last_open_date - datetime.timedelta(last_open_date.weekday() - 5 + 1)

	        #print(last_open_date)
	        #print(this_open_date)
	        is_holiday = self.date_is_holiday(last_open_date)
	        if (is_holiday):
	        	last_open_date = last_open_date - datetime.timedelta(days = 1)

	        if str(last_open_date) in self.priceDic[ticker]:
	        	
	        	#print(float(d[4]))
	        	#print(self.priceDic[ticker][str(last_open_date)])
	        	

	        	json_data = self.priceDic[ticker][str(last_open_date)]
	        	#print(json_data['close'])
	        	increases = (float(d[4]) - json_data['close']) / json_data['close']

	        #print(increases)
	        self.priceDic[ticker][str(this_open_date)] = {'open':   float(d[1]), 
													      'high':   float(d[2]),
														  'low':    float(d[3]),
														  'close':  float(d[4]),
														  'increases' : increases}

		f = open("PriceDic.txt", 'w')
		f.write(ticker + " : " + str(this_open_date) + " : " + str(self.priceDic[ticker][str(this_open_date)]))

	    return self.priceDic[ticker]

	def getPriceByDate(self, ticker, date, offset):
	    # offset is for choosing the price of date relative to
	    # the specified date, 1 for future 1 date, -1 for past 1 date
	    data = self.getHistoricalPrice(ticker)
	    #pos = None
	    #i = 0
	    #for d in data:
	        #if date == d['date']:
	        #    pos = 0
	        #    break
	        #elif date > d['date']:
	        #    pos = -0.5
	        #    break
	    #    i = i + 1

	    #if pos == None or ( offset==0 and pos != 0 ):
	    #    return None

	    #finalpos = int( i + pos - offset )
	    #finalpos = int( i - offset )
	    #if finalpos < 0 or finalpos >= len(data):
	    #    return None

	    #return data[offset]

	def main(self):
		self.getSymbolAndTweet("file:///Users/hpnhxxwn/Desktop/proj/cs502-capstone/aws_capstone_private/word2vec/CSV2/")
		self.tokenize_sentence()
		self.load_word2vec_model(size=self.opts.size)
		self.generate_tweet_vectors(size=self.opts.size)
		self.generate_vector_file()

if __name__ == "__main__":
	p = TweetPreProcess(parse_argv())
	p.main()


