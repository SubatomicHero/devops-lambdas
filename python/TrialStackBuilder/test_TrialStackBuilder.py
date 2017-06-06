from moto import mock_cloudformation, mock_ec2, mock_s3, mock_lambda
import unittest, boto, boto3, requests, sure, time, json, uuid, os
from botocore.exceptions import ClientError
from nose.tools import assert_raises
from TrialStackBuilderLambda import TrialStackBuilder

os.environ['stage'] = 'test'

# parameters
EVENT = {
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

DUMMY_TEMPLATE2 = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Stack 2",
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

TSB = TrialStackBuilder()

class TestTrialStackBuilder(unittest.TestCase):
    """
    TestTrialStackBuilder
    """
    def test_instance(self):
        """
        test_instance
        """
        print "test_instance()"
        self.assertIsNotNone(TSB.cloud_client)
        self.assertIsNotNone(TSB.ec2_client)
        self.assertIsNotNone(TSB.s3_client)

    @mock_cloudformation
    def build_stack(self, instance_id="i-0e0f25febd2bb4f43"):
        """
        build_stack
        """
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
        return TSB.cloud_client.create_stack(
            StackName="trial-test_stack",
            TemplateBody=template
        )

    @mock_ec2
    def add_servers(self, ami_id = "ami-0b71c21d"):
        """
        add_servers
        """
        conn = boto.connect_ec2('the_key', 'the_secret')
        return conn.run_instances(ami_id).instances[0]

    @mock_cloudformation
    def test_list_stack(self):
        """
        test_list_stack
        """
        print "test_listStack()"
        self.build_stack()
        stacks = TSB.list_stack()
        self.assertIsNotNone(stacks)
        self.assertEqual(len(stacks), 1)
        print "Test 'list stacks' : passed"

    @mock_s3
    @mock_ec2
    @mock_cloudformation
    def test_run_returns_200(self):
        """
        test_run_returns_200
        """
        template = json.dumps(DUMMY_TEMPLATE2)
        filename = 'online-trial-stack-develop.yaml'
        tplt = open('temp.yaml', 'w')
        tplt.write(template)
        tplt.close()
        s3_res = boto3.resource('s3')
        bucket = s3_res.create_bucket(Bucket='TrialBucket')
        s3_res.Bucket('TrialBucket').upload_file('temp.yaml', filename)
        if os.path.isfile('temp.yaml'):
            os.remove('temp.yaml')  # remove the file
        local_intance = TrialStackBuilder('TrialBucket', 'test')
        code = local_intance.run(EVENT)
        self.assertEquals(code, 200)
        print "Test 'Run function return 200' : passed"

    @mock_cloudformation
    def test_find_instance_id(self):
        """
        test_find_instance_id
        """
        self.build_stack()
        stacks = TSB.list_stack()
        instance_id_result = TSB.find_instance_id(stacks[0]['Outputs'])
        instance_id_expected = "i-0e0f25febd2bb4f43"
        assert instance_id_expected == instance_id_result
        print "Test 'Find Stack instanceId' : passed"

    @mock_cloudformation
    @mock_ec2
    def test_find_instance(self):
        """
        test_find_instance
        """
        instance = self.add_servers()
        self.build_stack(instance.id)
        instance_test = TSB.find_instance(instance.id)
        assert instance_test['ResponseMetadata']['HTTPStatusCode'] == 200
        assert instance_test['ResponseMetadata']["RetryAttempts"] == 0
        print "Test 'Find Instance' : passed"

    @mock_cloudformation
    @mock_ec2
    def test_find_unassigned_instance(self):
        """
        test_find_unassigned_instance
        """
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')
        self.build_stack(instance.id)
        instance_test = TSB.find_instance(instance.id)
        unassigned = TSB.find_unassigned_instance(instance_test['Tags'])
        assert unassigned
        print "Test 'Find Unassigned Instance' : passed"

    @mock_cloudformation
    @mock_ec2
    def test_count_unassigned_stack(self):
        """
        test_count_unassigned_stack
        """
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')
        self.build_stack(instance.id)
        stacks = TSB.list_stack()
        count = TSB.count_unassigned_stack(stacks)
        assert count == 1
        assert count is not None

        instance = self.add_servers()
        instance.add_tag('Allocated', 'true')
        self.build_stack(instance.id)
        stacks = TSB.list_stack()
        count = TSB.count_unassigned_stack(stacks)
        assert count == 0
        assert count is not None

        print "Test 'Count Unassigned Stack ' : passed"

    @mock_cloudformation
    @mock_s3
    def test_create_stack(self):
        """
        test_create_stack
        """
        template = json.dumps(DUMMY_TEMPLATE2)
        filename = 'online-trial-stack-develop.yaml'
        tplt = open('temp.yaml', 'w')
        tplt.write(template)
        tplt.close()
        s3_res = boto3.resource('s3')
        bucket = s3_res.create_bucket(Bucket='TrialBucket')
        s3_res.Bucket('TrialBucket').upload_file('temp.yaml', filename)
        if os.path.isfile('temp.yaml'):
            os.remove('temp.yaml')  # remove the file
        local_intance = TrialStackBuilder('TrialBucket', 'test')
        local_intance.template = template
        stack_id = local_intance.create_stack()
        assert stack_id != None
        assert 'arn:aws:cloudformation:us-east-1' in stack_id
        print "Test 'Create Stack' : passed"

    @mock_s3
    def test_get_template(self):
        """
        test_get_template
        """
        template = json.dumps(DUMMY_TEMPLATE2)
        filename = 'online-trial-stack-develop.yaml'
        tplt = open('temp.yaml', 'w')
        tplt.write(template)
        tplt.close()
        s3_res = boto3.resource('s3')
        bucket = s3_res.create_bucket(Bucket='TrialBucket')
        s3_res.Bucket('TrialBucket').upload_file('temp.yaml', filename)
        if os.path.isfile('temp.yaml'):
            os.remove('temp.yaml')  # remove the file
        local_intance = TrialStackBuilder('TrialBucket', 'test')
        test_template = local_intance.get_template()
        assert test_template == template
        print "Test 'Get Template' : passed"

if __name__ == '__main__':
    unittest.main()
  