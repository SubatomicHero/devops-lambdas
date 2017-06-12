from __future__ import print_function
import string
import time
import random
import json
import os
import base64
import requests
import boto3

from marketo import Marketo, MarketoAPIError
from botocore.exceptions import ClientError

class AssignUserHandler(object):
    """Assign User Handler"""
    def __init__(self, api_host, client_id, client_secret, queue_url=None):
        self.sqs_client = boto3.client('sqs')
        self.dynamo_client = boto3.client('dynamodb')
        self.cfn_client = boto3.client('cloudformation')
        self.ec2_client = boto3.client('ec2')
        self.queue_url = queue_url
        try:
            self.marketo_client = Marketo(
                host=api_host,
                client_id=client_id,
                client_secret=client_secret
            )
        except requests.ConnectionError as err:
            print("Cannot authenticate with Marketo: {}".format(err))
        except Exception as oth:
            print("Unknown error occured: {}".format(oth))
        self.success = 'SUCCESS'
        self.failed = 'FAILED'

    def is_valid_message(self, message):
        """Checks that the message object is valid to process"""
        return message and 'stack_url' in message and 'stack_id' in message and 'message' in message

    def create_password(self, length=10):
        """Generates a password for the instance based on the len param"""
        return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))

    def get_message_from_queue(self, queue_url):
        """Gets a message from the queue and returns it"""
        if queue_url:
            try:
                response = self.sqs_client.receive_message(
                    QueueUrl=queue_url,
                    VisibilityTimeout=30
                )
                if 'Messages' in response and response['Messages']:
                    print("Returning {} message".format(len(response['Messages'])))
                    return response['Messages']
                print("get_message_from_queue(): Returning None")
                return None
            except TypeError as err:
                print("get_message_from_queue(): {}".format(err))
        return None

    def _get_payload_data(self, details, password):
        return {
            "userName": details['result'][0]['email'],
            "firstName": details['result'][0]['firstName'],
            "lastName": details['result'][0]['lastName'],
            "email": details['result'][0]['email'],
            "password": password,
            "groups": ["GROUP_ALFRESCO_ADMINISTRATORS"]
        }

    def assign_user_to_stack(self, message):
        """Assigns a user to the stack based on the marketo details in the message"""
        if self.is_valid_message(message):
          # make a request to the stack url to add a user from the message to the stack
            try:
                url = "{}/alfresco/service/api/people".format(message['stack_url'])
                username = os.getenv('username')
                password = os.getenv('password')
                user_password = self.create_password()
                print("assign_user_to_stack(): {}".format(url))
                details = message['message']
                if isinstance(details, basestring):
                    details = json.loads(details)
                print(details)

                data = self._get_payload_data(details, user_password)
                base64string = base64.encodestring("{}:{}".format(username, password))
                base64string = base64string.replace("\n", "")
                headers = {
                    "Content-Type":"application/json",
                    "Authorization": "Basic {}".format(base64string)
                }
                req = requests.post(url, data=json.dumps(data), headers=headers)
                print("Response from request is {}".format(req.status_code))
                if req.status_code == 200 or req.status_code == 409:
                    return user_password
            except requests.HTTPError as err:
                print("assign_user_to_stack() -> error: {}".format(err))
        return None

    def upsert_leads(self, data):
        """Calls the Marketo API to upsert the leads"""
        try:
            return self.marketo_client.upsert_leads(data, lookup_field='id')
        except requests.HTTPError as err:
            print("upsert_leads(): {}".format(err))
        except MarketoAPIError as merr:
            print("upsert_leads(): {}".format(merr))
        return {}

    def create_marketo_data(self, lead):
        """Parses the lead object and returns a dict that marketo expects"""
        print("create_marketo_data() {}".format(lead))
        try:
            data = lead['message']
            if isinstance(lead['message'], basestring):
                data = json.loads(lead['message'])
            return {
                "lastName": data['result'][0]['lastName'],
                "firstName": data['result'][0]['firstName'],
                "email": data['result'][0]['email'],
                "id": data['result'][0]['id'],
                "onlineTrialHostname": lead['stack_url'],
                "onlineTrialUsername": data['result'][0]['email'],
                "onlineTrialStatus": 'running'
            }
        except KeyError as kerr:
            print("{}\n".format(kerr))
        else:
            return {}

    def get_expiry_from_stack(self, stack_id):
        """Get the expiry date from the current stack id"""
        try:
            instance_id = ""
            response = self.cfn_client.describe_stacks(
                StackName=stack_id
            )
            stack = response['Stacks'][0]
            for output in stack['Outputs']:
                if output['OutputKey'] == 'InstanceId':
                    instance_id = output['OutputValue']
                    break

            tags = self.ec2_client.describe_tags(
                Filters=[
                    {
                        'Name': 'resource-id',
                        'Values': [instance_id]
                    }
                ]
            )
            for tag in tags['Tags']:
                if tag['Key'] == 'ExpiryDate':
                    return tag['Value']

        except ClientError as err:
            print("{}\n".format(err))
        else:
            return None

    def update_marketo_lead(self, lead, password):
        """Takes the lead object and updates Marketo prompting an email"""
        if self.is_valid_message(lead):
            print("update_marketo_lead() {}".format(lead))
            data = self.create_marketo_data(lead)
            if data is not None:
                data['onlineTrialPassword'] = password
                data['onlineTrialExpiry'] = self.get_expiry_from_stack(lead['stack_id'])
                if self.marketo_client:
                    self.marketo_client._authenticate()
                    attempts = 1
                    limit = 5
                    response = self.upsert_leads(data)

                    while not response and attempts != limit:
                        print("Sleeping for 5 seconds, then trying again")
                        attempts += 1
                        time.sleep(5)
                        response = self.upsert_leads(data)
                    return {
                        "success": response['success'] if 'success' in response else False,
                        "attempts": attempts
                    }
        return {
            "success": False,
            "attempts": 0
        }

    def add_item_to_table(self, item, tablename=os.getenv('assign_stack_table')):
        """Adds an item to the designated dynamo table"""
        if self.is_valid_message(item):
            assign_time = lambda: int(round(time.time() * 1000))
            message = item['message']
            if isinstance(item['message'], basestring):
                message = json.loads(item['message'])
            response = self.dynamo_client.update_item(
                TableName=tablename,
                Key={
                    'LeadId': {
                        "N": str(message['result'][0]['id'])
                    },
                    'Date': {
                        "S": time.strftime("%d/%m/%Y")
                    }
                },
                UpdateExpression="set #A=:a, #AT=:t, #UD=:u",
                ExpressionAttributeNames={
                    '#A':'Assigned',
                    '#AT':'AssignTime',
                    '#UD':'UserDetails'
                },
                ExpressionAttributeValues={
                    ':a': {"S": str(True)},
                    ':t': {"S": str(assign_time())},
                    ':u': {"S": str(item)}
                }
            )
            return response and response['ResponseMetadata']['HTTPStatusCode'] == 200
        return False

    def run(self):
        """Runs the Assign User Handler"""
        try:
            # First, get the messages if any are there
            messages = self.get_message_from_queue(self.queue_url)
            m_ids = []
            if messages is None:
                print("No messages on the queue, exiting...")
                return self.success

            # process each message (should only be one but just in case)
            for message in messages:
                print(message)
                if message['MessageId'] not in m_ids:
                    print("Adding {} to read list".format(message['MessageId']))
                    m_ids.append(message['MessageId'])
                    message_body = json.loads(message['Body'])

                    # assign user to the stack by creating user on box
                    password = self.assign_user_to_stack(message_body)
                    if not password:
                        print("Unable to add new user to stack")
                        return self.failed
                    print("User assigned")

                    # update marketo lead
                    result = self.update_marketo_lead(message_body, password)
                    if not result['success']:
                        print("Unable to upsert Marketo lead")
                        return self.failed
                    print("Market lead updated")

                    # if we got here, we are safe to add item to assign user table
                    if not self.add_item_to_table(message_body):
                        print("Unable to save item to table")
                        return self.failed
                    print("Item added to table")

                    # All processed OK, delete message
                    self.sqs_client.delete_message(
                        QueueUrl=os.getenv('sqs_read_url'),
                        ReceiptHandle=message['ReceiptHandle']
                    )
                    print("Message deleted")
                else:
                    print("Already received ({}), moving on".format(message['MessageId']))

            print("All messages processed OK")
            return self.success
        except Exception as err:
            print("run(): {}".format(err))
        return self.failed

CLS = AssignUserHandler(
    os.getenv('api_host', "https://453-liz-762.mktorest.com"),
    os.getenv('client_id', "35a7e1a3-5e60-40b2-bd54-674680af2adc"),
    os.getenv('client_secret', "thesecret"),
    os.getenv('sqs_read_url', "queue_url")
)

def handler(event, context):
    """Main handler function"""
    return CLS.run()
