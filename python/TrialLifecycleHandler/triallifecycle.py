from __future__ import print_function
from datetime import datetime, timedelta
import boto3
import os

def handler(event, context):
    try:
        handler = LifecycleHandler()
        handler.run()
        return 0
    except Exception as err:
        print("{}".format(err))
    return 1

class LifecycleHandler:
  """
  This class contains all the functions to handle the lifecycle of the Cloudformation Stacks.
  The rules are: After 14 days, extend the expiry date by 3 days then stop the instance if the instance is running.
  If the expiry date has passed and the instance has already been stopped, delete the cloudformation stack.
  """
  def __init__(self):
    self.cfn_client = boto3.client('cloudformation')
    self.ec2_client = boto3.client('ec2')
    self.TODAY = datetime.today()
    self.EXPIRY_KEY = 'ExpiryDate'
    self.STATES = ['CREATE_COMPLETE', 'UPDATE_COMPLETE']
    self.STACK_TYPE = os.environ['stack_type'] if os.environ.get('stack_type') else 'Trial'
    self.DAYS_TO_STOP = int(os.environ['days_to_stop']) if os.environ.get('days_to_stop') else 3

  def describe_stacks(self):
    """Describes all Cloudformation stacks and returns the result"""
    try:
      print('describe_stacks()')
      return self.cfn_client.describe_stacks()
    except Exception as err:
      print("{}".format(err))
      return None

  def describe_tags(self, instance_id):
    """Describes all the tags attached to an instance"""
    if instance_id:
      try:
        print("describe_tags(): {}".format(instance_id))
        return self.ec2_client.describe_tags(
            Filters=[
                {
                    'Name': 'resource-id',
                    'Values': [instance_id]
                }
            ]
        )
      except Exception as err:
        print("{}".format(err))
    return None

  def describe_instances(self, instance_id):
    """Describes an instanced metadata by instance id"""
    if instance_id:
      try:
        print("describe_instances(): {}".format(instance_id))
        return self.ec2_client.describe_instances(InstanceIds=[instance_id])
      except Exception as err:
        print("{}".format(err))
    return None

  def get_instance_id(self, stack):
    """returns the instance id from a list of outputs, if present"""
    if stack and stack['StackStatus'] in self.STATES:
      is_good_stack = False
      while True:
        for output in stack['Outputs']:
          if not is_good_stack and output['OutputKey'] == 'Type' and output['OutputValue'] == self.STACK_TYPE:
            is_good_stack = True

          if is_good_stack and output['OutputKey'] == 'InstanceId':
            print("get_instance_id(): returning {}".format(output['OutputValue']))
            return output['OutputValue']
    print('get_instance_id(): Returning nothing!')
    return ""

  def update_tags(self, instance_id, tags):
    """Updates the given tags list onto the instance id"""
    if instance_id and len(tags) > 0:
      print("update_tags(): {}, {}".format(instance_id, tags))
      for tag in tags:
        if 'Key' not in tag and 'Value' not in tag:
          raise Exception('Tags in incorrect structure. Unable to update tags')
      
      print("{} is still running, updating tags".format(instance_id))
      return self.ec2_client.create_tags(
        Resources=[instance_id],
        Tags=tags
      )
    return None

  def stop_instance(self, instance_id):
    """Stops an instance by instance id"""
    if instance_id:
      print("Stopping Instance {0}".format(instance_id))
      return self.ec2_client.stop_instances(InstanceIds=[instance_id])
    return None

  def terminate_stack(self, stack):
    """Terminates a Cloudformation stack by using a stack object"""
    if stack and 'StackId' in stack and 'StackName' in stack:
      print("Instance expired and stopped, deleting cfn stack {}".format(stack['StackId']))
      return self.cfn_client.delete_stack(StackName=stack['StackName'])
    return None
  
  def run(self):
    """ Runs the handler, based on the rules"""
    print('Running LifecycleHandler...')
    response = self.describe_stacks()
    if response is None:
      raise Exception('Unable to retrieve list of cloudformation stacks')

    for stack in response['Stacks']:
      instance_id = self.get_instance_id(stack)
      print("We have an instance {}".format(instance_id))
      if instance_id:
        tags = self.describe_tags(instance_id)
        if tags is None:
          # raise error, instance must be tagged
          raise Exception("Unable to get tags from {}".format(instance_id))

        for tag in tags['Tags']:
          if tag['Key'] == self.EXPIRY_KEY:
            expiry_date = datetime.strptime(tag['Value'], '%Y-%m-%d')
            print("Expiry date on {} is {}".format(instance_id, str(expiry_date.date())))
            if self.TODAY > expiry_date:
              print("Instance {} has passed expiry date".format(instance_id))
              status = self.describe_instances(instance_id)
              if status is None:
                raise Exception("Unable to describe instance {}".format(instance_id))
              
              # Should only be the single instance
              for state in status['Reservations'][0]['Instances']:
                print("Current state is {}".format(state['State']['Name']))
                if state['State']['Name'] == 'running':
                  # add n days to expiry date, stop instance
                  new_expiry_date = expiry_date + timedelta(days=self.DAYS_TO_STOP)
                  print("New expiry date is {0}".format(str(new_expiry_date.date())))
                  updated_tags = self.update_tags(instance_id, [
                    {
                      'Key': self.EXPIRY_KEY,
                      'Value': str(new_expiry_date.date())
                    }
                  ])
                  if updated_tags is None:
                    raise Exception('Unable to update tags.')
                  
                  if self.stop_instance(instance_id) is None:
                    raise Exception("Unable to stop instance {}".format(instance_id))

                  break
                elif state['State']['Name'] == 'stopped':
                  # terminate the cfn stack
                  if self.terminate_stack(stack) is None:
                    raise Exception("Unable to terminate stack {}".format(stack['StackName']))
                  break
            else:
              print("{} has not expired yet.".format(stack['StackName']))
