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

os.environ['sqs_url'] = ""
os.environ['trial_request_table'] = ""
os.environ['api_host'] = ""
os.environ['client_id'] = ""
os.environ['client_secret'] = ""

response = {'result': [{'updatedAt': '2015-08-10T06:53:11Z', 'lastName': 'Taylor', 'firstName': 'Dan', 'createdAt': '2014-09-18T20:56:57Z', 'email': 'daniel.taylor@alfresco.com', 'id': 1558511}], 'success': True, 'requestId': 'e809#14f22884e5f'}
TRH = TrialRequestHandler()

class TestTrialRequestHandler(unittest.TestCase):
    def test_instance(self):
        self.assertIsNotNone(TRH.dynamo_client)
        self.assertIsNotNone(TRH.sqs_client)

    # @httpretty.activate
    # def test_assign_user_to_stack(self):
    #     httpretty.register_uri(
    #         httpretty.GET,
    #         "https://453-liz-762.mktorest.com/identity/oauth/token",
    #         body=json.dumps(response)
    #     )
    #     r =  TRH._get_access_token('https://453-liz-762.mktorest.com/')
        # self.assertTrue(response)

    # def test_details_marketo(self):
    #     try:
    #         id_test = '89406'
    #         print ('f')
    #         result = TRH.details_marketo(id_test)
    #         expected_result = {"requestId": "aa09#15b3ee9bc02", "success": True, "result": [{"firstName": "UNKNOWN", "lastName": "UNKNOWN", "id": 89406, "updatedAt": "2017-03-16T11:48:42Z", "email": "daniel.taylor@alfresco.com", "createdAt": "2016-08-23T11:30:55Z"}]}
    #         print (result)
    #         assert result == expected_result
    #         print("test passed")
    #     except IOError:
    #         print("test failed. an error has been found")

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
