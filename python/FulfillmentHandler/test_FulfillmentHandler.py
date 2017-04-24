import boto, boto3, botocore.exceptions, requests, sure , time, json, unittest, time, random
from boto.exception import SQSError
from boto.sqs.message import RawMessage, Message
from moto import  mock_sqs, mock_ec2, mock_cloudformation, mock_dynamodb2, mock_sns
from nose.tools import assert_raises
from FulfillmentHandlerLambda import FulfillmentHandler

FH = FulfillmentHandler()


class TestFulfillmentHandlerLambda(unittest.TestCase):
    def test_instance(self):
        self.assertIsNotNone(FH.sns_res)
        self.assertIsNotNone(FH.dynamo_res)
    
    @mock_dynamodb2
    def createDynamodb(self):
        try:
            dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
            return dynamodb
        except IOError:
            print("test failed. no instance of dynamodb created")

    @mock_dynamodb2
    def createTestTable(self, dynamodb, name):
        try:
            table = dynamodb.create_table(
                TableName = name,
                KeySchema = [
                    {
                        'AttributeName': 'LeadId',
                        'KeyType': 'HASH'  
                    },
                    {
                        'AttributeName': 'Date',
                        'KeyType': 'RANGE'  
                    }
                ],
                AttributeDefinitions = [
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
                ],
                ProvisionedThroughput = {
                    'ReadCapacityUnits': 10,
                    'WriteCapacityUnits': 10
                }
            )
        except IOError:
            print("test failed. no table created")

    def putItem(self, dynamodb, name, id, f):
        try:
            table = dynamodb.Table(name)
            table.put_item(
                Item = {
                    'LeadId': str(id),
                    'Fulfilled' : f,
                    'Date' : str(table.creation_date_time)
                }
            )
        except IOError:
            print("test failed. no instance table updated")

    @mock_dynamodb2
    def test_readFromTable_multipleReq(self):
        name = 'trial_request_table'
        dynamodb = self.createDynamodb()
        self.createTestTable(dynamodb, name)
        id1 = random.randint(0, 100)
        self.putItem(dynamodb, name, id1, 'y')
        id2 = random.randint(0, 100)
        self.putItem(dynamodb, name, id2, 'n')
        leadId = FH.readFromTable(dynamodb, name)
        assert leadId == str(id2)
        print ('Test dynamodb read leadId from table (multiple unfulfilled request table): Passed\n')

    @mock_dynamodb2
    def test_readFromTable_noReq(self):
        name = 'trial_request_table'
        dynamodb = self.createDynamodb()
        self.createTestTable(dynamodb, name)
        id1 = random.randint(0, 100)
        self.putItem(dynamodb, name, id1, 'y')
        id1 = random.randint(0, 100)
        leadId = FH.readFromTable(dynamodb, name)
        assert leadId == None
        print ('Test dynamodb read leadId from table (no unfulfilled request table): Passed\n')

    def test_createObject(self):
        id1 = random.randint(0, 100)
        obj = FH.createMessageObject(id1)
        assert obj['lead']['StringValue'] == str(id1)
        print ('Test create object: Passed\n')

    @mock_sns
    def test_publishTopicSNS(self):
        sns = boto3.resource('sns', region_name='us-east-1')
        topic = sns.Topic('arn:aws:dynamodb:us-east-1:123456789012:table/books_table')
        sns_client = boto3.client('sns', region_name='us-east-1')
        id1 = random.randint(0, 100)
        obj = { 
            'source': {
                'DataType': 'string',
                'StringValue': 'onlinetrial'
            },
            'lead': {
                'DataType': 'string',
                'StringValue': str(id1)
            }
        }
        response = FH.publishTopicSNS(sns_client, topic, obj)
        print ('Test create object: Passed\n')
    
if __name__ == '__main__':
  unittest.main()