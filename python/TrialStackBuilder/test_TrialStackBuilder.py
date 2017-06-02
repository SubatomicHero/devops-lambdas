from moto import mock_cloudformation, mock_ec2, mock_s3, mock_lambda
import unittest, boto, boto3, requests, sure, time, json, uuid, os
from botocore.exceptions import ClientError
from nose.tools import assert_raises
from TrialStackBuilderLambda import TrialStackBuilder

os.environ['stage'] = 'test'

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

dummy_template2 = {
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
    def test_instance(self):
        print("test_instance()")
        self.assertIsNotNone(TSB.cloud_client)
        self.assertIsNotNone(TSB.ec2_client)
        self.assertIsNotNone(TSB.s3_client)

    @mock_cloudformation
    def build_stack(self, instance_id="i-0e0f25febd2bb4f43"):
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
        conn = boto.connect_ec2('the_key', 'the_secret')
        return conn.run_instances(ami_id).instances[0]
    
    @mock_cloudformation
    def test_listStack(self):
        print("test_listStack()")
        self.build_stack()
        stacks = TSB.list_stack()
        self.assertIsNotNone(stacks)
        self.assertEqual(len(stacks), 1)
        print("Test 'list stacks' : passed")

    @mock_s3
    @mock_ec2
    @mock_cloudformation
    def test_run_returns_200(self):
        template = json.dumps(dummy_template2)
        filename = 'online-trial-stack-develop.yaml'
        file = open('temp.yaml','w') 
        file.write(template) 
        file.close() 
        s3_res= boto3.resource('s3', region_name='us-east-1')
        bucket = s3_res.create_bucket(Bucket='TrialBucket')
        s3_res.Bucket('TrialBucket').upload_file('temp.yaml', filename)
        if os.path.isfile('temp.yaml'):
            os.remove('temp.yaml')  # remove the file
        else:
            raise ValueError("file {} is not a file or dir.".format(path))
        local_intance = TrialStackBuilder('TrialBucket', 'test')
        code = local_intance.run(event)
        self.assertEquals(code, 200)
        print("Test 'Run function return 200' : passed")

    @mock_cloudformation
    def test_findInstanceId(self):
        self.build_stack()
        stacks = TSB.list_stack()
        instanceIdResult = TSB.find_instance_id(stacks[0]['Outputs'])
        instanceIdExpected = "i-0e0f25febd2bb4f43"
        assert instanceIdExpected == instanceIdResult
        print "Test 'Find Stack instanceId' : passed"
    
    @mock_cloudformation
    @mock_ec2
    def test_findInstance(self):
        instance = self.add_servers()
        self.build_stack(instance.id)
        instance_test = TSB.find_instance(instance.id)
        assert instance_test['ResponseMetadata']['HTTPStatusCode'] == 200
        assert instance_test['ResponseMetadata']["RetryAttempts"] == 0
        print("Test 'Find Instance' : passed")

    @mock_cloudformation
    @mock_ec2
    def test_findUnassignedInstance(self):
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')
        self.build_stack(instance.id)
        instance_test = TSB.find_instance(instance.id)
        unassigned = TSB.find_unassigned_instance(instance_test['Tags'])
        assert unassigned == True
        print("Test 'Find Unassigned Instance' : passed")

    @mock_cloudformation
    @mock_ec2
    def test_countUnassignedStack(self):
        instance = self.add_servers()
        instance.add_tag('Allocated', 'false')
        self.build_stack(instance.id)
        stacks = TSB.list_stack()
        count = TSB.count_unassigned_stack(stacks)
        assert count == 1
        print("Test 'Count Unassigned Stack ' : passed")

    @mock_cloudformation
    @mock_s3
    def test_createStack(self):
        template = json.dumps(dummy_template2)
        filename = 'online-trial-stack-develop.yaml'
        file = open('temp.yaml','w') 
        file.write(template) 
        file.close() 
        s3_res= boto3.resource('s3', region_name = 'us-east-1')
        bucket = s3_res.create_bucket(Bucket = 'TrialBucket')
        s3_res.Bucket('TrialBucket').upload_file('temp.yaml', filename)
        if os.path.isfile('temp.yaml'):
            os.remove('temp.yaml')  # remove the file
        else:
            raise ValueError("file {} is not a file or dir.".format(path))
        local_intance = TrialStackBuilder('TrialBucket', 'test')
        local_intance.template = template
        stackId = local_intance.create_stack()
        assert stackId != None
        assert ('arn:aws:cloudformation:us-east-1' in stackId ) == True
        print("Test 'Create Stack' : passed")

    @mock_s3
    def test_getTemplate(self):
        template = json.dumps(dummy_template2)
        filename = 'online-trial-stack-develop.yaml'
        file = open('temp.yaml','w') 
        file.write(template) 
        file.close() 
        s3_res= boto3.resource('s3', region_name = 'us-east-1')
        bucket = s3_res.create_bucket(Bucket = 'TrialBucket')
        s3_res.Bucket('TrialBucket').upload_file('temp.yaml', filename)
        if os.path.isfile('temp.yaml'):
            os.remove('temp.yaml')  # remove the file
        else:
            raise ValueError("file {} is not a file or dir.".format(path))
        local_intance = TrialStackBuilder('TrialBucket','test')
        testTemplate = local_intance.get_template()
        assert testTemplate == template
        print("Test 'Get Template' : passed")

if __name__ == '__main__':
    unittest.main()
  