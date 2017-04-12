import boto3
from moto import mock_sqs
from moto import mock_dynamodb2
from TRH import TrialRequestHandler
import datetime
import time
import json
import os


os.environ['sqs_url'] = ""
os.environ['trial_request_table'] = ""
os.environ['api_host'] = ""
os.environ['client_id'] = ""
os.environ['client_secret'] = ""


def test_details_marketo():
    try:
        id_test = '89406'
        handler = TrialRequestHandler()
        os.environ['api_host'] = "https://453-liz-762.mktorest.com/"
        os.environ['client_id'] = "35a7e1a3-5e60-40b2-bd54-674680af2adc"
        os.environ['client_secret'] = "iPPgKiB224jsa02duwPcKy9ox7078P7S"
        result = handler.details_marketo(id_test)
        expected_result = {"requestId": "aa09#15b3ee9bc02", "success": True, "result": [{"firstName": "UNKNOWN", "lastName": "UNKNOWN", "id": 89406, "updatedAt": "2017-03-16T11:48:42Z", "email": "daniel.taylor@alfresco.com", "createdAt": "2016-08-23T11:30:55Z"}]}
        assert result == expected_result
        print("test passed")
    except IOError:
        print("test failed. an error has been found")

@mock_dynamodb2
def test_dynamo_service():
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
def test_insert_dynamo():
    response = {'result': [{'updatedAt': '2015-08-10T06:53:11Z', 'lastName': 'Taylor', 'firstName': 'Dan', 'createdAt': '2014-09-18T20:56:57Z', 'email': 'daniel.taylor@alfresco.com', 'id': 1558511}], 'success': True, 'requestId': 'e809#14f22884e5f'}
    leadid = 89406
    fulfilled_test = "y"
    count_attempts = 10
    handler = TrialRequestHandler()
    os.environ
    resp = handler.insert_into_dynamo(test_dynamo_service(), leadid, response, fulfilled_test, count_attempts)
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 200
    print("test passed")


@mock_sqs
def test_SQS_service():
    try:
        sqs = boto3.client('sqs', region_name='us-west-2')
        queue = sqs.create_queue(QueueName='OnlineTrialRequestSQS', Attributes={'DelaySeconds': '5'})
        queue_url_message = sqs.get_queue_url(QueueName='OnlineTrialRequestSQS')
        queue_url = queue_url_message['QueueUrl']
        os.environ['sqs_url'] = queue_url
        return sqs
    except IOError:
        print("test failed. no instance of sqs created")

@mock_sqs
def test_send_to_SQS():
    try:
        response_m = {'result': [{'updatedAt': '2015-08-10T06:53:11Z', 'lastName': 'Taylor', 'firstName': 'Dan', 'createdAt': '2014-09-18T20:56:57Z', 'email': 'daniel.taylor@alfresco.com', 'id': 1558511}], 'success': True, 'requestId': 'e809#14f22884e5f'}
        sqs_s = test_SQS_service()
        handler = TrialRequestHandler()
        resp = handler.send_to_SQS(sqs_s, response_m)
        assert resp['ResponseMetadata']['HTTPStatusCode'] == 200
        print(resp)
        print(resp.get('MessageId'))
        print(resp.get('MD5OfMessageBody'))
        print("test passed")
    except IOError:
        print("test failed. an error has been found")



#test_details_marketo()
test_insert_dynamo()
test_send_to_SQS()

