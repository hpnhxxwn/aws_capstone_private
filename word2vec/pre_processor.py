from __future__ import print_function
import sys
#reload(sys)
import nltk
import re
from nltk.stem.porter import PorterStemmer
from nltk.stem.snowball import SnowballStemmer
#import word2vec
from gensim.models import Word2Vec
from gensim.models.word2vec import LineSentence
import glob
import datetime
import dateutil
import dateutil.parser
import argparse
import calendar
import copy
import io
import urllib2
import multiprocessing

MIN_DATE = {
    'bloomberg': datetime.datetime(2006, 10, 20),
    'reuters' : datetime.datetime(2006, 10, 20)
}
MAX_DATE = {
    'bloomberg': datetime.datetime(2013, 11, 26),
    'reuters' : datetime.datetime(2013, 11, 20)
}

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
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Read news and pre-process them")

    parser.add_argument("--start", metavar='YYYY-MM-DD',
        type=str, default='2006-10-20', help="start date")

    parser.add_argument("--end", metavar='YYYY-MM-DD',
        type=str, default='2013-11-20', help="end date")

    parser.add_argument("--new_source", metavar='bloomberg|reuters',
        type=str, default='reuters', help="News source, bloomberg or reuters")

    parser.add_argument("--src", metavar='URI',
        type=str, default='/Users/hpnhxxwn/Downloads/',
        help="data source directory")

    parser.add_argument("--dst", metavar='URI',
        type=str, default='file://',
        help="data destination directory")

    parser.add_argument("--max-lines", metavar='NUM', type=int,
        dest='max_lines', default=sys.maxint, help="maximum lines")

    parser.add_argument("--buf-size", metavar='NUM', type=int,
        dest='read_buf_size', default=16 * 1024 * 1024,
        help="read buffer size in bytes")

    parser.add_argument("--tagging", metavar='true/false', type=str,
        dest='tagging', default='true',
        help="enable or disable objects tagging")

    parser.add_argument("--procs", metavar='NUM', type=int,
        dest='procs', default=1,
        help="number of parallel process")

    parser.add_argument("--cross-account", action='store_true',
        dest='cross_account', default=False,
        help="enable cross-account copy")

    args = parser.parse_args()
    print(args.start)
    print(args.end)
    # check arguments
    args.start = dateutil.parser.parse(args.start) # set day
    args.end = dateutil.parser.parse(args.end)
    if args.start > args.end:
        fatal('start date %s is after end date %s' % \
            (args.start.strftime('%Y-%m-%d'), args.end.strftime('%Y-%m-%d')))

    if not (args.start >= MIN_DATE[args.new_source] and \
            args.end <= MAX_DATE[args.new_source]):
        fatal('date range must be from %s to %s for %s data' % \
            (MIN_DATE[args.new_source].strftime('%Y-%m-%d'),
             MAX_DATE[args.new_source].strftime('%Y-%m-%d'),
             args.new_source))

    args.tagging = eval(args.tagging.capitalize())

    return args

class PreProcess(object):
	def __init__(self, args):
		#args = parse_argv()
		self.stemmer = SnowballStemmer("english")
		self.start = "".join(args.start.split('-'))
		self.end = "".join(args.end.split('-'))
		self.src = args.src
		self.dest = args.dest
		self.new_source = args.new_source
		self.sents = []

	def get_news(self, date):
		path = "/Users/hpnhxxwn/Downloads/ReutersNews106521/" + date + "/us-abbott-results-idUSBRE96G0KW20130717"
		#input_file = open(path)
		raw = ""
		with open(path, "rt") as f:
			for line in f:
				if re.match("--", line):
					line = f.next();
				else:
					line = line.rstrip("\n")
					raw += line
		
		pattern = r"\w+(?:\w\.\w)*" 
	
		pat = re.compile(pattern)
		
		tokens = nltk.regexp_tokenize(raw, pat)
		
		print(tokens)
		return tokens

	def tokenize_sentence(self):
		path = self.src + self.start
		#raw = open(path, 'r').read()
		
		sentences = []
		raw = ""
		files = glob.glob(path)
		# iterate over the list getting each file 
		for fle in files:
			print(fle)
			with open(fle, "rt") as f:
				for line in f:
					if re.match("--", line):
						line = f.next();
					else:
						line = line.rstrip("\n")
						raw += line

			sent = nltk.sent_tokenize(raw)
			#sent = LineSentence
			for s in sent:
				#print("hehe")
				pattern = r"\w+(?:\w\.\w)*" 
				sentences.append(s)
		return sentences

	def tokenize_and_stem(self, sentences):
		#sents = []
		#stemmer = SnowballStemmer("english")
		for s in sentences:
			pattern = r"\w+(?:\w\.\w)*" 
			pat = re.compile(pattern)
			tokens = nltk.regexp_tokenize(s, pat)
			stems = [stemmer.stem(t) for t in tokens]
			self.sents.append(stems)

	
		#stems = [stemmer.stem(t) for t in sents]
		#print(sents)
		return sents

	def train_word2vec(self, sentences_tokens):
		model = Word2Vec(sentences_tokens, size=100, window=5, min_count=5, workers=4)
		return model

if __name__ == "__main__":
	args = parse_argv()
	obj = PreProcess(args)
	sentences = obj.tokenize_sentence()
	sents = obj.tokenize_and_stem(sentences)
	print(sents)
	model = train_word2vec(sents)
	model.save("word2vec_model")
	#tokens = get_news(20130717)
	#print(tokenize_and_stem(tokens))