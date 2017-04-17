import boto, boto3, botocore.exceptions, requests, sure , time, json, unittest
from boto.exception import SQSError
from boto.sqs.message import RawMessage, Message
from moto import  mock_sqs, mock_ec2, mock_cloudformation
from nose.tools import assert_raises
from FulfillmentHandlerLambda import FulfillmentHandler

FH = FulfillmentHandler()
       
class TestFulfillmentHandlerLambda(unittest.TestCase):
    def test_instance(self):
        self.assertIsNotNone(FH.sns_client)
        self.assertIsNotNone(FH.dynamo_client)

if __name__ == '__main__':
  unittest.main()