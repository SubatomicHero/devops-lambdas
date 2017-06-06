import json
from datetime import datetime, timedelta
import unittest
import os
import boto

os.environ['days_to_stop'] = '3'
os.environ['stack_type'] = 'Trial'
os.environ['stage'] = 'test'

from triallifecycle import LifecycleHandler
from moto import mock_cloudformation, mock_ec2, mock_opsworks
from botocore.exceptions import ClientError
from nose.tools import assert_raises

HANDLER = LifecycleHandler(
    os.environ['stack_type'],
    os.environ['days_to_stop'],
)

class TestTrialLifeCycle(unittest.TestCase):
    """TestTrialLifecycle"""
    def test_instance(self):
        """test_instance"""
        self.assertIsNotNone(HANDLER.cfn_client)
        self.assertIsNotNone(HANDLER.ec2_client)
        self.assertEqual(HANDLER.expiry_key, 'ExpiryDate')
        self.assertEqual(len(HANDLER.states), 2)

    @mock_opsworks
    @mock_cloudformation
    def build_stack(self, instance_id="i-0e0f25febd2bb4f43"):
        """build_stack"""
        # mock opsworks too
        stack_id = HANDLER.ops_client.create_stack(
            Name="test_stack_1",
            Region="us-east-1",
            ServiceRoleArn="service_arn",
            DefaultInstanceProfileArn="profile_arn"
        )['StackId']

        os.environ['layer_id'] = HANDLER.ops_client.create_layer(
            StackId=stack_id,
            Type="custom",
            Name="TestLayer",
            Shortname="TestLayerShortName"
        )['LayerId']

        HANDLER.ops_client.create_instance(
            StackId=stack_id,
            LayerIds=[os.environ['layer_id']],
            InstanceType='t2.micro',
            Hostname='e6br9y'
        )

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
                                "Value": "04-05-2017"
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
            },
            "Tags": [
                {
                    'Value': 'Trial',
                    'Key': 'Type'
                },
                {
                    'Value': 'test',
                    'Key': 'Stage'
                }
            ]
        }
        template = json.dumps(dummy_template)
        return HANDLER.cfn_client.create_stack(
            StackName="test_stack",
            TemplateBody=template
        )

    @mock_cloudformation
    def test_describe_stacks(self):
        """test_describe_stacks"""
        self.build_stack()
        stacks = HANDLER.describe_stacks()
        self.assertIsNotNone(stacks)
        self.assertEqual(len(stacks), 1)

        os.environ['stage'] = 'prod'
        stacks = HANDLER.describe_stacks()
        self.assertEqual(len(stacks), 0)

        os.environ['stage'] = 'test'
        stacks = HANDLER.describe_stacks()
        self.assertIsNotNone(stacks)
        self.assertEqual(len(stacks), 1)

    @mock_ec2
    def add_servers(self, ami_id="ami-0b71c21d"):
        """add_servers"""
        conn = boto.connect_ec2('the_key', 'the_secret')
        return conn.run_instances(ami_id).instances[0]

    @mock_ec2
    def test_describe_tags(self):
        """test_describe_tags"""
        # test that if none is passed, we receive none
        instance_id = None
        tags = HANDLER.describe_tags(instance_id)
        self.assertIsNone(tags)

        # Test that with a valid instance id, we get the tags we expect
        instance = self.add_servers()
        instance.add_tag(HANDLER.expiry_key, "05-04-2017")
        response = HANDLER.describe_tags(instance.id)
        self.assertEquals(response['ResponseMetadata']['HTTPStatusCode'], 200)
        self.assertEquals(len(response['Tags']), 1)
        self.assertEquals(response['Tags'][0]['Key'], HANDLER.expiry_key)
        self.assertEquals(response['Tags'][0]['Value'], "05-04-2017")

    @mock_ec2
    def test_describe_instances(self):
        """test_describe_instances"""
        instance_id = ""
        response = HANDLER.describe_instances(instance_id)
        self.assertIsNone(response)

        instance = self.add_servers()
        response = HANDLER.describe_instances(instance.id)
        obj = response['Reservations'][0]['Instances'][0]
        self.assertIsNotNone(response)
        self.assertIsNotNone(obj)
        self.assertEquals(obj['State']['Name'], 'running')

    @mock_ec2
    def test_update_tags(self):
        """test_update_tags"""
        instance_id = ""
        response = HANDLER.update_tags(instance_id, [])
        self.assertIsNone(response)
        tags = [{'Key':'blah', 'Value':'blah'}]
        response = HANDLER.update_tags(instance_id, tags)
        self.assertIsNone(response)

        instance = self.add_servers()
        instance.add_tag(HANDLER.expiry_key, "05-04-2017")
        response = HANDLER.describe_tags(instance.id)
        self.assertEquals(response['Tags'][0]['Value'], "05-04-2017")
        HANDLER.update_tags(instance.id, [
            {
                'Key': HANDLER.expiry_key,
                'Value': "08-04-2017"
            }
        ])
        response = HANDLER.describe_tags(instance.id)
        self.assertEquals(response['Tags'][0]['Value'], "08-04-2017")

    @mock_cloudformation
    def test_get_instance_id(self):
        """test_get_instance_id"""
        stack = {}
        uid = HANDLER.get_instance_id(stack)
        self.assertIsNone(uid)

        instance = self.add_servers()
        self.build_stack(instance.id)
        stacks = HANDLER.describe_stacks()
        stack = stacks[0]
        uid = HANDLER.get_instance_id(stack)
        self.assertEquals(uid, instance.id)

    # @mock_opsworks
    # def test_stop_instance(self):
    #     """test_stop_instance"""
    #     self.build_stack()
    #     stack = HANDLER.describe_stacks()[0]

    #     response = HANDLER.stop_instance(stack)
    #     self.assertIsNone(response)

    @mock_opsworks
    @mock_cloudformation
    def test_stop_instance_if_expired(self):
        """test_stop_instance_if_expired"""
        # tests that an instance is stopped if the expiry date
        #  is before today and the instance is running
        today = datetime.strptime(datetime.today().strftime("%d-%m-%Y"), "%d-%m-%Y")
        yesterday = today - timedelta(days=1)
        instance = self.add_servers()
        instance.add_tag(HANDLER.expiry_key, str(yesterday.date().strftime("%d-%m-%Y")))
        response = HANDLER.describe_tags(instance.id)
        self.assertEquals(response['Tags'][0]['Value'], str(yesterday.date().strftime("%d-%m-%Y")))
        self.assertTrue(today > yesterday)
        response = HANDLER.describe_instances(instance.id)
        obj = response['Reservations'][0]['Instances'][0]
        self.assertEquals(obj['State']['Name'], 'running')

        # The instance is running and expired yesterday
        self.build_stack(instance.id)
        HANDLER.run()

        # instance should have new expiry date and be stopped
        response = HANDLER.describe_instances(instance.id)
        obj = response['Reservations'][0]['Instances'][0]
        self.assertEquals(obj['State']['Name'], 'stopped')
        ned = yesterday + timedelta(days=HANDLER.days_to_stop)

        response = HANDLER.describe_tags(instance.id)
        self.assertEquals(response['Tags'][0]['Value'], str(ned.date().strftime("%d-%m-%Y")))

    @mock_ec2
    @mock_cloudformation
    def test_terminate_stack_if_stopped(self):
        """test_terminate_stack_if_stopped"""
        # tests that a cloudformation stack is terminated if the instance is stopped and expired
        today = datetime.strptime(datetime.today().strftime("%d-%m-%Y"), "%d-%m-%Y")
        yesterday = today - timedelta(days=1)
        instance = self.add_servers()
        instance.add_tag(HANDLER.expiry_key, str(yesterday.date().strftime("%d-%m-%Y")))
        self.build_stack(instance.id)
        stack = HANDLER.describe_stacks()[0]
        # lets stop the instance, as per the logic
        HANDLER.stop_instance(stack)

        # run the handler, the stack should be terminated. Describing would return an ClientError
        # as it no longer exists
        HANDLER.run()
        with assert_raises(ClientError):
            HANDLER.cfn_client.describe_stacks(
                StackName='test_stack'
            )

    @mock_cloudformation
    @mock_ec2
    def test_run_returns_0(self):
        """test_run_returns_0"""
        today = datetime.strptime(datetime.today().strftime("%d-%m-%Y"), "%d-%m-%Y")
        yesterday = today - timedelta(days=1)
        instance = self.add_servers()
        instance.add_tag(HANDLER.expiry_key, str(yesterday.date().strftime("%d-%m-%Y")))
        self.build_stack(instance.id)
        code = HANDLER.run()

        self.assertEquals(code, 0)

if __name__ == '__main__':
    unittest.main()
  