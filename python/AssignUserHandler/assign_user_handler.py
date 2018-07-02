import logging
from string import ascii_lowercase, digits
import time
from random import choice
import json
from os import getenv
import base64
import requests
import boto3

logger = logging.getLogger()
logger.setLevel(logging.getLogger())

from marketo import Marketo, MarketoAPIError
from botocore.exceptions import ClientError

class AssignUserHandler(object):
    """Assign User Handler"""
    def __init__(self, api_host, client_id, client_secret, queue_url=None):
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
            logger.info("Cannot authenticate with Marketo: {}".format(err))
        except Exception as oth:
            logger.info("Unknown error occured: {}".format(oth))
        self.success = 'SUCCESS'
        self.failed = 'FAILED'

    def is_valid_message(self, message):
        """Checks that the message object is valid to process"""
        return message and 'stack_url' in message and 'stack_id' in message and 'message' in message

    def create_password(self, length=10):
        """Generates a password for the instance based on the len param"""
        return ''.join(choice(ascii_lowercase + digits) for _ in range(length))

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
                username = getenv('username')
                password = getenv('password')
                user_password = self.create_password()
                logger.info("assign_user_to_stack(): {}".format(url))
                details = message['message']
                if isinstance(details, basestring):
                    details = json.loads(details)
                logger.info(details)

                data = self._get_payload_data(details, user_password)
                base64string = base64.encodestring("{}:{}".format(username, password))
                base64string = base64string.replace("\n", "")
                headers = {
                    "Content-Type":"application/json",
                    "Authorization": "Basic {}".format(base64string)
                }
                req = requests.post(url, data=json.dumps(data), headers=headers)
                logger.info("Response from request is {}".format(req.status_code))
                if req.status_code == 200 or req.status_code == 409:
                    return user_password
            except requests.HTTPError as err:
                logger.error("assign_user_to_stack() -> error: {}".format(err))
        return None

    def upsert_leads(self, data):
        """Calls the Marketo API to upsert the leads"""
        try:
            return self.marketo_client.upsert_leads(data, lookup_field='id')
        except requests.HTTPError as err:
            logger.error("upsert_leads(): {}".format(err))
        except MarketoAPIError as merr:
            logger.error("upsert_leads(): {}".format(merr))
        return {}

    def create_marketo_data(self, lead):
        """Parses the lead object and returns a dict that marketo expects"""
        logger.info("create_marketo_data() {}".format(lead))
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
            logger.error(str(kerr))
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
            logger.error(str(err))
            return None

    def update_marketo_lead(self, lead, password):
        """Takes the lead object and updates Marketo prompting an email"""
        if self.is_valid_message(lead):
            logger.info("update_marketo_lead() {}".format(lead))
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
                        logger.info("Sleeping for 5 seconds, then trying again")
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

    def add_item_to_table(self, item, tablename=getenv('assign_stack_table')):
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

    def run(self, records):
        """Runs the Assign User Handler"""
        try:
            m_ids = []
            # process each message
            for message in records:
                logger.info(message)
                if message['messageId'] not in m_ids:
                    logger.info("Adding {} to read list".format(message['messageId']))
                    m_ids.append(message['messageId'])
                    message_body = json.loads(message['body'])

                    # assign user to the stack by creating user on box
                    password = self.assign_user_to_stack(message_body)
                    if not password:
                        logger.info("Unable to add new user to stack")
                        return self.failed
                    logger.info("User assigned")

                    # update marketo lead
                    result = self.update_marketo_lead(message_body, password)
                    if not result['success']:
                        logger.info("Unable to upsert Marketo lead")
                        return self.failed
                    logger.info("Market lead updated")

                    # if we got here, we are safe to add item to assign user table
                    if not self.add_item_to_table(message_body):
                        logger.info("Unable to save item to table")
                        return self.failed
                    logger.info("Item added to table")
                else:
                    logger.info("Already received ({}), moving on".format(message['messageId']))

            logger.info("All messages processed OK")
            return self.success
        except Exception as err:
            logger.error("run(): {}".format(err))
            return self.failed

CLS = AssignUserHandler(
    getenv('api_host', "https://453-liz-762.mktorest.com"),
    getenv('client_id', "35a7e1a3-5e60-40b2-bd54-674680af2adc"),
    getenv('client_secret', "thesecret"),
    getenv('sqs_read_url', "queue_url")
)

def handler(event, _):
    """Main handler function"""
    if 'Records' in event:
        return CLS.run(event['Records'])
    return 'SUCCESS'
