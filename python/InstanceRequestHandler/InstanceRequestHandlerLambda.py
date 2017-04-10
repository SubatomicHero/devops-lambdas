from __future__ import print_function
import json
import os
import boto3
import json
import six

class InstanceRequestHandler:
    def __init__(self):
        try:
            self.cloud_client = boto3.client('cloudformation')
            self.sqs_client = boto3.client('sqs')
            self.sqs_res = boto3.resource('sqs')
            self.ec2_client = boto3.client('ec2')
        except Exception as err:
            message = "{0}\n".format(err)
            print(message)
            raise err
        
    def receiveMessage(self ):
        try :
            response = self.sqs_client.receive_message(
                QueueUrl=os.environ['sqs_read_url'],
            )
            print (response)
            if "Messages" in response :
                messages = response['Messages']
                if (len(messages) > 0):
                    print('Recieved messages: {}'.format(messages))
                    return messages
                else :
                    print ('No messages to read')
                    return 0
            else :
                print ('No messages to read')
                return 0
        except Exception as err:
            print ('error')
            message = "{0}\n".format(err)
            print(message)
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
                message = "{0}\n".format(err)
                print(message)
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
            
    def run(self):
        try :
            stackList = IRH.describeStack()
            if stackList is None:
                raise TypeError
            trialStack = IRH.findStack(stackList)
            if trialStack is None:
                raise TypeError
            stackId = trialStack['StackId']
            trialStackOutputs = trialStack['Outputs']
            stackUrl = IRH.findOutputKeyValue(trialStackOutputs, 'Url')
            instanceId = IRH.findOutputKeyValue(trialStackOutputs, 'InstanceId')
            if instanceId is None:
                raise TypeError
            instanceTags = IRH.allocateInstance(instanceId)
            if  (stackId is None) or (stackUrl is None) :
                print (instanceTags)
                raise TypeError
            messages = IRH.receiveMessage()
            if(messages == 0):
                return 200
            elif messages is None :
                raise TypeError
            else:
                unread = False
                for i in range(len(messages)):
                    message = messages[i]
                    if message['MessageId'] in msg_id:
                        print ('Message already read.')
                        if(i == messages[len(messages)-1] and not(unread)):
                            print ('All Messages in the queue have been already read.')
                            return 'SUCCESS'
                    else:
                        msg_id.append(message['MessageId'])
                        unread = True
                        try:
                            m = self.sqs_res.Message('sqs_read_url',message['ReceiptHandle'])
                        except Exception as err:
                            message = "{0}\n".format(err)
                            print(message)
                            return None
                        messageBody = json.dumps(m['body'])
                        
                        response = IRH.sendMessage(stackId,stackUrl,messagebody)
                        if response  is None :
                            raise TypeError
                        
                           
                        m.delete()
            
            
    
        except Exception as err:
            message = "{0}\n".format(err)
            print(message)
            print (err.args)
            return ('FAILURE due to '+ message)
        else:
            print("All OK")
            return 200

IRH = InstanceRequestHandler()

def lambda_handler(event, context):
    try :
        res = IRH.run()
        if res is None :
            raiseTypeError

    except Exception as err:
        message = "{0}\n".format(err)
        print(message)
        print (err.args)
        return ('FAILURE due to '+ message)
    else:
        print("All OK")
        return 200