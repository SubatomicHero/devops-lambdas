import boto, boto3, botocore.exceptions, requests, sure , time, json, unittest
from boto.exception import SQSError
from boto.sqs.message import RawMessage, Message
from moto import  mock_sqs, mock_ec2, mock_cloudformation, mock_dynamodb
from nose.tools import assert_raises
from FulfillmentHandlerLambda import FulfillmentHandler

FH = FulfillmentHandler()
       
class TestFulfillmentHandlerLambda(unittest.TestCase):
    def test_instance(self):
        self.assertIsNotNone(FH.sns_client)
        self.assertIsNotNone(FH.dynamo_client)
    
    @mock_dynamodb
    def test_rereadFromTable(self):
        dynamodb = boto.connect_dynamodb()
        # response = dynamo_client.create_table(
        #     TableName='table',
        #      AttributeDefinitions=[
        #       {
        #           'AttributeName': 'LeadId',
        #           'AttributeType': 'S',
        #       },
        #       ],
        #       KeySchema=[
        #           {
        #               'AttributeName': 'LeadId',
        #               'KeyType': 'HASH',
        #           }
        #       ],
        #       ProvisionedThroughput={
        #           'ReadCapacityUnits': 5,
        #           'WriteCapacityUnits': 5,
        #       },
        #   )
        table_schema = dynamodb.create_schema(
            hash_key_name='leadID',
            hash_key_proto_value=str,
            range_key_name='subject',
            range_key_proto_value=str
        )
        table = dynamodb.create_table(
            name='test_table',
            schema=table_schema,
            read_units=10,
            write_units=10
        )
        FH.readFromTable(table)
if __name__ == '__main__':
  unittest.main()