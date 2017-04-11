
from moto import mock_cloudformation, mock_ec2, mock_s3, mock_lambda
import unittest
import boto, boto3
from botocore.exceptions import ClientError
import requests
import sure  # noqa
import time
import json 
from nose.tools import assert_raises
from TrialStackBuilderLambda import TrialStackBuilder
import uuid


# parameters
event = {
  "account": "123456789012",
  "region": "us-east-1",
  "detail": {},
  "detail-type": "Scheduled Event",
  "source": "aws.events",
  "time": "1970-01-01T00:00:00Z",
  "id": "cdc73f9d-aea9-11e3-9d5a-835b769c0d9c",
  "resources": [
    "arn:aws:events:us-east-1:123456789012:rule/my-schedule"
  ]
}
stage = 'test'
template_bucket_name = 'online-trial-control-tes-onlinetrialstacktemplate-ak21n1yv3vdc'
stack_count = '5'



TSB = TrialStackBuilder()

dummy_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Stack 1",
    "Resources": {            
    "EC2Instance1": {
        "Type": "AWS::EC2::Instance",
        "Properties": {
            "ImageId": "ami-d3adb33f",
            "KeyName": "dummy",
            "InstanceType": "t2.micro",
            "Tags": [
            {
                "Key": "Allocated",
                "Value": "False"
            }
            ]
        }
        }
    },
    "Outputs": {
        "Type": {
            "Value": "Trial"
            },
            "InstanceId": {
            "Value": "i-0e0f25febd2bb4f43"
            },
        "PublicIp": {
            "Value": "54.210.56.83"
        },
        "Stage": {
            "Value": "test"
        },
        "Url": {
            "Value":"https://e6br9y.trial.alfresco.com"
        }
    }
}

class TestTrialStackBuilder(unittest.TestCase):
    def test_instance(self):
        self.assertIsNotNone(TSB.cloud_client)
        self.assertIsNotNone(TSB.ec2_client)

    @mock_cloudformation
    def build_stack(self, instance_id="i-0e0f25febd2bb4f43"):
        
        template = json.dumps(dummy_template)
        return TSB.cloud_client.create_stack(
            StackName="test_stack",
            TemplateBody=template
        )
        
    @mock_cloudformation
    def test_listStack(self):
        self.build_stack()
        stacks = TSB.listStack()
        self.assertIsNotNone(stacks)
        self.assertEqual(len(stacks), 1)
        print("Test 'list stacks' : passed")

    @mock_s3
    @mock_ec2
    @mock_cloudformation
    def test_run_returns_0(self):
        stacks = self.build_stack()
        code = TSB.run(event)
        self.assertEquals(code, 200)

    @mock_cloudformation
    def test_findInstanceId(self):
        self.build_stack()
        stacks = TSB.listStack()
        instanceIdResult = TSB.findInstanceId(stacks[0]['Outputs'])
        instanceIdExpected = "i-0e0f25febd2bb4f43"
        assert instanceIdExpected == instanceIdResult
        print("Test 'Find Stack instanceId' : passed")
    
    @mock_cloudformation
    @mock_ec2
    def test_findInstance(self):
        self.build_stack()
        stacks = TSB.listStack()
        instanceId = TSB.findInstanceId(stacks[0]['Outputs'])
        instance = TSB.findInstance(instanceId)
        assert instance['ResponseMetadata']['HTTPStatusCode'] == 200
        assert instance['ResponseMetadata']["RetryAttempts"] == 0
        print("Test 'Find Instance' : passed")

    @mock_cloudformation
    @mock_ec2
    def test_findUnassignedInstance(self):
        self.build_stack()
        stacks = TSB.listStack()
        instanceId = TSB.findInstanceId(stacks[0]['Outputs'])
        instance = TSB.findInstance(instanceId)
        unassigned = TSB.findUnassignedInstance(instance['Tags'])
        assert unassigned == False
        print("Test 'Find Unassigned Instance' : passed")

    @mock_cloudformation
    @mock_ec2
    def test_countUnassignedStack(self):
        self.build_stack()
        stacks = TSB.listStack()
        count = TSB.countUnassignedStack(stacks)
        assert count == 0
        print("Test 'Count Unassigned Stack ' : passed")

    @mock_cloudformation
    def test_createStack(self):
        # template = json.dumps(dummy_template)
        # name = str(uuid.uuid1())
        # name =  'TrialStack'+name.replace('-','')
        # stack = TSB.cloud_client.create_stack(
        #     StackName=name,
        #     TemplateBody=template
        # )
        stack = TSB.createStack()
        print(stack)
        # assert stack['ResponseMetadata']['HTTPStatusCode'] == 200
        # assert stack['ResponseMetadata']["RetryAttempts"] == 0
        print("Test 'Create Stack' : passed")
if __name__ == '__main__':
    unittest.main()
  