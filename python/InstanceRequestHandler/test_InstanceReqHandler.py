import boto
import boto3
import botocore.exceptions
from boto.exception import SQSError
from boto.sqs.message import RawMessage, Message

import requests
import sure  # noqa
import time
import json 
from moto import  mock_sqs, mock_ec2, mock_cloudformation
from nose.tools import assert_raises
from InstanceRequestHandlerLambda import InstanceRequestHandler

import unittest

IRH = InstanceRequestHandler()


class TestInstanceRequestHandler(unittest.TestCase):
    
    @mock_cloudformation
    @mock_ec2
    @mock_sqs
    def test_run_noNessage(self):
        print ("--Test Run function--")
        # build dummy read queue
        sqs = boto3.resource('sqs', region_name='us-east-1')
        q = sqs.create_queue(QueueName='readqueue')
        read_queue = sqs.get_queue_by_name(QueueName='readqueue')
        

        q1 = sqs.create_queue(QueueName='publishqueue')
        publish_queue = sqs.get_queue_by_name(QueueName='publishqueue')

        local_instance = InstanceRequestHandler(read_queue.url, publish_queue.url )
        
        # build dummy instance
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')

        # test that with no messages, returns 200
        self.build_stack(instance.id)
        code = local_instance.run()
        self.assertEquals(code, 200)
        print("Test 'run function with no message' : passed")

    @mock_ec2
    @mock_sqs
    def test_run_noReadQueue(self):
        print ("--Test Run function--")
        # build dummy read queue
        sqs = boto3.resource('sqs', region_name='us-east-1')
        q = sqs.create_queue(QueueName='readqueue')
        read_queue = sqs.get_queue_by_name(QueueName='readqueue')
        

        q1 = sqs.create_queue(QueueName='publishqueue')
        publish_queue = sqs.get_queue_by_name(QueueName='publishqueue')

        local_instance = InstanceRequestHandler(read_queue.url, publish_queue.url )
        read_queue.delete()
        
        # build dummy instance
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')

        # test that with no messages, returns 200
        self.build_stack(instance.id)
        code = local_instance.run()
        self.assertEquals(code, 200)
        print("Test 'run function with no read queue' : passed")

        


    
    @mock_cloudformation
    @mock_ec2
    @mock_sqs
    def test_run_withMessage(self):
        print ("--Test Run function--")
        # build dummy read queue
        sqs = boto3.resource('sqs', region_name='us-east-1')
        q = sqs.create_queue(QueueName='readqueue')
        original_message = {'result': [{'updatedAt': '2015-08-10T06:53:11Z', 'lastName': 'Taylor', 'firstName': 'Dan', 'createdAt': '2014-09-18T20:56:57Z', 'email': 'daniel.taylor@alfresco.com', 'id': 1558511}], 'success': True, 'requestId': 'e809#14f22884e5f'}
        messageBody=json.dumps(original_message)
        q.send_message(MessageBody=messageBody)

        read_queue = sqs.get_queue_by_name(QueueName='readqueue')

        q1 = sqs.create_queue(QueueName='publishqueue')
        publish_queue = sqs.get_queue_by_name(QueueName='publishqueue')
        local_instance = InstanceRequestHandler(read_queue.url, publish_queue.url )
        
        # build dummy instance
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')

        # test that with no messages, returns 200
        self.build_stack(instance.id)
        code = local_instance.run()
        self.assertEquals(code, 200)
        print("Test 'run function with message' : passed")

    @mock_cloudformation
    @mock_ec2
    @mock_sqs
    def test_run_withMessageNoPublishQueue(self):
        print ("--Test Run function--")
        # build dummy read queue
        sqs = boto3.resource('sqs', region_name='us-east-1')
        q = sqs.create_queue(QueueName='readqueue')
        original_message = {'result': [{'updatedAt': '2015-08-10T06:53:11Z', 'lastName': 'Taylor', 'firstName': 'Dan', 'createdAt': '2014-09-18T20:56:57Z', 'email': 'daniel.taylor@alfresco.com', 'id': 1558511}], 'success': True, 'requestId': 'e809#14f22884e5f'}
        messageBody=json.dumps(original_message)
        q.send_message(MessageBody=messageBody)

        read_queue = sqs.get_queue_by_name(QueueName='readqueue')

        q1 = sqs.create_queue(QueueName='publishqueue')
        publish_queue = sqs.get_queue_by_name(QueueName='publishqueue')
        local_instance = InstanceRequestHandler(read_queue.url, publish_queue.url )
        publish_queue.delete()
        
        # build dummy instance
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')

        # test that with no messages, returns 200
        self.build_stack(instance.id)
        code = local_instance.run()
        self.assertEquals(code, 200)
        print("Test 'run function with message and no publish queue' : passed")
    
    
    @mock_ec2
    def add_servers(self, ami_id="ami-12345abc"):
        conn = boto.connect_ec2('the_key', 'the_secret')
        return conn.run_instances(ami_id).instances[0]

    @mock_cloudformation
    def build_stack(self, instance_id="i-011e00f871fdcac11"):
        dummy_template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Description": "Stack 1",
            "Resources": {
                "TrialEc2Instance": {
                    "Type": "AWS::EC2::Instance",
                    "Properties": {
                        "ImageId": "ami-d3adb33f",
                        "KeyName": "dummy",
                        "InstanceType": "t2.micro",
                        "Tags": [
                            {
                                "Key": "Allocated",
                                "Value": "false"
                            }
                        ]
                    },
                },
            },
            "Outputs": {
                "Type": {
                    "Description": "The type of stack this is; Trial, etc.",
                    "Value": "Trial"
                },
                "Stage": {
                    "Description": "The stage of stack this is; test, etc",
                    "Value": "test"
                },
                "Url": {
                    "Description": "The Public Url that allows users access",
                    "Value": "https://requesttest.trial.alfresco.com/online-trial"
                },
                "InstanceId": {
                    "Description": "The id of the ec2 instance created by this stack",
                    "Value": instance_id
                },
            }
        }


        dummy_template_json = json.dumps(dummy_template)


        # cf = boto3.client('cloudformation')
        return IRH.cloud_client.create_stack(
            StackName="trial_stack",
            TemplateBody=dummy_template_json,
        )

    @mock_cloudformation  
    def test_describeStack(self):
        self.build_stack()
        stackList = IRH.describeStack()
        stack = stackList[0]
        self.assertIsNotNone(stackList)
        self.assertEqual(len(stackList), 1)

        stack['StackStatus'].should.equal('CREATE_COMPLETE')
        print("Test 'describe stacks' : passed")

    @mock_cloudformation 
    def test_findStack(self):
        self.build_stack()
        stackList = IRH.describeStack()
        stackExpected = stackList[0]
        stackResult = IRH.findStack(stackList)
        assert stackExpected == stackResult
        print("Test 'Find stacks' : passed")
    
    @mock_cloudformation 
    def test_findUrl(self):
        self.build_stack()
        stackList = IRH.describeStack()
        trialStack = IRH.findStack(stackList)
        urlExpected = "https://requesttest.trial.alfresco.com/online-trial"
        urlResult = IRH.findOutputKeyValue(trialStack['Outputs'], 'Url')
        assert urlExpected == urlResult
        print("Test 'find stack Url' : passed")

    @mock_cloudformation 
    def test_findinstanceId(self):
        self.build_stack()
        stackList = IRH.describeStack()
        trialStack = IRH.findStack(stackList)
        instanceIdExpected = "i-011e00f871fdcac11"
        instanceIdResult = IRH.findOutputKeyValue(trialStack['Outputs'], 'InstanceId')
        assert instanceIdExpected == instanceIdResult
        print("Test 'Find Stack instanceId' : passed")

    @mock_cloudformation
    @mock_ec2
    def test_findInstance(self):
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')
        self.build_stack(instance.id)
        instance = IRH.findInstance(instance.id)

        assert instance['ResponseMetadata']['HTTPStatusCode'] == 200
        assert instance['ResponseMetadata']["RetryAttempts"] == 0
        print("Test 'Find Instance' : passed")

    @mock_ec2
    @mock_cloudformation
    def test_allocateInstance(self):
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')
        self.build_stack(instance.id)
        tags = IRH.allocateInstance(instance.id)
        assert tags['ResponseMetadata']['HTTPStatusCode'] == 200
        assert tags['ResponseMetadata']["RetryAttempts"] == 0
        
        print("Test 'Allocate Stack ' : passed")

    @mock_sqs
    def test_receiveMessage(self):
        original_message = {'result': [{'updatedAt': '2015-08-10T06:53:11Z', 'lastName': 'Taylor', 'firstName': 'Dan', 'createdAt': '2014-09-18T20:56:57Z', 'email': 'daniel.taylor@alfresco.com', 'id': 1558511}], 'success': True, 'requestId': 'e809#14f22884e5f'}
        sqs = boto.connect_sqs('the_key', 'the_secret')
        queue = sqs.create_queue('OnlineTrialRequestSQS', visibility_timeout=60)
        messageBody=json.dumps(original_message)
        queue.write(queue.new_message(messageBody))

        queue.count().should.equal(1)
        messages = sqs.receive_message(queue, number_messages=1, visibility_timeout=0)

        assert len(messages) == 1

        queue.count().should.equal(1)
        messageResult = messages[0].get_body() 
        assert messageResult == json.dumps(original_message)
        print("Test 'received message' : passed")
        return json.loads(messageResult)

    @mock_sqs
    def test_sendMessage(self):
        original_message = {'result': [{'updatedAt': '2015-08-10T06:53:11Z', 'lastName': 'Taylor', 'firstName': 'Dan', 'createdAt': '2014-09-18T20:56:57Z', 'email': 'daniel.taylor@alfresco.com', 'id': 1558511}], 'success': True, 'requestId': 'e809#14f22884e5f'}
        original_message['stack_id'] = 'i-1234'
        original_message['stack_url'] =  "https://requesttest.trial.alfresco.com/online-trial"
        sqs = boto3.resource('sqs')
        queue = sqs.create_queue(QueueName='OnlineTrialRequestSQS')
        response = queue.send_message(MessageBody=json.dumps(original_message))
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        assert response['ResponseMetadata']["RetryAttempts"] == 0
        assert response.get('Failed') == None
        # assert response.get('MD5OfMessageBody') == '7d8643aa0e8110fd8e26462e9e01600c'
        print("Test 'send message' : passed")
        return response.get('Failed')

  
if __name__ == '__main__':
  unittest.main()