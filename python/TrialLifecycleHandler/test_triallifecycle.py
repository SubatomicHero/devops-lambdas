from triallifecycle import LifecycleHandler
from moto import mock_cloudformation, mock_ec2
import unittest
from datetime import datetime, timedelta
import json
import boto
from botocore.exceptions import ClientError
from nose.tools import assert_raises

handler = LifecycleHandler()

class TestTrialLifeCycle(unittest.TestCase):
      def test_instance(self):
          self.assertIsNotNone(handler.cfn_client)
          self.assertIsNotNone(handler.ec2_client)
          self.assertEqual(handler.expiry_key, 'ExpiryDate')
          self.assertEqual(len(handler.states), 2)

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
          }
        }
        template = json.dumps(dummy_template)
        return handler.cfn_client.create_stack(
          StackName="test_stack",
          TemplateBody=template
        )

      @mock_cloudformation
      def test_describe_stacks(self):
        self.build_stack()
        stacks = handler.describe_stacks()
        
        self.assertIsNotNone(stacks)
        self.assertEqual(len(stacks['Stacks']), 1)

      @mock_ec2
      def add_servers(self, ami_id="ami-0b71c21d"):
        conn = boto.connect_ec2('the_key', 'the_secret')
        return conn.run_instances(ami_id).instances[0]

      @mock_ec2
      def test_describe_tags(self):
        # test that if none is passed, we receive none
        instance_id = ""
        tags = handler.describe_tags(instance_id)
        self.assertIsNone(tags)

        # Test that with a valid instance id, we get the tags we expect
        instance = self.add_servers()
        instance.add_tag(handler.expiry_key, "05-04-2017")
        response = handler.describe_tags(instance.id)
        self.assertEquals(response['ResponseMetadata']['HTTPStatusCode'], 200)
        self.assertEquals(len(response['Tags']), 1)
        self.assertEquals(response['Tags'][0]['Key'], handler.expiry_key)
        self.assertEquals(response['Tags'][0]['Value'], "05-04-2017")

      @mock_ec2
      def test_describe_instances(self):
        instance_id = ""
        response = handler.describe_instances(instance_id)
        self.assertIsNone(response)

        instance = self.add_servers()
        response = handler.describe_instances(instance.id)
        obj = response['Reservations'][0]['Instances'][0]
        self.assertIsNotNone(response)
        self.assertIsNotNone(obj)
        self.assertEquals(obj['State']['Name'], 'running')

      @mock_ec2
      def test_update_tags(self):
        instance_id = ""
        response = handler.update_tags(instance_id, [])
        self.assertIsNone(response)
        tags = [{'Key':'blah', 'Value':'blah'}]
        response = handler.update_tags(instance_id, tags)
        self.assertIsNone(response)

        instance = self.add_servers()
        instance.add_tag(handler.expiry_key, "05-04-2017")
        response = handler.describe_tags(instance.id)
        self.assertEquals(response['Tags'][0]['Value'], "05-04-2017")
        handler.update_tags(instance.id, [
          {
            'Key': handler.expiry_key,
            'Value': "08-04-2017"
          }
        ])
        response = handler.describe_tags(instance.id)
        self.assertEquals(response['Tags'][0]['Value'], "08-04-2017")

      @mock_cloudformation
      def test_get_instance_id(self):
        stack = {}
        id = handler.get_instance_id(stack)
        self.assertIsNone(id)

        instance = self.add_servers()
        self.build_stack(instance.id)
        response = handler.describe_stacks()
        print(response)
        stack = response['Stacks'][0]
        id = handler.get_instance_id(stack)
        self.assertEquals(id, instance.id)

      @mock_ec2
      def test_stop_instance(self):
        instance_id = ""
        response = handler.stop_instance(instance_id)
        self.assertIsNone(response)

        instance = self.add_servers()
        handler.stop_instance(instance.id)
        response = handler.describe_instances(instance.id)
        self.assertEquals(response['Reservations'][0]['Instances'][0]['State']['Name'], 'stopped')

      @mock_ec2
      @mock_cloudformation
      def test_stop_instance_if_expired(self):
        # tests that an instance is stopped if the expiry date is before today and the instance is running
        today = datetime.strptime(datetime.today().strftime("%d-%m-%Y"), "%d-%m-%Y")
        yesterday = today - timedelta(days=1)
        instance = self.add_servers()
        instance.add_tag(handler.expiry_key, str(yesterday.date().strftime("%d-%m-%Y")))
        response = handler.describe_tags(instance.id)
        self.assertEquals(response['Tags'][0]['Value'], str(yesterday.date().strftime("%d-%m-%Y")))
        self.assertTrue(today > yesterday)
        response = handler.describe_instances(instance.id)
        obj = response['Reservations'][0]['Instances'][0]
        self.assertEquals(obj['State']['Name'], 'running')

        # The instance is running and expired yesterday
        self.build_stack(instance.id)
        handler.run()

        # instance should have new expiry date and be stopped
        response = handler.describe_instances(instance.id)
        obj = response['Reservations'][0]['Instances'][0]
        self.assertEquals(obj['State']['Name'], 'stopped')
        new_expiry_date = yesterday + timedelta(days=handler.days_to_stop)

        response = handler.describe_tags(instance.id)
        self.assertEquals(response['Tags'][0]['Value'], str(new_expiry_date.date().strftime("%d-%m-%Y")))

      @mock_ec2
      @mock_cloudformation
      def test_terminate_stack_if_stopped(self):
        # tests that a cloudformation stack is terminated if the instance is stopped and expired
        today = datetime.strptime(datetime.today().strftime("%d-%m-%Y"), "%d-%m-%Y")
        yesterday = today - timedelta(days=1)
        instance = self.add_servers()
        instance.add_tag(handler.expiry_key, str(yesterday.date().strftime("%d-%m-%Y")))
        self.build_stack(instance.id)
        
        # lets stop the instance, as per the logic
        handler.stop_instance(instance.id)

        # run the handler, the stack should be terminated. Describing would return an ClientError
        # as it no longer exists
        handler.run()
        with assert_raises(ClientError):
          response = handler.cfn_client.describe_stacks(
            StackName='test_stack'
          )
    
      @mock_cloudformation
      @mock_ec2
      def test_run_returns_0(self):
        today = datetime.strptime(datetime.today().strftime("%d-%m-%Y"), "%d-%m-%Y")
        yesterday = today - timedelta(days=1)
        instance = self.add_servers()
        instance.add_tag(handler.expiry_key, str(yesterday.date().strftime("%d-%m-%Y")))
        self.build_stack(instance.id)
        code = handler.run()

        self.assertEquals(code, 0)

if __name__ == '__main__':
  unittest.main()
  