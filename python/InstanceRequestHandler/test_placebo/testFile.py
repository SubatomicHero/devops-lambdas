# import unittest, unittest2, os.path
# from Boto3wrapper import Boto3Wrapper
# from lambdafunc import *
# class MyTest(unittest2.TestCase):
#     def setUp(self):
#         def attach_placebo(self,session):
#             path = os.path.join(
#                 os.path.dirname(__file__),
#                 'placebo')
#             self.pill = placebo.attach(session, data_path=path)
#             return session
#         def attach_placebo2(self,client):
#             path = os.path.join(
#                 os.path.dirname(__file__),
#                 'placebo')
#             self.pill = placebo.attach(client, data_path=path)
#             return client
#         Boto3Wrapper.SESSION_CREATE_HOOK = attach_placebo
#         Boto3Wrapper.CLIENT_CREATE_HOOK = attach_placebo2
#         self.pill.playback()
#     def test_receive(self):
#         self.assertEqual(receiveMessage(), 2 )



sqs_read_url = 'https://sqs.us-east-1.amazonaws.com/179276412545/online-trial-control-test-OnlineTrialRequestSQS-LE73O10X02XK'
sqs_publish_url = 'https://sqs.us-east-1.amazonaws.com/179276412545/online-trial-control-test-OnlineTrialInstanceRequestSQS-1N2FII2ZEIOKE'


import unittest
import os

import boto3
from mock import Mock, mock

import placebo 

from InstanceRequestHandlerLambda import InstanceRequestHandler


IRH = InstanceRequestHandler
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

    

    @Mock(all)
    def test_describe_tags(self):
        self.pill.playback()
        result = IRH.findInstance()
        self.assertEqual(result['Addresses']['Tags']['Key'],"Account")

    @Mock(all)
    def test_receiveMessage(self):
        self.pill.playback()
        result = IRH.receiveMessage()
        self.assertEqual(result['Addresses']['ResponseMetadata']['RequestId'],"e62187a6-64ec-508a-a659-d6f238075c90")

    @Mock(all)
    def test_sendMessage(self):
        self.pill.playback()
        result = IRH.sendMessage()
        self.assertEqual(result['Addresses']['ResponseMetadata']['RequestId'],"e62187a6-64ec-508a-a659-d6f238075c90")

if __name__ == '__main__':
    unittest.main()