from __future__ import print_function
from datetime import datetime, timedelta
import os
import boto3

class LifecycleHandler(object):
    """
    This class contains all the functions to handle the lifecycle of the Cloudformation Stacks.
    The rules are:
      - After 14 days, extend the expiry date by n days and stop the instance.
      - If the expiry date has passed and the instance has stopped, delete the cloudformation stack.
    """
    def __init__(self):
        self.cfn_client = boto3.client('cloudformation')
        self.ec2_client = boto3.client('ec2')
        self.expiry_key = 'ExpiryDate'
        self.states = ['CREATE_COMPLETE', 'UPDATE_COMPLETE']
        self.stack_type = os.getenv('stack_type', 'Trial')
        self.days_to_stop = int(os.getenv('days_to_stop', 3))
        self.stage = os.getenv('stage', 'test')

    def describe_stacks(self):
        """
        Describes all Cloudformation stacks and returns the result.
        Only returns stacks we are looking for
        """
        try:
            print('describe_stacks()')
            response = {}
            response['Stacks'] = []
            for stack in self.cfn_client.describe_stacks()['Stacks']:
                is_trial = False
                is_correct_stage = False
                if 'Outputs' in stack:
                    for output in stack['Outputs']:
                        if output['OutputKey'] == 'Type' and output['OutputValue'] == self.stack_type:
                            is_trial = True
                        if output['OutputKey'] == 'Stage' and output['OutputValue'] == self.stage:
                            is_correct_stage = True
                        if is_correct_stage and is_trial:
                            response['Stacks'].append(stack)
                            break
            return response
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
        if stack and stack['StackStatus'] in self.states:
            # if one of the outputs keys is type and the value is stack_type, get the instance id
            print("get_instance_id(): {}".format(stack['StackName']))
            if 'Outputs' in stack:
                for output in stack['Outputs']:
                    if output['OutputKey'] == 'InstanceId':
                        print("get_instance_id(): returning {}".format(output['OutputValue']))
                        return output['OutputValue']
        print("Returning nothing. No instance id output")
        return None

    def update_tags(self, instance_id, tags):
        """Updates the given tags list onto the instance id"""
        if instance_id and tags:
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
            print("Stopping Instance {}".format(instance_id))
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
            raise ValueError('Unable to retrieve list of cloudformation stacks')

        for stack in response['Stacks']:
            instance_id = self.get_instance_id(stack)
            if instance_id:
                print("We have an instance {}".format(instance_id))
                tags = self.describe_tags(instance_id)
                if tags is None:
                    # raise error, instance must be tagged
                    raise ValueError("Unable to get tags from {}".format(instance_id))

                for tag in tags['Tags']:
                    if tag['Key'] == self.expiry_key:
                        expiry_date = datetime.strptime(tag['Value'], '%d-%m-%Y')
                        str_date = str(expiry_date.date().strftime("%d-%m-%Y"))
                        print("Expiry date on {} is {}".format(instance_id, str_date))
                        today = datetime.today().strftime("%d-%m-%Y")
                        str_today = datetime.strptime(today, "%d-%m-%Y")
                        if str_today > expiry_date:
                            print("Instance {} has passed expiry date".format(instance_id))
                            status = self.describe_instances(instance_id)
                            if status is None:
                                raise ValueError("Unable to describe {}".format(instance_id))

                            # Should only be the single instance
                            for state in status['Reservations'][0]['Instances']:
                                print("Current state is {}".format(state['State']['Name']))
                                if state['State']['Name'] == 'running':
                                    # add n days to expiry date, stop instance
                                    new_expiry_date = expiry_date + timedelta(days=self.days_to_stop)
                                    ned = new_expiry_date.date().strftime("%d-%m-%Y")
                                    print("New expiry date is {}".format(ned))
                                    updated_tags = self.update_tags(instance_id, [
                                        {
                                            'Key': self.expiry_key,
                                            'Value': ned
                                        }
                                    ])
                                    if updated_tags is None:
                                        raise ValueError('Unable to update tags.')
                                    if self.stop_instance(instance_id) is None:
                                        raise ValueError("Unable to stop {}".format(instance_id))
                                    break
                                elif state['State']['Name'] == 'stopped':
                                    # terminate the cfn stack
                                    if self.terminate_stack(stack) is None:
                                        raise ValueError("Unable to terminate {}".format(stack['StackName']))
                                    break
                                elif state['State']['Name'] == 'stopping':
                                    # the instance is still stopping
                                    print("Skipping {}, its still stopping".format(instance_id))
                                    break
                        else:
                            print("{} has not expired yet.".format(stack['StackName']))
                        break
            else:
                print("Stack Id {} is not a trial stack".format(stack['StackId']))
        print("No more stacks to assess")
        return 0

CLS = LifecycleHandler()

def handler(event, context):
    """Lambda Handler"""
    try:
        return CLS.run()
    except ValueError as verr:
        print("{}".format(verr))
    return 1
