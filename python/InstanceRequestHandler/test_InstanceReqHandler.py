import boto
import boto3
import botocore.exceptions
from boto.exception import SQSError
from boto.sqs.message import RawMessage, Message

import requests
import sure  # noqa
import time
import json 
from moto import  mock_sqs, mock_ec2, mock_cloudformation, mock_lambda
from nose.tools import assert_raises
from InstanceRequestHandlerLambda import InstanceRequestHandler



IRH = InstanceRequestHandler()


@mock_lambda
def test_lambda_handler():
    message = test_receiveMessage()
    stackList = test_describeStack()
    trialStack = test_findStack(stackList)
    stackId = trialStack['StackId']
    stackUrl = test_findUrl(trialStack)
    instanceId = test_findinstanceId(trialStack)
    test_findInstance(instanceId)
    test_allocateInstance()
    test_sendMessage(stackId, stackUrl, message)

@mock_sqs
def test_receiveMessage():
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
def test_sendMessage(stackId, stackUrl,original_message):

    original_message['stack_id'] = stackId
    original_message['stack_url'] = stackUrl
    sqs = boto3.resource('sqs')
    queue = sqs.create_queue(QueueName='OnlineTrialRequestSQS')
    response = queue.send_message(MessageBody=json.dumps(original_message))
    assert response['ResponseMetadata']['HTTPStatusCode'] == 200
    assert response['ResponseMetadata']["RetryAttempts"] == 0
    assert response.get('Failed') == None
    # assert response.get('MD5OfMessageBody') == '7d8643aa0e8110fd8e26462e9e01600c'
    print("Test 'send message' : passed")

@mock_cloudformation
def test_describeStack():
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
                "Value": "i-011e00f871fdcac11"
            },
        }
    }


    dummy_template_json = json.dumps(dummy_template)



    cf = boto3.client('cloudformation')
    cf.create_stack(
        StackName="trial_stack",
        TemplateBody=dummy_template_json,
    )

    stackList = cf.describe_stacks(StackName="trial_stack")['Stacks']
   

    # stackList = IRH.describeStack()
    stack = stackList[0]
    response = cf.describe_stack_resources(StackName=stack['StackName'])
    resource = response['StackResources'][0]
    resource['LogicalResourceId'].should.equal('TrialEc2Instance')
    resource['ResourceStatus'].should.equal('CREATE_COMPLETE')
    resource['ResourceType'].should.equal('AWS::EC2::Instance')
    resource['StackId'].should.equal(stack['StackId'])

    stack['StackStatus'].should.equal('CREATE_COMPLETE')
    print("Test 'describe stacks' : passed")
    return stackList

def test_findStack(stackList):
    stackExpected = stackList[0]
    stackResult = IRH.findStack(stackList)
    assert stackExpected == stackResult
    print("Test 'Find stacks' : passed")
    return stackResult

def test_findUrl(trialStack):
    urlExpected = "https://requesttest.trial.alfresco.com/online-trial"
    urlResult = IRH.findOutputKeyValue(trialStack['Outputs'], 'Url')
    assert urlExpected == urlResult
    print("Test 'find stack Url' : passed")
    return urlResult

def test_findinstanceId(trialStack):
    instanceIdExpected = "i-011e00f871fdcac11"
    instanceIdResult = IRH.findOutputKeyValue(trialStack['Outputs'], 'InstanceId')
    assert instanceIdExpected == instanceIdResult
    print("Test 'Find Stack instanceId' : passed")
    return instanceIdResult

@mock_ec2
def test_findInstance(instanceId):
    ec2_client = boto3.client('ec2')
    instance = ec2_client.describe_tags(
        Filters=[
            {
                'Name': 'resource-id',
                'Values': [
                    instanceId,
                ],
            },
        ],
    )
    assert instance['ResponseMetadata']['HTTPStatusCode'] == 200
    assert instance['ResponseMetadata']["RetryAttempts"] == 0
    print("Test 'Find Instance' : passed")

@mock_ec2
def test_allocateInstance():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-d3adb33f')
    instance = reservation.instances[0]
    instance.add_tag("Allocated", "false")
    instanceId = instance.id 
    image_id = conn.create_image(instanceId, "test-ami", "this is a test ami")
    image = conn.get_image(image_id)

    tags = conn.get_all_tags(filters={'resource-id': instanceId})
    tag = tags[0]
    tags.should.have.length_of(1)
    tag.res_id.should.equal(instanceId)
    tag.res_type.should.equal('instance')
    tag.name.should.equal("Allocated")
    tag.value.should.equal("false")

    instance.add_tag("Allocated", "true")
    image_id = conn.create_image(instanceId, "test-ami", "this is a test ami")
    image = conn.get_image(image_id)

    tags = conn.get_all_tags(filters={'resource-id': instanceId})
    tag = tags[0]
    tags.should.have.length_of(1)
    tag.res_id.should.equal(instanceId)
    tag.res_type.should.equal('instance')
    tag.name.should.equal("Allocated")
    tag.value.should.equal("true")
    print("Test 'Allocate Stack ' : passed")

test_lambda_handler()