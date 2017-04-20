import boto, boto3, botocore.exceptions, requests, sure , time, json, unittest
from boto.exception import SQSError
from boto.sqs.message import RawMessage, Message
from moto import  mock_sqs, mock_ec2, mock_cloudformation, mock_dynamodb2
from nose.tools import assert_raises
from FulfillmentHandlerLambda import FulfillmentHandler

FH = FulfillmentHandler()
       
class TestFulfillmentHandlerLambda(unittest.TestCase):
    def test_instance(self):
        self.assertIsNotNone(FH.sns_client)
        self.assertIsNotNone(FH.dynamo_client)

    
    @mock_dynamodb2
    def createTable(self):
        try:
            dynamodb = boto3.client('dynamodb', region_name='us-east-1')
            table = dynamodb.create_table(
                TableName = 'trial_request_table',
                KeySchema = [
                    {
                        'AttributeName': 'LeadId',
                        'KeyType': 'HASH'  # Partition key
                    },
                    {
                        'AttributeName': 'Date',
                        'KeyType': 'RANGE'  # Sort key
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
                ProvisionedThroughput = {
                    'ReadCapacityUnits': 10,
                    'WriteCapacityUnits': 10
                }
            )
            return dynamodb
        except IOError:
            print("test failed. no instance of dynamodb created")
        
    def test_readFromTable(self):
        dynamodb = self.createTable()
        print(FH.readFromTable(dynamodb, 'trial_request_table'))
       
if __name__ == '__main__':
  unittest.main()