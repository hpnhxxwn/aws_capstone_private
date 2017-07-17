#1. talk to any kafka and topic, configurable
#2. fetch stock price every second
from googlefinance import getQuotes
from kafka import KafkaProducer
from kafka.errors import KafkaError, KafkaTimeoutError
from apscheduler.schedulers.background import BackgroundScheduler

import atexit
import argparse
import logging
import json
import time


logger_format = '%(asctime)-15s %(message)s'
logging.basicConfig(format=logger_format)
logger = logging.getLogger('data-producer')
logger.setLevel(logging.DEBUG)

# symbol = 'GOOG'
# topic_name = 'stock'
# kafka_broker = '127.0.0.1:9092'


def shutdown_hook():
	try:
		logger.info('Flushing pending messages to kafka, timeout is set to 10s')
		producer.flush(10)
		logger.warn('shutdown resource')
	except KafkaError as ke:
		logger.warn('failed to flush kafka, caused by:%s', ke.message)
	finally:
		logger.info('Closing kafka connection')
		producer.close(10)
		schedule.shutdown()

def fetch_price(producer, symbol, topic_name):
	"""
	:param producer
	:param symbol - string
	"""
	logger.debug('Start to fetch stock price for %s', symbol)
	try:
		if topic_name == 'stock-price':
			topic = json.dumps(getQuotes(symbol))
			logger.debug('received stock price %s' % topic)
			producer.send(topic=topic_name, value=topic, timestamp_ms=time.time())
			logger.debug('Sent stock price for %s to Kafka', symbol)
	except KafkaTimeoutError as timeout_error:
		logger.warn('failed to send stock price for %s to kafka, caused by: %s', (symbol, timeout_error.message))	
	except Exception:
		logger.warn('failed to send stock price', )

if __name__ == '__main__':
	#argument parser
	parser = argparse.ArgumentParser()
	parser.add_argument('symbol', help='the symbol of the stack')
	parser.add_argument('topic_name', help='the kafka topic to push to')
	parser.add_argument('kafka_broker', help='the location of kafka broker')

	args = parser.parse_args()
	symbol = args.symbol
	topic_name = args.topic_name
	kafka_broker = args.kafka_broker

	producer = KafkaProducer(bootstrap_servers=kafka_broker)
	
	#1, simple scenario
	# fetch_price(producer, symbol)


	#2, scheduler scenario
	schedule = BackgroundScheduler()
	schedule.add_executor('threadpool')

	schedule.add_job(fetch_price, 'interval', [producer, symbol, topic_name], seconds=1, id=symbol)
	# - schedule and run the fetch_price function every second
    # schedule.every(1).second.do(fetch_price, producer, symbol)
	schedule.start()

	#register shutdown hook
	atexit.register(shutdown_hook)

	while True:
		time.sleep(1)
    	pass