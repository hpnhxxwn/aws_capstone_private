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

model = Word2Vec.load('tweet_model')

def buildWordVector(text, size=100):
	vec = np.zeros(size).reshape((1, size))
	count = 0.
	for word in text:
		try:
			vec += model[word].reshape((1, size))
			count += 1.
		except KeyError:
			continue
	if count != 0:
		vec /= count
	return vec

text = "http:// smq.tc/1VvJJhE < Try Jason Bond Stock Trading Chatroom Risk FREE for a limited time only.! $ CELG $ ARIA $ BA"
def generate_tweet_vectors(size=100):
	#for symbol in tweetDic:
	#	vecList[symbol] = {}
	#	for d in tweetDic[symbol]:
	#		if d not in vecList[symbol]:
	#			vecList[symbol][d] = []

	#		for s in tweetDic[symbol][d]:
				#if d in self.priceDic[symbol]:
	#			print(s)
	#			vecList[symbol][d].append({buildWordVector(s): priceDic[symbol][d]['increases']})
	vecList = []
	vecList.append([buildWordVector(text), 1.01])
	print(vecList)
	return vecList


def generate_vector_file():
	with open("vector.txt", 'wb') as f: 
		#for symbol in self.vecList:
		#	for d in self.vecList[symbol]:
			for v in vecList:
				#print(v[0].reshape(1, 100))
				f.write("{")
				for item in v[0][0]:
					#print(item)
					f.write(str(item) + " ")
				f.write(": ")
				f.write(str(v[1]))
				f.write("}")

vecList = generate_tweet_vectors()
generate_vector_file()

#print(vecList)