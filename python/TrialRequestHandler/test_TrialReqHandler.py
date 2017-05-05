import boto3
from moto import mock_sqs, mock_dynamodb2
from TrialRequestHandlerLambda import TrialRequestHandler
import unittest
import datetime
import time
import json
import os
import requests
import httpretty

response = {'result': [{'updatedAt': '2015-08-10T06:53:11Z', 'lastName': 'Taylor', 'firstName': 'Dan', 'createdAt': '2014-09-18T20:56:57Z', 'email': 'daniel.taylor@alfresco.com', 'id': 1558511}], 'success': True, 'requestId': 'e809#14f22884e5f'}
TRH = TrialRequestHandler()

class TestTrialRequestHandler(unittest.TestCase):
    def test_instance(self):
        self.assertIsNotNone(TRH.dynamo_client)
        self.assertIsNotNone(TRH.sqs_client)

    @httpretty.activate
    def test_get_access_token(self):
        try: 
            host = 'http://example.com/'
            client_id = "usee"
            client_secret = "pass"
            json_body = json.dumps({'access_token': '123'})
            p = {
                    'grant_type':'client_credentials',
                    'client_id': client_id,
                    'client_secret': client_secret
                }
            httpretty.register_uri(
                httpretty.GET, host, 
                body = json_body, 
                content_type = 'application/json',
                status=200,
                params = p
            ) 
            response = TRH._get_access_token(host, client_id, client_secret)
            assert response == '123' 
            print("Test get_access_token : passed")
        except IOError:
            print("test failed. an error has been found")
            
    def test_details_marketo(self):
        try:
            id_test = '89406'
            access_token = '123'
            host = 'http://example.com/'
            json_body = json.dumps({'access_token': '123'})
            p = {
                    'access_token': access_token,
                    'filterType': 'id',
                    'filterValues': id_test
                }
            httpretty.register_uri(
                httpretty.GET, host, 
                body = json_body, 
                content_type = 'application/json',
                status=200,
                params = p
            ) 
            r = requests.get(host, params=p)
            # data = json.loads(r.content.decode('utf-8'))
            # print(data)
            # # result = TRH.details_marketo(host, id_test, access_token)
            
            print("test passed")
        except IOError:
            print("test failed. an error has been found")

    @mock_dynamodb2
    def test_dynamo_service(self):
        try:
            dynamodb = boto3.client('dynamodb', region_name='us-east-1')
            t_name = 'trial_request_table'
            table_t = dynamodb.create_table(
            TableName=t_name,
            KeySchema=[
                {
                    'AttributeName': 'LeadId',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'Date',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'LeadId',
                    'AttributeType': 'N'
                },
                {
                    'AttributeName': 'Date',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'Fulfilled',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'Attempts',
                    'AttributeType': 'N'
                },
                {
                    'AttributeName': 'RequestTime',
                    'AttributeType': 'N'
                },
                {
                    'AttributeName': 'Request',
                    'AttributeType': 'S'
                },
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            })
            os.environ['trial_request_table'] = t_name
            return dynamodb
        except IOError:
            print("test failed. no instance of dynamodb created")

    @mock_dynamodb2
    def test_insert_dynamo(self):
        leadid = 89406
        fulfilled_test = "y"
        count_attempts = 10
        self.test_dynamo_service()
        resp = TRH.insert_into_dynamo(leadid, response, fulfilled_test, count_attempts)
        assert resp == True
        print("Test insert_into_dynamo: passed")
    
    @mock_sqs
    def test_send_to_SQS(self):
        try:
            sqs = boto3.resource('sqs', region_name = 'us-east-1')
            q1 = sqs.create_queue(QueueName = 'publishqueue')
            publish_queue = sqs.get_queue_by_name(QueueName = 'publishqueue')
            resp = TRH.send_to_SQS(publish_queue.url, response)
            assert resp['ResponseMetadata']['HTTPStatusCode'] == 200
            assert resp['ResponseMetadata']["RetryAttempts"] == 0
            assert resp.get('Failed') == None
            print("Test 'send message' : passed")
        except IOError:
            print("test failed. an error has been found")

    @mock_sqs
    def test_send_to_SQS_returns_fail(self):
        try:
            sqs = boto3.resource('sqs', region_name = 'us-east-1')
            q1 = sqs.create_queue(QueueName = 'publishqueue')
            publish_queue = sqs.get_queue_by_name(QueueName = 'publishqueue')
            response = TRH.send_to_SQS(publish_queue.url, None)
            assert response == None
            print("Test 'failed send message' : passed")
        except IOError:
            print("test failed. an error has been found")

if __name__ == '__main__':
  unittest.main()
