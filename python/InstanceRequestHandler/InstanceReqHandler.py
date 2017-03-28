from __future__ import print_function
import json
import os
import boto3
import json
import six

sqs_client = boto3.client('sqs')
ec2_client = boto3.client('ec2')

def lambda_handler(event, context):
    message = receiveMessage()
    trialStack = listStack()
    stackId = trialStack['StackId']
    trialStackOutputs = trialStack['Outputs']
    if trialStackOutputs:
        stackUrl = findOutputKeyValue(trialStackOutputs, 'Url')
        instanceId = findOutputKeyValue(trialStackOutputs, 'InstanceId')
    else:
        return 'FAILURE'
    if instanceId != None:
        instanceTags = allocateInstance(instanceId)
        if instanceTags == None:
            return 'FAILURE'
    else:
        return 'FAILURE'
    if stackId == None and stackUrl == None and message == None:
        return 'FAILURE'
    response = sendMessage(stackId,stackUrl,message)
    if response == None :
        return 'FAILURE'
    return 'SUCCESS'
    

def receiveMessage():
    try :
        message = sqs_client.receive_message(
            QueueUrl=os.environ['sqs_read_url'],
            AttributeNames=['All'],
             MessageAttributeNames=['All'],
        )
        return message
    except Exception as err:
        return None
    
def sendMessage(stackId, stackUrl, originalmessage):
    if stackId.strip() and stackUrl.strip() and  originalmessage:
        message = {}
        message['message'] = originalmessage
        message['stack_id'] = stackId
        message['stack_url'] = stackUrl
        try:
            response = sqs_client.send_message(
                QueueUrl=os.environ['sqs_publish_url'],
                MessageBody=json.dumps(message),
            )
            return response
        except Exception as err:
            return None
      
def listStack():
    try:
        cloud_client = boto3.client('cloudformation')
        trial = False
        test = False
        try:
            response = cloud_client.describe_stacks()
            stackList = response['Stacks']
            resultList = []
            for stack in stackList:
                if stack['StackStatus']=="CREATE_COMPLETE" or stack['StackStatus']=="UPDATE_COMPLETE":
                    for output in stack['Outputs']:
                        if output['OutputKey']=="Type" and output['OutputValue']=="Trial" :
                            trial = True
                        if output['OutputKey']=="Stage" and output['OutputValue']=="test" :
                            test = True
                    if trial and test :
                        resultList.append(stack)
            if len(resultList) != 0:
                return resultList[0]
        except Exception as err:
            return None
    except Exception as err:
        return None
    
def allocateInstance(instanceId):
    instance = findInstance(instanceId)
    if instance != None:
        for tag in instance['Tags']:
            tagKey = tag['Key']
            if tagKey=='Allocated' and tag['Value']=='false':
                try :
                    response = ec2_client.create_tags(
                        Resources=[
                            instanceId,
                        ],
                        Tags=[
                            {
                                'Key': 'Allocated',
                                'Value': 'true'
                            },
                        ]
                    )
                    instance = findInstance(instanceId)
                    if instance != None:
                        return instance['Tags']
                except Exception as err:
                    return None
            else:
                return instance['Tags']
    return None
    

def findInstance(instanceId):
    if instanceId and isinstance(instanceId, six.string_types) and  instanceId.strip():
        try:
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
            return instance
        except Exception as err:
            return None
    return None
    
def findOutputKeyValue(trialStackOutputs, key):
    if trialStackOutputs and key and isinstance(key, str) and  key.strip():
        for output in trialStackOutputs:
            outputKey = output['OutputKey']
            if outputKey and isinstance(outputKey, str) and  outputKey.strip():
                try:
                    if outputKey == key:
                        return output['OutputValue']
                except Exception as err:
                    return None
    return None
             