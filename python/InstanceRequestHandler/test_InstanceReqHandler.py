import boto, boto3, botocore.exceptions, requests, sure , time, json, unittest
from boto.exception import SQSError
from boto.sqs.message import RawMessage, Message
from moto import  mock_sqs, mock_ec2, mock_cloudformation
from nose.tools import assert_raises
from InstanceRequestHandlerLambda import InstanceRequestHandler

IRH = InstanceRequestHandler()
original_message = {'result': [{'updatedAt': '2015-08-10T06:53:11Z', 'lastName': 'Taylor', 'firstName': 'Dan', 'createdAt': '2014-09-18T20:56:57Z', 'email': 'daniel.taylor@alfresco.com', 'id': 1558511}], 'success': True, 'requestId': 'e809#14f22884e5f'}
       
class TestInstanceRequestHandler(unittest.TestCase):
    def test_instance(self):
        self.assertIsNotNone(IRH.cloud_client)
        self.assertIsNotNone(IRH.ec2_client)
        self.assertIsNotNone(IRH.sqs_client)
        self.assertIsNotNone(IRH.sqs_res)
    
    @mock_cloudformation
    @mock_ec2
    @mock_sqs
    def test_run_noNessage(self):
        print ("--Test Run function--")
        sqs = boto3.resource('sqs', region_name = 'us-east-1')
        q = sqs.create_queue(QueueName = 'readqueue')
        read_queue = sqs.get_queue_by_name(QueueName = 'readqueue')
        q1 = sqs.create_queue(QueueName = 'publishqueue')
        publish_queue = sqs.get_queue_by_name(QueueName = 'publishqueue')
        local_instance = InstanceRequestHandler(read_queue.url, publish_queue.url)
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')
        self.build_stack(instance.id)
        code = local_instance.run()
        self.assertEquals(code, 200)
        print("Test 'run function with no message' : passed")

    @mock_ec2
    @mock_sqs
    def test_run_noReadQueue(self):
        print ("--Test Run function--")
        sqs = boto3.resource('sqs', region_name = 'us-east-1')
        q = sqs.create_queue(QueueName = 'readqueue')
        read_queue = sqs.get_queue_by_name(QueueName = 'readqueue')
        q1 = sqs.create_queue(QueueName = 'publishqueue')
        publish_queue = sqs.get_queue_by_name(QueueName = 'publishqueue')
        local_instance = InstanceRequestHandler(read_queue.url, publish_queue.url)
        read_queue.delete()
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')
        self.build_stack(instance.id)
        code = local_instance.run()
        self.assertEquals(code, 'FAILURE')
        print("Test 'Failed run function with no read queue' : passed")

    @mock_cloudformation
    @mock_ec2
    @mock_sqs
    def test_run_withMessage(self):
        print ("--Test Run function--")
        sqs = boto3.resource('sqs', region_name = 'us-east-1')
        q = sqs.create_queue(QueueName = 'readqueue')
        messageBody = json.dumps(original_message)
        q.send_message(MessageBody = messageBody)
        read_queue = sqs.get_queue_by_name(QueueName = 'readqueue')
        q1 = sqs.create_queue(QueueName = 'publishqueue')
        publish_queue = sqs.get_queue_by_name(QueueName = 'publishqueue')
        local_instance = InstanceRequestHandler(read_queue.url, publish_queue.url)
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')
        self.build_stack(instance.id)
        code = local_instance.run()
        self.assertEquals(code, 200)
        print("Test 'run function with message' : passed")

    @mock_cloudformation
    @mock_ec2
    @mock_sqs
    def test_run_withMessageNoPublishQueue(self):
        print ("--Test Run function--")
        sqs = boto3.resource('sqs', region_name = 'us-east-1')
        q = sqs.create_queue(QueueName = 'readqueue')
        messageBody = json.dumps(original_message)
        q.send_message(MessageBody = messageBody)
        read_queue = sqs.get_queue_by_name(QueueName = 'readqueue')
        q1 = sqs.create_queue(QueueName = 'publishqueue')
        publish_queue = sqs.get_queue_by_name(QueueName = 'publishqueue')
        local_instance = InstanceRequestHandler(read_queue.url, publish_queue.url)
        publish_queue.delete()
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')
        self.build_stack(instance.id)
        code = local_instance.run()
        self.assertEquals(code, 'FAILURE')
        print("Test 'Failed run function with message and no publish queue' : passed")
    
    @mock_ec2
    def add_servers(self, ami_id = "ami-12345abc"):
        conn = boto.connect_ec2('the_key', 'the_secret')
        return conn.run_instances(ami_id).instances[0]

    @mock_cloudformation
    def build_stack(self, instance_id = "i-011e00f871fdcac11"):
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
            StackName = "trial_stack",
            TemplateBody = dummy_template_json,
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

    @mock_ec2
    @mock_cloudformation 
    def test_findStack(self):
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')
        self.build_stack(instance.id)
        stackList = IRH.describeStack()
        stackExpected = stackList[0]
        stackResult = IRH.findStack(stackList)
        assert stackExpected == stackResult
        print("Test 'Find stacks' : passed")
    
    @mock_cloudformation 
    def test_findUrl(self):
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')
        self.build_stack(instance.id)
        stackList = IRH.describeStack()
        trialStack = IRH.findStack(stackList)
        urlExpected = "https://requesttest.trial.alfresco.com/online-trial"
        urlResult = IRH.findOutputKeyValue(trialStack['Outputs'], 'Url')
        assert urlExpected == urlResult
        print("Test 'find stack Url' : passed")

    @mock_cloudformation 
    def test_findinstanceId(self):
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')
        self.build_stack(instance.id)
        stackList = IRH.describeStack()
        trialStack = IRH.findStack(stackList)
        instanceIdResult = IRH.findOutputKeyValue(trialStack['Outputs'], 'InstanceId')
        assert instance.id == instanceIdResult
        print("Test 'Find Stack instanceId' : passed")

    @mock_cloudformation
    @mock_ec2
    def test_findInstance(self):
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')
        self.build_stack(instance.id)
        instance_test = IRH.findInstance(instance.id)
        assert instance_test['ResponseMetadata']['HTTPStatusCode'] == 200
        assert instance_test['ResponseMetadata']["RetryAttempts"] == 0
        print("Test 'Find Instance' : passed")

    @mock_ec2
    @mock_cloudformation
    def test_allocateInstance(self):
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')
        self.build_stack(instance.id)
        tags = IRH.allocateInstance(instance.id)
        assert tags == True
        print("Test 'Allocate Stack ' : passed")

    @mock_sqs
    def test_receiveMessage(self):
        sqs = boto3.resource('sqs', region_name = 'us-east-1')
        q = sqs.create_queue(QueueName = 'readqueue')
        messageBody=json.dumps(original_message)
        q.send_message(MessageBody = messageBody)
        read_queue = sqs.get_queue_by_name(QueueName = 'readqueue')
        messageResult = IRH.receiveMessage(read_queue.url)
        assert messageResult['Messages'][0]['Body'] == json.dumps(original_message)
        print("Test 'received message' : passed")

    @mock_sqs
    def test_sendMessage(self):
        stack_id = 'i-1234'
        stack_url =  "https://requesttest.trial.alfresco.com/online-trial"
        sqs = boto3.resource('sqs', region_name = 'us-east-1')
        q1 = sqs.create_queue(QueueName = 'publishqueue')
        publish_queue = sqs.get_queue_by_name(QueueName = 'publishqueue')
        response = IRH.sendMessage(publish_queue.url, stack_id, stack_url, original_message)
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        assert response['ResponseMetadata']["RetryAttempts"] == 0
        assert response.get('Failed') == None
        print("Test 'send message' : passed")

if __name__ == '__main__':
  unittest.main()