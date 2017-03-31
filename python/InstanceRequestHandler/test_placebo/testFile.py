import unittest
import os

import boto3
from mock import Mock, mock

import placebo 
import json

from InstanceRequestHandlerLambda import InstanceRequestHandler

addresses_result_one = {
    "Addresses": [
        {
            "InstanceId": "",
            "PublicIp": "192.168.0.1",
            "Domain": "standard"
        }
    ]
}
sqs_read_url = 'https://sqs.us-east-1.amazonaws.com/179276412545/online-trial-control-test-OnlineTrialRequestSQS-LE73O10X02XK'
        

IRH = InstanceRequestHandler()
class TestPlacebo(unittest.TestCase):

    def setUp(self):
        self.environ = {}
        self.environ_patch = mock.patch('os.environ', self.environ)
        self.environ_patch.start()
        credential_path = os.path.join(os.path.dirname(__file__), 'cfg',
                                       'aws_credentials')
        self.environ['AWS_SHARED_CREDENTIALS_FILE'] = credential_path
        self.data_path = os.path.join(os.path.dirname(__file__), 'responses')
        self.data_path = os.path.join(self.data_path, 'saved')
        self.session = boto3.Session(region_name='us-east-1')
        self.pill = placebo.attach(self.session, self.data_path)
        self.pill.record(services='ec2')

    def tearDown(self):
        pass

    def test_ec2(self):
        self.pill.save_response(
            'ec2', 'DescribeAddresses', addresses_result_one)
        self.pill.playback()
        ec2_client = self.session.client('ec2')
        result = ec2_client.describe_addresses()
        self.assertEqual(result['Addresses'][0]['PublicIp'], '192.168.0.1')
        result = ec2_client.describe_addresses()
        self.assertEqual(result['Addresses'][0]['PublicIp'], '192.168.0.1')

    @Mock
    def test_describe_tags(self):
        self.pill.playback()
        result = IRH.findInstance()
        self.assertEqual(result['Addresses']['Tags']['Key'],"Stage")
        self.assertEqual(result['Addresses']['Tags']['Key'],"Type")

   
    def test_receive_message(self):
        self.pill.playback()
        sqs_client = self.session.client('sqs')
        result = sqs_client.receive_message(QueueUrl=sqs_read_url,)
        self.assertEqual(result['Addresses']['ResponseMetadata']['RequestId'],"e62187a6-64ec-508a-a659-d6f238075c90")

    @Mock
    def test_sendMessage(self):
        self.pill.playback()
        original_message = {'result': [{'updatedAt': '2015-08-10T06:53:11Z', 'lastName': 'Taylor', 'firstName': 'Dan', 'createdAt': '2014-09-18T20:56:57Z', 'email': 'daniel.taylor@alfresco.com', 'id': 1558511}], 'success': True, 'requestId': 'e809#14f22884e5f'}
        message = json.dumps(original_message)
        result = IRH.sendMessage("2", "url", message )
        self.assertEqual(result['Addresses']['ResponseMetadata']['RequestId'],"e62187a6-64ec-508a-a659-d6f238075c90")

if __name__ == '__main__':
    unittest.main()