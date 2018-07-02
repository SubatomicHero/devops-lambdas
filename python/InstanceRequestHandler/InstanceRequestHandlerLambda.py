import logging
from datetime import datetime, timedelta
from random import shuffle
import json
from os import environ, getenv
import boto3
import six

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class InstanceRequestHandler(object):
    """
    Handles requests for instances
    """
    def __init__(self, read_url=getenv('sqs_read_url'), publish_url=getenv('sqs_publish_url')):
        try:
            self.cloud_client = boto3.client('cloudformation')
            self.sqs_client = boto3.client('sqs')
            self.ec2_client = boto3.client('ec2')
            self.read_url = read_url
            self.publish_url = publish_url
        except Exception as err:
            logger.info("{}\n".format(err))
            raise err

    def send_message(self, send_url, stack_id, stack_url, originalmessage):
        """
        Sends a message to a queue
        """
        if stack_id.strip() and stack_url.strip() and originalmessage:
            message = {
                'message': originalmessage,
                'stack_id': stack_id,
                'stack_url': stack_url
            }
            return self.sqs_client.send_message(
                QueueUrl=send_url,
                MessageBody=json.dumps(message),
            )
        raise ValueError('Valid stack ID, stack url and message are needed')

    def describe_stack(self, token=None):
        """
        Describes and returns all the current cfn stacks
        That we want
        """
        if token:
            response = self.cloud_client.describe_stacks(
                NextToken=token
            )
        else:
            response = self.cloud_client.describe_stacks()
        if 'Stacks' in response:
            stacks = []
            for stack in response['Stacks']:
                correct_stage = False
                correct_type = False
                if 'Outputs' in stack:
                    for output in stack['Outputs']:
                        key = output['OutputKey']
                        value = output['OutputValue']
                        if key == 'Type' and value == 'Trial':
                            correct_type = True
                        if key == 'Stage' and value == environ['stage']:
                            correct_stage = True
                    if correct_type and correct_stage:
                        stacks.append(stack)
            if 'NextToken' in response:
                stacks = stacks + self.describe_stack(response['NextToken'])
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
                    logger.info("This stack doesnt have any outputs, skipping")
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
                        logger.info("Instance {} is not running. Skipping".format(instance_id))
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
            logger.info('Every Stack must have an instance id')
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
        logger.info('Every stack should have a valid instance id')
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
                    logger.info('The key should be a str')
                    return None
        else:
            logger.info('The Stack should have a valid output')
            return None

    def run(self, records):
        """
        Run method
        """
        try:
            msg_id = []
            for message in records:
                logger.info("Received message: {}".format(message['body']))
                if message['messageId'] in msg_id:
                    logger.info("Message {} already read".format(message['messageId']))
                else:
                    # we havent processed this message yet
                    msg_id.append(message['messageId'])
                    logger.info('The Message {} is read.'.format(message['messageId']))

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
                    logger.info("The StackId of the stack is: {}".format(stack_id))
                    logger.info("The StackURL of the stack is: {}".format(stack_url))
                    logger.info("The InstanceId of the stack is: {}".format(instance_id))
                    instance_tags = self.allocate_instance(instance_id)
                    if instance_tags:
                        logger.info('The instance is allocated')

                    response = self.send_message(self.publish_url, stack_id, stack_url, message['body'])
                    if response is None:
                        raise ValueError('No valid queue exists to send a message')
                    logger.info("The Message {} is sent.".format(response['messageId']))
            logger.info("All messages read and processed")
            return 200
        except Exception as err:
            logger.error(str(err))
            return 'FAILURE'

IRH = InstanceRequestHandler()

def lambda_handler(event, context):
    """
    Entry function for the Lambda
    """
    try:
        if 'Records' in event:
            res = IRH.run(event['Records'])
            if res == 'FAILURE':
                logger.error('The run function has failed')
                raise ValueError
            logger.info("All OK")
            return res
        logger.info("No messages to process")
        return 200
    except Exception as err:
        logger.error(str(err))
        return 'FAILURE'        
