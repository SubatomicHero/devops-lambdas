from __future__ import print_function
import json
import os
import boto3
import json
import six

os.environ['sqs_read_url'] = 'https://sqs.us-east-1.amazonaws.com/179276412545/online-trial-control-test-OnlineTrialRequestSQS-F546SLFQSE7Q'
os.environ['sqs_publish_url'] ='https://sqs.us-east-1.amazonaws.com/179276412545/online-trial-control-test-OnlineTrialInstanceRequestSQS-1E7SKEZWS698'


class InstanceRequestHandler:
    def __init__(self, read_url= os.environ['sqs_read_url'], publish_url=os.environ['sqs_publish_url']):
        try:
            self.cloud_client = boto3.client('cloudformation')
            self.sqs_client = boto3.client('sqs')
            self.sqs_res = boto3.resource('sqs')
            self.ec2_client = boto3.client('ec2')
            self.read_url = read_url
            self.publish_url = publish_url
        except Exception as err:
            message = "{0}\n".format(err)
            print(message)
            raise err
        
    def receiveMessage(self):
        try :
            response = self.sqs_client.receive_message(
                QueueUrl=self.read_url
            )
            if "Messages" in response :
                messages = response['Messages']
                if (len(messages) > 0):
                    print('Recieved messages: {}'.format(messages[0]['Body']))
                    return messages
                else :
                    print ('No messages to read')
                    return 0
            else :
                print ('No messages to read')
                return 0
        except AttributeError :
            print('No queue exists to receive a message')
            return 0
        except Exception  as e:
            print(type(e))
            return None
        
    def sendMessage(self ,stackId, stackUrl, originalmessage):
        if stackId.strip() and stackUrl.strip() and  originalmessage:
            message = {}
            message['message'] = originalmessage
            message['stack_id'] = stackId
            message['stack_url'] = stackUrl
            try:
                response = self.sqs_client.send_message(
                    QueueUrl=self.publish_url ,
                    MessageBody=json.dumps(message),
                )
                return response
            except AttributeError :
                print('No queue exists to send a  message')
                return 0
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
            print(message)
            print (err.args)
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
        if instance is None:
            return None
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
                    print(message)
                    print (err.args)
                    return None
            elif tagKey=='Allocated' and tag['Value']=='true':
                return 0
        return 'Not found'
        
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
                        print(message)
                        print (err.args)
                        return None
        else:
            return None
            
    def run(self):
        try :
            stackList = self.describeStack()
            if stackList is None:
                raise TypeError
            trialStack = self.findStack(stackList)
            if trialStack is None:
                raise TypeError
            stackId = trialStack['StackId']
            trialStackOutputs = trialStack['Outputs']
            stackUrl = self.findOutputKeyValue(trialStackOutputs, 'Url')
            if  (stackId is None) or (stackUrl is None) :
                raise TypeError
            instanceId = self.findOutputKeyValue(trialStackOutputs, 'InstanceId')
            if instanceId is None :
                raise TypeError
            print("The StackId of the stack is: {}".format(stackId))
            print("The StackURL of the stack is: {}".format(instanceId))
            print("The InstanceId of the stack is: {}".format(stackUrl))
            instanceTags = self.allocateInstance(instanceId)
            if instanceTags is None:
                raise TypeError
            if instanceTags == 0:
                print('The instance is already allocated')
            elif instanceTags == 'Not found':
                print('The instance doesnt have any tag Allocated.' )
            else:
                print('The instance is allocated now')
            msg_id = []
            messages = self.receiveMessage()
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
                        print ('The Message {} is read.'.format(message['MessageId']))
                        try:
                            m = self.sqs_res.Message(self.read_url,message['ReceiptHandle'])
                        except Exception as err:
                            message = "{0}\n".format(err)
                            return None
                        messageBody = json.dumps(message['Body'])
                        
                        response = self.sendMessage(stackId,stackUrl,messageBody)
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