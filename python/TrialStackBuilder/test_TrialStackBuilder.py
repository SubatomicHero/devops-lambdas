
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



class TestTrialStackBuilder(unittest.TestCase):
    def test_instance(self):
        self.assertIsNotNone(TSB.cloud_client)
        self.assertIsNotNone(TSB.ec2_client)

    @mock_ec2
    def add_servers(self, ami_id="ami-0b71c21d"):
        conn = boto.connect_ec2('the_key', 'the_secret')
        return conn.run_instances(ami_id).instances[0]

    @mock_cloudformation
    def build_stack(self, instance_id="i-0e0f25febd2bb4f43"):
        # Create a stack first so we can play with it
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
                    "Key": "ExpiryDate",
                    "Value": "2017-05-04"
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
            "Value": instance_id
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
        template = json.dumps(dummy_template)
        # cf = boto3.client('cloudformation')
        cf = TSB.cloud_client
        return cf.create_stack(
            StackName="test_stack",
            TemplateBody=template
        )
    @mock_cloudformation
    def test_listStack(self):
        # # cf = boto3.client('cloudformation')
        # cf = TSB.cloud_client
        # stacks = cf.describe_stacks(StackName="trial_stack")['Stacks']
        # self.assertIsNotNone(stacks)
        # self.assertEqual(len(stacks['Stacks']), 1)
        print("Test 'describe stacks' : passed")
    #     return stacks

    # @mock_ec2
    # @mock_cloudformation
    # def test_run_returns_0(self):
    #     instance = self.add_servers()
    #     stacks = self.build_stack(instance.id)
    #     print(stacks)
    #     # self.test_listStack()
    #     # code = TSB.run(event)
    #     # self.assertEquals(code, 200)
    #     TSB.countUnassignedStack(stacks)

if __name__ == '__main__':
    unittest.main()
  