"""
Test case for Instance Request Handler
"""
import json
import unittest
import boto
import boto3

from moto import mock_sqs, mock_ec2, mock_cloudformation
from InstanceRequestHandlerLambda import InstanceRequestHandler

IRH = InstanceRequestHandler()
ORIGINAL_MESSAGE = {
    'result': [
        {
            'updatedAt': '2015-08-10T06:53:11Z',
            'lastName': 'Taylor',
            'firstName': 'Dan',
            'createdAt': '2014-09-18T20:56:57Z',
            'email': 'daniel.taylor@alfresco.com',
            'id': 1558511
        }
    ],
    'success': True,
    'requestId': 'e809#14f22884e5f'
}

class TestInstanceRequestHandler(unittest.TestCase):
    """
    Tests for Instance Request Handler
    """
    def test_instance(self):
        """
        Test the instance is created
        """
        self.assertIsNotNone(IRH.cloud_client)
        self.assertIsNotNone(IRH.ec2_client)
        self.assertIsNotNone(IRH.sqs_client)
        self.assertIsNotNone(IRH.sqs_res)

    @mock_cloudformation
    @mock_ec2
    @mock_sqs
    def test_run_no_message(self):
        """
        Test if there is no message
        """
        print "--Test Run function--"
        sqs = boto3.resource('sqs')
        queue = sqs.create_queue(QueueName='readqueue')
        read_queue = sqs.get_queue_by_name(QueueName='readqueue')
        queue_1 = sqs.create_queue(QueueName='publishqueue')
        publish_queue = sqs.get_queue_by_name(QueueName='publishqueue')
        local_instance = InstanceRequestHandler(read_queue.url, publish_queue.url)
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')
        self.build_stack(instance.id)
        code = local_instance.run()
        self.assertEquals(code, 200)
        print "Test 'run function with no message' : passed"

    @mock_ec2
    @mock_sqs
    def test_run_no_read_queue(self):
        """
        Tests if there is no read queue
        """
        print "--Test Run function--"
        sqs = boto3.resource('sqs')
        queue = sqs.create_queue(QueueName='readqueue')
        read_queue = sqs.get_queue_by_name(QueueName='readqueue')
        queue_1 = sqs.create_queue(QueueName='publishqueue')
        publish_queue = sqs.get_queue_by_name(QueueName='publishqueue')
        local_instance = InstanceRequestHandler(read_queue.url, publish_queue.url)
        read_queue.delete()
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')
        self.build_stack(instance.id)
        code = local_instance.run()
        self.assertEquals(code, 'FAILURE')
        print "Test 'Failed run function with no read queue' : passed"

    @mock_cloudformation
    @mock_ec2
    @mock_sqs
    def test_run_with_message(self):
        """
        Tests run with a valid message
        """
        print "--Test Run function--"
        sqs = boto3.resource('sqs')
        queue = sqs.create_queue(QueueName='readqueue')
        message_body = json.dumps(ORIGINAL_MESSAGE)
        queue.send_message(MessageBody=message_body)
        read_queue = sqs.get_queue_by_name(QueueName='readqueue')
        queue1 = sqs.create_queue(QueueName='publishqueue')
        publish_queue = sqs.get_queue_by_name(QueueName='publishqueue')
        local_instance = InstanceRequestHandler(read_queue.url, publish_queue.url)
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')
        self.build_stack(instance.id)
        code = local_instance.run()
        self.assertEquals(code, 200)
        print "Test 'run function with message' : passed"

    @mock_cloudformation
    @mock_ec2
    @mock_sqs
    def test_run_no_publish_queue(self):
        """
        Tests run with no publish queue
        """
        print "--Test Run function--"
        sqs = boto3.resource('sqs')
        queue = sqs.create_queue(QueueName='readqueue')
        message_body = json.dumps(ORIGINAL_MESSAGE)
        queue.send_message(MessageBody=message_body)
        read_queue = sqs.get_queue_by_name(QueueName='readqueue')
        queue_1 = sqs.create_queue(QueueName='publishqueue')
        publish_queue = sqs.get_queue_by_name(QueueName='publishqueue')
        local_instance = InstanceRequestHandler(read_queue.url, publish_queue.url)
        publish_queue.delete()
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')
        self.build_stack(instance.id)
        code = local_instance.run()
        self.assertEquals(code, 'FAILURE')
        print "Test 'Failed run function with message and no publish queue' : passed"

    @mock_ec2
    def add_servers(self, ami_id="ami-12345abc"):
        """
        Quickly adds ec2 instances
        """
        conn = boto.connect_ec2('the_key', 'the_secret')
        return conn.run_instances(ami_id).instances[0]

    @mock_cloudformation
    def build_stack(self, instance_id="i-011e00f871fdcac11"):
        """
        Quickly builds a dummy cfn stack
        """
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
        return IRH.cloud_client.create_stack(
            StackName="trial_stack",
            TemplateBody=dummy_template_json,
        )

    @mock_cloudformation
    def test_describe_stack(self):
        """
        Tests describing all the stacks
        """
        self.build_stack()
        stack_list = IRH.describe_stack()
        stack = stack_list[0]
        self.assertIsNotNone(stack_list)
        self.assertEqual(len(stack_list), 1)
        assert stack['StackStatus'] == 'CREATE_COMPLETE'
        print "Test 'describe stacks' : passed"

    @mock_ec2
    @mock_cloudformation
    def test_findstack(self):
        """
        Tests finding a stack
        """
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')
        self.build_stack(instance.id)
        stack_list = IRH.describe_stack()
        stack_expected = stack_list[0]
        stack_result = IRH.find_stack(stack_list)
        assert stack_expected == stack_result
        print "Test 'Find stacks' : passed"

    @mock_cloudformation
    def test_findurl(self):
        """
        Tests getting the url output of a stack
        """
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')
        self.build_stack(instance.id)
        stacklist = IRH.describe_stack()
        trialstack = IRH.find_stack(stacklist)
        urlexpected = "https://requesttest.trial.alfresco.com/online-trial"
        urlresult = IRH.find_output_key_value(trialstack['Outputs'], 'Url')
        assert urlexpected == urlresult
        print "Test 'find stack Url' : passed"

    @mock_cloudformation
    def test_findinstanceid(self):
        """
        Tests getting the instance id output of a stack
        """
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')
        self.build_stack(instance.id)
        stacklist = IRH.describe_stack()
        trialstack = IRH.find_stack(stacklist)
        instanceidresult = IRH.find_output_key_value(trialstack['Outputs'], 'InstanceId')
        assert instance.id == instanceidresult
        print "Test 'Find Stack instanceId' : passed"

    @mock_cloudformation
    @mock_ec2
    def test_findinstance(self):
        """
        Tests finding a valid instance using an instance id
        """
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')
        self.build_stack(instance.id)
        instance_test = IRH.find_instance(instance.id)
        assert instance_test['ResponseMetadata']['HTTPStatusCode'] == 200
        assert instance_test['ResponseMetadata']["RetryAttempts"] == 0
        print "Test 'Find Instance' : passed"

    @mock_ec2
    @mock_cloudformation
    def test_allocateinstance(self):
        """
        Tests allocating an instance
        """
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')
        self.build_stack(instance.id)
        tags = IRH.allocate_instance(instance.id)
        assert tags
        print "Test 'Allocate Stack ' : passed"

    @mock_sqs
    def test_receivemessage(self):
        """
        Tests receiving a message
        """
        sqs = boto3.resource('sqs')
        queue = sqs.create_queue(QueueName='readqueue')
        message_body = json.dumps(ORIGINAL_MESSAGE)
        queue.send_message(MessageBody=message_body)
        read_queue = sqs.get_queue_by_name(QueueName='readqueue')
        messageresult = IRH.receive_message(read_queue.url)
        assert messageresult['Messages'][0]['Body'] == json.dumps(ORIGINAL_MESSAGE)
        print "Test 'received message' : passed"

    @mock_sqs
    def test_send_message(self):
        """
        Tests sending a message
        """
        stack_id = 'i-1234'
        stack_url = "https://requesttest.trial.alfresco.com/online-trial"
        sqs = boto3.resource('sqs')
        queue1 = sqs.create_queue(QueueName='publishqueue')
        publish_queue = sqs.get_queue_by_name(QueueName='publishqueue')
        response = IRH.send_message(publish_queue.url, stack_id, stack_url, ORIGINAL_MESSAGE)
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        assert response['ResponseMetadata']["RetryAttempts"] == 0
        assert response.get('Failed') is None
        print "Test 'send message' : passed"

if __name__ == '__main__':
    unittest.main()
