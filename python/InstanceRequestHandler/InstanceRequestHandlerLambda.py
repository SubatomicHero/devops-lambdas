from __future__ import print_function
import json
import os
import boto3
import json
import six

class InstanceRequestHandler:
    def __init__(self, read_url = os.environ['sqs_read_url'], publish_url = os.environ['sqs_publish_url']):
        try:
            self.cloud_client = boto3.client('cloudformation')
            self.sqs_client = boto3.client('sqs')
            self.sqs_res = boto3.resource('sqs')
            self.ec2_client = boto3.client('ec2')
            self.read_url = read_url
            self.publish_url = publish_url
        except Exception as err:
            print("{}\n".format(err))
            raise err
        
    def receiveMessage(self, read_url):
        try:
            response = self.sqs_client.receive_message(
                QueueUrl = read_url
            )
            return response
        except Exception as err:
            print("{}\n".format(err))
        else:
            print('No messages to read')
            return None
        
    def sendMessage(self, send_url, stackId, stackUrl, originalmessage):
        try:
            if stackId.strip() and stackUrl.strip() and originalmessage:
                message = {}
                message['message'] = originalmessage
                message['stack_id'] = stackId
                message['stack_url'] = stackUrl
                response = self.sqs_client.send_message(
                    QueueUrl = send_url ,
                    MessageBody = json.dumps(message),
                )
                return response
            else:
                raise ValueError('Valid stack ID, stack url and message are needed')
        except Exception as err:
            print("{}\n".format(err))
        else:
            print('No queue to send messages')
            return None
        
    def describeStack(self):
        try:
            response = self.cloud_client.describe_stacks()
            stackList = response['Stacks']
            if stackList != None:
                return stackList
        except Exception as err:
            print("{}\n".format(err))
        else:
            return None

    def findStack(self, stackList):
        trial = False
        test = False
        for stack in stackList:
            if stack['StackStatus'] == "CREATE_COMPLETE":
                for output in stack['Outputs']:
                    if output['OutputKey'] == "Type" and output['OutputValue'] == "Trial":
                        trial = True
                    if output['OutputKey'] == "Stage" and output['OutputValue'] == os.environ['stage']:
                        test = True
                if trial and test:
                    return stack
        return None
        
    def allocateInstance(self, instanceId):
        instance = self.findInstance(instanceId)
        try:
            if instance is None:
                raise ValueError('Every Stack must have an instance id')
            for tag in instance['Tags']:
                tagKey = tag['Key']
                if tagKey == 'Allocated':
                    if tag['Value'] == 'false':
                        response = self.ec2_client.create_tags(
                            Resources = [
                                instanceId,
                            ],
                            Tags = [
                                {
                                    'Key': 'Allocated',
                                    'Value': 'true'
                                },
                            ]
                        )
                    return True
        except Exception as err:
            print("{}\n".format(err))
            return False
        
    def findInstance(self, instanceId):
        try:
            if instanceId and isinstance(instanceId, six.string_types) and instanceId.strip():
                instance = self.ec2_client.describe_tags(
                    Filters = [
                        {
                            'Name': 'resource-id',
                            'Values': [
                                instanceId,
                            ],
                        },
                    ],
                )
                return instance
            else: 
                raise ValueError('Every stack should have a valid instance id')
        except Exception as err:
            print("{}\n".format(err))
        else:
            return None
        
    def findOutputKeyValue(self, trialStackOutputs, key):
        try:
            if trialStackOutputs and key and key.strip():
                for output in trialStackOutputs:
                    outputKey = output['OutputKey']
                    if outputKey and isinstance(outputKey, str) and outputKey.strip():
                        if outputKey == key:
                            return output['OutputValue']
                    else:
                        raise ValueError('The key should be a str')
            else:
                raise ValueError('The Stack should have a valid output')
        except Exception as err:
            print("{}\n".format(err))
            return None
            
    def run(self):
        try:
            stackList = self.describeStack()
            if stackList is None:
                raise ValueError('No valid stack could be found')
            trialStack = self.findStack(stackList)
            if trialStack is None:
                raise ValueError('No Stack could be found')
            stackId = trialStack['StackId']
            trialStackOutputs = trialStack['Outputs']
            stackUrl = self.findOutputKeyValue(trialStackOutputs, 'Url')
            if (stackId is None) or (stackUrl is None) :
                raise ValueError('No valid stack id could be found')
            instanceId = self.findOutputKeyValue(trialStackOutputs, 'InstanceId')
            if instanceId is None:
                raise ValueError('No instance id could be found')
            print("The StackId of the stack is: {}".format(stackId))
            print("The StackURL of the stack is: {}".format(instanceId))
            print("The InstanceId of the stack is: {}".format(stackUrl))
            instanceTags = self.allocateInstance(instanceId)
            if instanceTags:
                print('The instance is allocated')
            response = self.receiveMessage(self.read_url)
            if response is None:
                raise ValueError('No valid queue exists to receive a message')
            else:
                if "Messages" in response:
                    messages = response['Messages']
                    unread = False
                    msg_id = []
                    for i in range(len(messages)):
                        message = messages[i]
                        print('Recieved message: {}'.format(message['Body']))
                        if message['MessageId'] in msg_id:
                            print ('Message already read.')
                            if(i == messages[len(messages)-1] and not(unread)):
                                print ('All Messages in the queue have been already read.')
                                return 'SUCCESS'
                        else:
                            msg_id.append(message['MessageId'])
                            unread = True
                            print ('The Message {} is read.'.format(message['MessageId']))
                            m = self.sqs_res.Message(self.read_url, message['ReceiptHandle'])
                            messageBody = json.dumps(message['Body'])
                            response = self.sendMessage(self.publish_url, stackId, stackUrl, messageBody)
                            if response  is None:
                                raise ValueError('No valid queue exists to send a message')
                            print ('The Message {} is sent.'.format(response['MessageId']))
                            try:
                                m.delete()
                            except Exception as err:
                                raise err
                            print ('The Message {} is sent.'.format(m))
                else:
                    print('No message in the queue')
        except Exception as err:
            message = "{0}\n".format(err)
            print("{}\n".format(err))
            return message
        else:
            return 200

IRH = InstanceRequestHandler()

def lambda_handler(event, context):
    try:
        res = IRH.run()
        if res != 200:
            print (res)
            raise ValueError
    except Exception as err:
        print("{}\n".format(err))
        return ('FAILURE')
    else:
        print("All OK")
        return 200