# read from any kafka broker and topic
#relay to redis channel


from kafka import KafkaConsumer

import redis

import argparse
import logging
# import json
import atexit

logging.basicConfig()
logger = logging.getLogger('redis-publisher')
logger.setLevel(logging.DEBUG)


def shutdown_hook(kafka_consumer):
    logger.info('closing kafka client')
    kafka_consumer.close()


if __name__ == '__main__':
    # -args parser
    parser = argparse.ArgumentParser()
    parser.add_argument('topic_name', help='the kafka topic to parse')
    parser.add_argument('kafka_broker', help='the location of kafka')
    parser.add_argument('redis_host', help='the ip of the redis server')
    parser.add_argument('redis_port', help='the port of the redis server')
    parser.add_argument('redis_channel', help='the channel to publish to')

    args = parser.parse_args()
    topic_name = args.topic_name
    kafka_broker = args.kafka_broker
    redis_host = args.redis_host
    redis_port = args.redis_port
    redis_channel = args.redis_channel





    # - create a kafka client
    kafka_consumer = KafkaConsumer(
    	topic_name, 
    	bootstrap_servers=kafka_broker,
    	enable_auto_commit = False
    )

    # - create redis client
    redis_client = redis.StrictRedis(host=redis_host, port=redis_port)

    for msg in kafka_consumer:
    	logger.info('received data from kafka %s' % str(msg))
    	redis_client.publish(redis_channel, msg.value)

    shutdown_hook(kafka_consumer)
