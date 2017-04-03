from __future__ import print_function
import json
import os
import boto3
import json
import six


def lambda_handler(event, context):
    try :
        IRH = InstanceRequestHandler()
        message = IRH.receiveMessage()
        stackList = IRH.describeStack()
        if stackList:
            trialStack = IRH.findStack(stackList)
            if trialStack:
                stackId = trialStack['StackId']
                trialStackOutputs = trialStack['Outputs']
                stackUrl = IRH.findOutputKeyValue(trialStackOutputs, 'Url')
                instanceId = IRH.findOutputKeyValue(trialStackOutputs, 'InstanceId')
                if instanceId != None:
                    instanceTags = IRH.allocateInstance(instanceId)
                    if instanceTags == None:
                        return 'FAILURE'
                    else:
                        if stackId == None or stackUrl == None or message == None:
                            return 'FAILURE'
                        else:
                            response = IRH.sendMessage(stackId,stackUrl,message)
                            if response == None :
                                return 'FAILURE'
                else:
                    return 'FAILURE'
            else:
                return 'FAILURE'
        else:
            return 'FAILURE'

    except Exception as err:
        message = "{0}\n".format(err)
        print(message)
        raise err
    else:
        print("All OK")
        return 200

class InstanceRequestHandler:
    def __init__(self):
        try:
            self.cloud_client = boto3.client('cloudformation')
            self.sqs_client = boto3.client('sqs')
            self.ec2_client = boto3.client('ec2')
        except Exception as err:
            return None
        
    def receiveMessage(self ):
        try :
            message = self.sqs_client.receive_message(
                QueueUrl=os.environ['sqs_read_url'],
            )
            return message
        except Exception as err:
            return None
        
    def sendMessage(self ,stackId, stackUrl, originalmessage):
        if stackId.strip() and stackUrl.strip() and  originalmessage:
            message = {}
            message['message'] = originalmessage
            message['stack_id'] = stackId
            message['stack_url'] = stackUrl
            try:
                response = self.sqs_client.send_message(
                    QueueUrl=os.environ['sqs_publish_url'],
                    MessageBody=json.dumps(message),
                )
                return response
            except Exception as err:
                return None
        else:
            return None
        
    def describeStack(self ):
        try:
            response = self.cloud_client.describe_stacks()
            stackList = response['Stacks']
            if stackList != None:
                return stackList
        except Exception as err:
            return None

    def findStack(self ,stackList):
        trial = False
        test = False
        for stack in stackList:
            if stack['StackStatus']=="CREATE_COMPLETE" :
                for output in stack['Outputs']:
                    if output['OutputKey']=="Type" and output['OutputValue']=="Trial" :
                        trial = True
                    if output['OutputKey']=="Stage" and output['OutputValue']=="test" :
                        test = True
                if trial and test :
                    return stack
        return None
        
    def allocateInstance(self ,instanceId):
        instance = self.findInstance(instanceId)
        if instance != None:
            for tag in instance['Tags']:
                tagKey = tag['Key']
                if tagKey=='Allocated' and tag['Value']=='false':
                    try :
                        response = self.ec2_client.create_tags(
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
                        return response
                    except Exception as err:
                        return None
        

    def findInstance(self ,instanceId):
        if instanceId and isinstance(instanceId, six.string_types) and  instanceId.strip():
            try:
                instance = self.ec2_client.describe_tags(
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
        else:
            return None
        
    def findOutputKeyValue(self ,trialStackOutputs, key):
        if trialStackOutputs and key  and  key.strip():
            for output in trialStackOutputs:
                outputKey = output['OutputKey']
                if outputKey and isinstance(outputKey, str) and  outputKey.strip():
                    try:
                        if outputKey == key:
                            return output['OutputValue']
                    except Exception as err:
                        return None
        else:
            return None