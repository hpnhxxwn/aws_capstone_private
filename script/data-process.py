# read from any kafka broker and topic
# perform average price of stock every 5 sec
# write data back to kafka


import sys
from pyspark import SparkContext
from pyspark.streaming import StreamingContext
from pyspark.streaming.kafka import KafkaUtils
from kafka import KafkaProducer
from kafka.errors import KafkaError, KafkaTimeoutError

import json
import logging
import atexit
import time

logging.basicConfig()
logger = logging.getLogger('data-process')
logger.setLevel(logging.INFO)

topic = "stock-price"
broker = "localhost"
target_topic = "average-stock-price"
kafka_producer = None

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


	sc = SparkContext("local[2]", "AverageStockPrice")
	sc.setLogLevel("INFO")
	# data every 5 secs into Dstream
	ssc = StreamingContext(sc, 5)

	#alternatives for passing argument from command
	broker, topic, target_topic = sys.argv[1:]

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
