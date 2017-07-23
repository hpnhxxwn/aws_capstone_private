#!/usr/bin/env python

# Copyright 2017, Nan Dun <nan.dun@acm.org>
# All rights reserved.

from __future__ import print_function

import argparse
import copy
import datetime
import decimal
import io
import json
import logging
import multiprocessing
import os.path
import sys
import time

import boto3
import botocore

from collections import Counter
from boto3.dynamodb.conditions import Key, Attr

from common import *
from geo import NYCBorough, NYCGeoPolygon
from tasks import TaskManager

from utilities import *

logging.basicConfig()
logger = logging.getLogger(os.path.basename(__file__))

def parse_argv():
    o = Options()
    o.add('--src', metavar='URI', type=str,
        default='s3://aws-nyc-taxi-data', help="data source directory")
    o.add('-s', '--start',  metavar='NUM', type=int,
        default=0, help="start record index")
    o.add('-e', '--end',  metavar='NUM', type=int,
        default=4 * 1024 ** 3, help="end record index")
    o.add('-r', '--report', action='store_true',
        default=False, help="report results")
    o.add('-p', '--procs', type=int, dest='nprocs',
        default=1, help="number of concurrent processes")
    o.add('-w', '--worker', action='store_true',
        default=False, help="worker mode")
    o.add('--sleep', type=int,
        default=10, help="worker sleep time if no task")

    opts = o.load()

    if opts.start < 0 or opts.start > opts.end:
        fatal("invalid range [%d, %d]" % (opts.start, opts.end))

    logger.setLevel(opts.verbose)
    return opts



class DB:
    def __init__(self, opts):
        self.ddb = boto3.resource('dynamodb',
            region_name=opts.region, endpoint_url=opts.ddb_endpoint)
        tag = getTagName()
        self.table_name_A = tag + "_tweet_individual_sentiment"
        self.table_name_B = tag + "_average_sentiment"
        self.table_tweet_indivisual_sentiment = self.ddb.Table(self.table_name_A)
        self.table_average_sentiment = self.ddb.Table(table_name_B)
        try:
            assert self.table_tweet_indivisual_sentiment.table_status == 'ACTIVE'
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.warning("table %s does not exist" % self.table_tweet_indivisual_sentiment.table_name)
            logger.debug("create table %s/%s" % \
                (opts.ddb_endpoint, self.table_tweet_indivisual_sentiment.table_name))
            self.create_table_A()

        try:
            assert self.table_average_sentiment.table_status == 'ACTIVE'
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.warning("table %s does not exist" % self.table_average_sentiment.table_name)
            logger.debug("create table %s/%s" % \
                (opts.ddb_endpoint, self.table_average_sentiment.table_name))
            self.create_table_B()

    def create_table_A(self):
        self.table_tweet_indivisual_sentiment = self.ddb.create_table(
            TableName=self.table_name_A,
            KeySchema=[
                {
                    'AttributeName': 'symbol',
                    'KeyType': 'HASH'   # partition key
                },
                {
                    'AttributeName': 'timestamp',
                    'KeyType': 'RANGE'  # sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'symbol',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'timestamp',
                    'AttributeType': 'N'
                },
                {
                    'AttributeName': 'tweet_create_time',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'user_name',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'text',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'individual_sentiment',
                    'AttributeType': 'N'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 2,
                'WriteCapacityUnits': 10
            }
        )

    def create_table_B(self):
        self.table_average_sentiment = self.ddb.create_table(
            TableName=self.table_name_B,
            KeySchema=[
                {
                    'AttributeName': 'symbol',
                    'KeyType': 'HASH'   # partition key
                },
                {
                    'AttributeName': 'average_sentiment',
                    'KeyType': 'RANGE'  # sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'symbol',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'count',
                    'AttributeType': 'N'
                },
                {
                    'AttributeName': 'average_sentiment',
                    'AttributeType': 'N'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 2,
                'WriteCapacityUnits': 10
            }
        )

    def query(start_time, end_time, symbol):
        print("Query tweets one hour before")
        response = table.query(
            ProjectionExpression="symbol, timestamp, individual_sentiment",
            ScanIndexForward=False,
            KeyConditionExpression=Key('symbol').eq(symbol) & Key('timestamp').ge(start_time) & Key('timestamp').lt(end_time)
        )

        return response['Items']

    def put_item_to_tweet_table(self, message):
        self.table_tweet_indivisual_sentiment.put_item(
            Item={
                    'symbol': message['symbol'],
                    'timestamp': message['timestamp'],
                    'user_name': message['user_name'],
                    'tweet_create_time': message['tweet_create_time'],
                    #'retweets': message['retweets'],
                    #'favorite': message['favorite'],
                    'text': message['text'],
                    #'geo': message['geo'],
                    #'mentions': message['mentions'],
                    'id': message['id'],
                    #'link': message['link'],
                    'individual_sentiment': message['individual_sentiment']
                })

    def put_item_to_sentiment_table(self, ave_sent, count):
        try:
            self.table_average_sentiment.update_item(
                Key={
                    'key': message['symbol']
                },
                UpdateExpression="SET count = count + :inc, average_sentiment = :ave_sent",
                ConditionExpression="count = :curr",
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':curr': count,
                    ':ave_sent': ave_sent
                },
                ReturnValues="UPDATED_NEW"
            )
            return -1
        except boto.dynamodb.exceptions.DynamoDBConditionalCheckFailedError:
            response = self.table_average_sentiment.get_item(
                Key={
                    'symbol': message['symbol']
                }
            )
            return response['Item']['count']
     
    def get_item_from_tweet_table(self, timestamp):
        try:
             response = self.table_tweet_indivisual_sentiment.get_item(
                Key={
                    'symbol': message['symbol'],
                    'timestamp': message['timestamp']
                }
            )
         except botocore.exceptions.ClientError as e:
            logger.warning(e.response['Error']['Message'])
            response = None
         except KeyError:
            logger.warning('item () => not found')
            response = None
        finally:
            return response 

    def get_item_from_sentiment_table(self, symbol):
        try:
            response = self.table_average_sentiment.get_item(
                Key={
                    'symbol': symbol
                }
            )
        except botocore.exceptions.ClientError as e:
            logger.warning(e.response['Error']['Message'])
            response = None
        except KeyError:
            logger.warning('item () => not found')
            response = None
            self.table_average_sentiment.put_item(
                Item={
                    'symbol': symbol,
                    'count': 0,
                    'average_sentiment': 0.
                    }
                )
        finally:
            return response
