from __future__ import print_function
import string
import time
import random
import json
import os
import requests
import boto3

from marketo import Marketo, MarketoAPIError
from botocore.exceptions import ClientError

class AssignUserHandler:
  def __init__(self, api_host, client_id, client_secret, queue_url=None):
    self.sqs_client = boto3.client('sqs')
    self.dynamo_client = boto3.client('dynamodb')
    self.sqs_res = boto3.resource('sqs')
    self.cfn_client = boto3.client('cloudformation')
    self.ec2_client = boto3.client('ec2')
    self.queue_url = queue_url
    try:
      self.marketo_client = Marketo(host=api_host, client_id=client_id, client_secret=client_secret)
    except requests.ConnectionError as err:
      print("Cannot authenticate with Marketo: {}".format(err))
    except Exception as oth:
      print("Unknown error occured: {}".format(oth))
    self.SUCCESS = 'SUCCESS'
    self.FAILED = 'FAILED'

  def is_valid_message(self, message):
    """Checks that the message object is valid to process"""
    return message and 'stack_url' in message and 'stack_id' in message and 'message' in message

  def create_password(self, len=10):
    """Generates a password for the instance based on the len param"""
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(len))

  def get_message_from_queue(self, queue_url):
    """Gets a message from the queue and returns it"""
    if queue_url:
      try:
        response = self.sqs_client.receive_message(
          QueueUrl=queue_url,
          VisibilityTimeout=30
        )
        if 'Messages' in response and len(response['Messages']) > 0:
          print("Returning {} message".format(len(response['Messages'])))
          return response['Messages']
        print("get_message_from_queue(): Returning None")
        return None
      except TypeError as err:
        print("get_message_from_queue(): {}".format(err))
    return None

  def disable_admin_user(self, message):
    """Disables the admin user from the stack"""
    if self.is_valid_message(message):
      try:
         # make a request to the url in the message to remove an admin user
        url = "{}/alfresco/service/api/people/admin".format(message['stack_url'])
        username = os.getenv('username')
        headers = {
          "Accept":"application/json",
          "Content-Type":"application/json"
        }
        print("disable_admin_user(): {}".format(url))
        r = requests.put(url, data=json.dumps({"disableAccount": True}), headers=headers, auth=(username, username))
        print("Response from request is {}".format(r.status_code))
        r.raise_for_status()
        return True
      except requests.HTTPError as err:
        print("disable_admin_user() -> error: {}".format(err))
    return False

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
        data = {
          "userName": details['result'][0]['email'],
          "firstName": details['result'][0]['firstName'],
          "lastName": details['result'][0]['lastName'],
          "email": details['result'][0]['email'],
          "password": user_password,
          "groups": ["GROUP_ALFRESCO_ADMINISTRATORS"]
        }
        headers = {"Content-Type":"application/json"}
        r = requests.post(url, data=json.dumps(data), headers=headers, auth=(username, password))
        print("Response from request is {}".format(r.status_code))
        r.raise_for_status()
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
    try:
      return {
        "lastName": lead['message']['result'][0]['lastName'],
        "firstName": lead['message']['result'][0]['firstName'],
        "email": lead['message']['result'][0]['email'],
        "id": lead['message']['result'][0]['id'],
        "onlineTrialHostname": lead['stack_url'],
        "onlineTrialUsername": lead['message']['result'][0]['email'],
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
      data = self.create_marketo_data(lead)
      if data is not None:
        data['onlineTrialPassword'] = password
        data['onlineTrialExpiry'] = self.get_expiry_from_stack(lead['stack_id'])
        if self.marketo_client:
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
    if (self.is_valid_message(item)):
      assign_time = lambda: int(round(time.time() * 1000))
      response = self.dynamo_client.update_item(
        TableName=tablename,
        Key={
          'LeadId': {
            "N": str(item['message']['result'][0]['id'])
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
          ':u': {"S": json.dumps(item['message'])}
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
        return self.SUCCESS

      # process each message (should only be one but just in case)
      for message in messages:
        if message['MessageId'] not in m_ids:
          m_ids.append(message['MessageId'])
          m = self.sqs_res.Message(self.queue_url, message['ReceiptHandle'])
          message_body = json.load(m.body())

          # assign user to the stack by creating user on box
          password = self.assign_user_to_stack(message_body)
          if not password:
            print("Unable to add new user to stack")
            return self.FAILED

          # disable admin user
          if not self.disable_admin_user(message_body):
            print("Unable to disable admin user")
            return self.FAILED

          # update marketo lead
          result = self.update_marketo_lead(message_body, password)
          if not result['success']:
            print("Unable to upsert Marketo lead")
            return self.FAILED

          # if we got here, we are safe to add item to assign user table
          if not self.add_item_to_table(message_body):
            print("Unable to save item to table")
            return self.FAILED

          # All processed OK, delete message
          m.delete()
        else:
          print("Already received this message ({}), moving on".format(message['MessageId']))
      
      print("All messages processed OK")
      return self.SUCCESS
    except Exception as err:
      print("run(): {}".format(err))
    return self.FAILED

cls = AssignUserHandler(
  os.getenv('api_host', "https://453-liz-762.mktorest.com"),
  os.getenv('client_id', "35a7e1a3-5e60-40b2-bd54-674680af2adc"),
  os.getenv('client_secret', "thesecret"),
  os.getenv('sqs_read_url', "queue_url")
)

def handler(event, context):
  try:
    return cls.run()
  except Exception as err:
    print("{}".format(err))
  return cls.FAILED
