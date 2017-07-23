import atexit
import logging
import json
import sys
import time

from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError, KafkaTimeoutError
from pyspark import SparkContext
from pyspark.streaming import StreamingContext
from pyspark.streaming.kafka import KafkaUtils
#from pyspark_cassandra import streaming

from zipkin.api import api as zipkin_api
from py_zipkin.zipkin import zipkin_span
import requests
from datetime import datetime, timedelta
from cassandra.cluster import Cluster

import boto3
from utilities import *
import db
from getSymbolAndTweet import *
from gensim.models import Word2Vec
from gensim.models.word2vec import LineSentence
import nltk
import re
from nltk.stem.porter import PorterStemmer
from nltk.stem.snowball import SnowballStemmer
import numpy as np
from numpy import array
#def getEC2Tag():
#	ec2 = boto3.resource('ec2', region_name='us-west-2')
#	ec2.get_all_images(filters={'tag-key': 'Name'. 'resource-id': instance_id})




target_topic = None
brokers = "localhost:9092"
kafka_producer = None
self.stemmer = SnowballStemmer("english")
#contact_points = "localhost"
#keyspace = "bittiger"
#tweet_table = "stock_tweet"
def tokenize_and_stem(sentences):
	sents = []
	#stemmer = SnowballStemmer("english")
	for s in sentences:
		pattern = r"\w+(?:\w\.\w)*" 
		pat = re.compile(pattern)
		tokens = nltk.regexp_tokenize(s, pat)
		stems = [stemmer.stem(t) for t in tokens]
		sents.append(stems)

	return sents

def tokenize_sentence(text):
	sentStem = []
	sents = []
			
	sent = nltk.sent_tokenize(t)
	sentStem = tokenize_and_stem(sent)
	for s in sentStem:
		sents.append(s)

	return sents

def load_word2vec_model():
	model = Word2Vec.load('tweet_model')

	return model

def load_nlp_model():
	with open('sgd.pkl', 'rb') as f:
		return pickle.load(f)

def sentiment_score(vec):
	feature_vector = pd.DataFrame(data=vec)
	feature_matrix = feature.as_matrix()
	pred = model.predict(feature_matrix)
	return pred

def buildWordVector(text, model, size=32):
	#print(text)
	sents = tokenize_sentence(text)

	tmp = np.zeros(size)
	vec = tmp.reshape((1, size))
	count = 0.
	for sent in sents:
		for word in sent:
			try:
				vec += model[word].reshape((1, size))
			continueount += 1.
			except KeyError:
				continue

	if count != 0:
		vec /= count
	return vec

last_time = -1.

def process_tweet_stream(stream, db, model):
    #def send_to_kafka(rdd):

    def send_tweet_to_dynamoDB(rdd):
        results = rdd.collect()
        for tweet in results:
            symbol = tweet[0]
            user_id = int(tweet[1])
            user_name = tweet[2]
            tweet_create_time = tweet[3]
            tweet_text = str(tweet[4].encode('utf-8'))
            tweet_text = tweet_text.replace("[", "")
            tweet_text = tweet_text.replace("]", "")

            timestamp = tweet[5]

            tweet_vec = buildWordVector(tweet_text)

            score = sentiment_score(tweet_vec)
            message = {'symbol':symbol, 'tweet_create_time':tweet_create_time, 'user_name':user_name, 'text':tweet_text, 'id':user_id, 'individual_sentiment': score, 'timestamp': timestamp}
            #stmt = "INSERT INTO %s (stock_symbol, user_id, user_screen_name, tweet_create_time, tweet) VALUES ('%s', '%s', '%s', '%s', '%s')" % (tweet_table, symbol.encode('utf-8'), user_id, user_name.encode('utf-8'), tweet_create_time.encode('utf-8'), tweet_text)
            
            print(message)
            if last_time == -1.:
            	last_time = timestamp

            total = 0;
            c = 0;
            if (last_time < timestamp - 3600):
            	query = db.query(last_time, timestamp - 3600, symbol)
            	c = len(query)
	            for res in query:
	            	total += res['individual_sentiment']

            last_time = query[0]['timestamp']

            resp = db.get_item_from_sentiment_table(symbol)
            count = 0
            average_sentiment = score
            if resp != None:
            	values = resp['Item']
            	count = values['count']
            	average_sentiment = ((values['average_sentiment'] * count) - total + score) / (count - c + 1)
            	#count += 1

            db.put_item_to_sentiment_table(average_sentiment, count)
            #session.execute(stmt)
            db.put_item_to_tweet_table(message)

    tweets = stream.map(lambda x: x[1].split('^$$^')).filter(lambda y: len(y[0]) > 0)
    #.map(lambda y: {"stock_symbol":y[0], "user_id":y[1], "user_screen_name":y[2], "tweet_create_time":y[3], "tweet":y[4]})
    tweets.pprint()
    tweets.foreachRDD(send_tweet_to_dynamoDB)


