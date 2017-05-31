from __future__ import print_function
from datetime import datetime, timedelta
from random import shuffle
import json
import os
import boto3
import six

class InstanceRequestHandler(object):
    """
    Handles requests for instances
    """
    def __init__(self, read_url=os.getenv('sqs_read_url'), publish_url=os.getenv('sqs_publish_url')):
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

    def receive_message(self, read_url):
        """
        Receives a message from the queue
        """
        return self.sqs_client.receive_message(QueueUrl=read_url)

    def send_message(self, send_url, stack_id, stack_url, originalmessage):
        """
        Sends a message to a queue
        """
        if stack_id.strip() and stack_url.strip() and originalmessage:
            message = {}
            message['message'] = originalmessage
            message['stack_id'] = stack_id
            message['stack_url'] = stack_url
            return self.sqs_client.send_message(
                QueueUrl=send_url,
                MessageBody=json.dumps(message),
            )
        raise ValueError('Valid stack ID, stack url and message are needed')

    def describe_stack(self):
        """
        Describes and returns all the current cfn stacks
        That we want
        """
        trial = False
        test = False
        response = self.cloud_client.describe_stacks()
        if 'Stacks' in response:
            stacks = []
            stage = os.environ['stage']
            for stack in response['Stacks']:
                if 'Outputs' not in stack:
                    continue
                for output in stack['Outputs']:
                    key = output['OutputKey']
                    value = output['OutputValue']
                    if key == "Type" and value == "Trial":
                        trial = True
                    if key == "Stage" and value == stage:
                        test = True
                if trial and test:
                    stacks.append(stack)
            return stacks
        return None

    def find_stack(self, stack_list):
        """
        Finds an unallocated stack and returns it
        """
        shuffle(stack_list)
        for stack in stack_list:
            if stack['StackStatus'] == "CREATE_COMPLETE":
                instance_id = None
                if 'Outputs' not in stack:
                    print("This stack doesnt have any outputs, skipping")
                    continue
                for output in stack['Outputs']:
                    key = output['OutputKey']
                    value = output['OutputValue']
                    if key == 'InstanceId':
                        instance_id = value
                        break
                if instance_id:
                    # first, make sure the instance is running. It may be stopped
                    response = self.ec2_client.describe_instance_status(
                        InstanceIds=[instance_id]
                    )
                    statuses = response['InstanceStatuses']
                    if not statuses:
                        print("Instance {} is not running. Skipping".format(instance_id))
                        continue
                    # All good, we can allocate this instance
                    instance = self.find_instance(instance_id)
                    if instance is None:
                        raise ValueError('Every Stack must have an instance id')
                    for tag in instance['Tags']:
                        tag_key = tag['Key']
                        if tag_key == 'Allocated':
                            if tag['Value'] == 'false':
                                return stack
                            break
        return None

    def allocate_instance(self, instance_id):
        """
        Updates the tags on an instance so its allocated
        """
        instance = self.find_instance(instance_id)
        if instance is None:
            print('Every Stack must have an instance id')
            return False
        for tag in instance['Tags']:
            tag_key = tag['Key']
            if tag_key == 'Allocated':
                if tag['Value'] == 'false':
                    date = datetime.today() + timedelta(days=14)
                    self.ec2_client.create_tags(
                        Resources=[instance_id],
                        Tags=[
                            {
                                'Key': 'Allocated',
                                'Value': 'true'
                            },
                            {
                                'Key': 'ExpiryDate',
                                'Value': date.date().strftime('%d-%m-%Y')
                            }
                        ]
                    )
                return True

    def find_instance(self, instance_id):
        """
        Finds an instance from the tags
        """
        if instance_id and isinstance(instance_id, six.string_types) and instance_id.strip():
            return self.ec2_client.describe_tags(
                Filters=[
                    {
                        'Name': 'resource-id',
                        'Values': [instance_id],
                    },
                ],
            )
        print('Every stack should have a valid instance id')
        return None

    def find_output_key_value(self, trial_stack_outputs, key):
        """
        Gets the value from a cfn stack output
        """
        if trial_stack_outputs and key and key.strip():
            for output in trial_stack_outputs:
                output_key = output['OutputKey']
                if output_key and isinstance(output_key, str) and output_key.strip():
                    if output_key == key:
                        return output['OutputValue']
                else:
                    print('The key should be a str')
                    return None
        else:
            print('The Stack should have a valid output')
            return None

    def run(self):
        """
        Run method
        """
        try:
            # get messages from queue
            response = self.receive_message(self.read_url)
            if "Messages" in response:
                # we have messages to process, 1 or more
                messages = response['Messages']
                msg_id = []
                for message in messages:
                    print("Received message: {}".format(message['Body']))
                    if message['MessageId'] in msg_id:
                        print("Message {} already read".format(message['MessageId']))
                    else:
                        # we havent processed this message yet
                        msg_id.append(message['MessageId'])
                        print ('The Message {} is read.'.format(message['MessageId']))
                        msg = self.sqs_res.Message(self.read_url, message['ReceiptHandle'])

                        # Allocate an instance
                        stack_list = self.describe_stack()
                        if stack_list is None:
                            raise ValueError('No valid stack could be found')
                        trial_stack = self.find_stack(stack_list)
                        if trial_stack is None:
                            raise ValueError('No Stack could be found')
                        stack_id = trial_stack['StackId']
                        trial_stack_outputs = trial_stack['Outputs']
                        stack_url = self.find_output_key_value(trial_stack_outputs, 'Url')
                        if (stack_id is None) or (stack_url is None):
                            raise ValueError('No valid stack id could be found')
                        instance_id = self.find_output_key_value(trial_stack_outputs, 'InstanceId')
                        if instance_id is None:
                            raise ValueError('No instance id could be found')
                        print("The StackId of the stack is: {}".format(stack_id))
                        print("The StackURL of the stack is: {}".format(stack_url))
                        print("The InstanceId of the stack is: {}".format(instance_id))
                        instance_tags = self.allocate_instance(instance_id)
                        if instance_tags:
                            print('The instance is allocated')

                        response = self.send_message(self.publish_url, stack_id, stack_url, message['Body'])
                        if response is None:
                            raise ValueError('No valid queue exists to send a message')
                        print("The Message {} is sent.".format(response['MessageId']))
                        try:
                            msg.delete()
                            print("The Message has been deleted")
                        except Exception as err:
                            raise err
                print("All messages read and processed")
            else:
                print("No messages to read")
        except Exception as err:
            print("{}\n".format(err))
            return 'FAILURE'
        else:
            return 200

IRH = InstanceRequestHandler()

def lambda_handler(event, context):
    """
    Entry function for the Lambda
    """
    try:
        res = IRH.run()
        if res == 'FAILURE':
            print ('The run function has failed')
            raise ValueError
        print("All OK")
        return 200
    except Exception as err:
        print("{}\n".format(err))
    else:
        return 'FAILURE'