def shutdown_hook():
	try:
		logger.info('Flushing pending messages to kafka, timeout is set to 10s')
		producer.flush(10)
		logger.warn('shutdown resource')
	except KafkaError as ke:
		logger.warn('failed to flush kafka, caused by:%s', ke.message)
	finally:
		try:
			logger.info('Closing kafka connection')
			producer.close(10)
		except Exception as e:
			logger.warn('Failed to close kafka connection, caused by: %s', e.message)




def proces_stream(stream):
    '''
    a function stream processing data and send back to kafka
    :param stream: kafka_streaming
    :return: None
    '''
    # - send data to kafka with symbol, time and average stock price
    def send_to_kafka(rdd):
        results = rdd.collect()
        for r in results:
            data = json.dumps(
                {
                    'symbol': r[0],
                    'timestamp': time.time(),
                    'average': r[1]
                }
            )
            try:
                logger.info('Sending average price %s to kafka' % data)
                kafka_producer.send(target_topic, value=data)
            except KafkaError as error:
                logger.warn('Failed to send average stock price to kafka, caused by: %s', error.message)

    # - map data to symbol and price
    def pair(data):
        record = json.loads(data[1].decode('utf-8'))[0]
        return record.get('StockSymbol'), (float(record.get('LastTradePrice')), 2)

    stream.map(pair)\
        .reduceByKey(lambda a, b: (a[0] + b[0], a[1] + b[1]))\
        .map(lambda (k, v): (k, v[0]/v[1])).foreachRDD(send_to_kafka)

if __name__ == '__main__':
	# -kafka broker, kafka oringal topic, kafka target topic
	if len(sys.argv) != 4:
		print("usage: data-process.py kafka-original-topic kafka-new-topic")
		exit(1)

	db = DB()
	#pp = PreProcess()
	w2v_model = load_word2vec_model() 
	nlp_model = load_nlp_model()

	sc = SparkContext("local[2]", "AverageStockPrice")
	sc.setLogLevel("INFO")
	# data every 5 secs into Dstream
	ssc = StreamingContext(sc, 5)

	#alternatives for passing argument from command
	broker, target_topic = sys.argv[1:]
	topic = getTagName()

	# connect kafak to stream
	directKafkaStream = KafkaUtils.createDirectStream(ssc, [topic], {'metadata.broker.list': broker})
	proces_stream(directKafkaStream)
	# directKafkaStream.foreachRDD(process)

	kafka_producer = KafkaProducer(
		bootstrap_servers=broker
	)
	ssc.start()
	ssc.awaitTermination()

	atexit.register(shutdown_hook, kafka_producer)


	# - create SparkContext and StreamingContext
	sc = SparkContext("local[*]", "StockAveragePrice")
	sc.setLogLevel('INFO')
	# every 5 seconds
	ssc = StreamingContext(sc, 5)

	#session = startCassandraSession(contact_points)
	#session.set_keyspace(keyspace)
	tweetDirectKafkaStream = KafkaUtils.createDirectStream(ssc, [topic], {'metadata.broker.list': brokers})

	process_tweet_stream(tweetDirectKafkaStream, keyspace, tweet_table, session)

	ssc.start()
	ssc.awaitTermination()



