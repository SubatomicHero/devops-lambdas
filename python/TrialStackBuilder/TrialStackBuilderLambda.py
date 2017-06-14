import os
import uuid
import boto3
import six

class TrialStackBuilder(object):
    """
    TrialStackBuilder checks on a schedule how many stacks to build
    to keep the pool maintained
    """
    def __init__(self, bucketname=os.getenv('template_bucket_name'), stage=os.getenv('stage')):
        try:
            self.cloud_client = boto3.client('cloudformation')
            self.ec2_client = boto3.client('ec2')
            self.s3_client = boto3.client('s3')
            self.bucketname = bucketname
            self.stage = stage
            self.template = None
        except Exception as err:
            print "{}\n".format(err)
            raise err

    def list_stack(self, token=None):
        """
        Lists all the stacks by name as some may not be created yet
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
                if "trial-{}".format(self.stage) in stack['StackName']:
                    stacks.append(stack)
            if 'NextToken' in response:
                stacks = stacks + self.list_stack(response['NextToken'])
            return stacks
        return None

    def count_unassigned_stack(self, stack_list):
        """
        returns a count of unassigned stacks
        """
        count = 0
        for stack in stack_list:
            if stack['StackStatus'] == "CREATE_IN_PROGRESS":
                print "The stack {} is still creating".format(stack['StackName'])
                count += 1
            elif stack['StackStatus'] == "CREATE_COMPLETE":
                instance_id = self.find_instance_id(stack['Outputs'])
                if not instance_id:
                    raise ValueError('Cannot count stack without instance id')
                instance = self.find_instance(instance_id)
                if not instance:
                    raise ValueError('Cannot find any valid instance')
                unassigned = self.find_unassigned_instance(instance['Tags'])
                if unassigned is None:
                    raise ValueError('Cannot find any unassigned instance')
                elif unassigned:
                    count += 1
        return count

    def find_unassigned_instance(self, instance_tags):
        """
        Finds an unassigned instance
        """
        if instance_tags != None:
            for tag in instance_tags:
                tag_key = tag['Key']
                if tag_key == 'Allocated':
                    if tag['Value'] == 'false':
                        return True
                    elif tag['Value'] == 'true':
                        return False
        return False

    def find_instance_id(self, stack_outputs):
        """
        Finds the instance id from the list of stack outputs
        """
        if stack_outputs:
            for output in stack_outputs:
                output_key = output['OutputKey']
                if output_key and isinstance(output_key, str) and output_key.strip():
                    if output_key == 'InstanceId':
                        return output['OutputValue']
        return None

    def find_instance(self, instance_id):
        """
        Finds an instance and returns it
        """
        if instance_id and isinstance(instance_id, six.string_types) and instance_id.strip():
            return self.ec2_client.describe_tags(
                Filters=[
                    {
                        'Name': 'resource-id',
                        'Values': [
                            instance_id,
                        ],
                    },
                ],
            )
        return None

    def get_template(self):
        """
        Gets the cfn template from a bucket
        """
        try:
            branch = 'develop' if self.stage == 'test' else 'master'
            response = self.s3_client.get_object(
                Bucket=self.bucketname,
                Key="online-trial-stack-{}.yaml".format(branch)
            )
            print 'Received the template from S3 Bucket'
            return response['Body'].read()
        except Exception as err:
            print "{}\n".format(err)
        else:
            return None

    def create_stack(self):
        """
        Creates a cfn stack
        """
        try:
            unique_id = str(uuid.uuid1()).replace('-', '')
            name = "trial-{}-{}".format(self.stage, unique_id)
            response = self.cloud_client.create_stack(
                StackName=name,
                TemplateBody=self.template,
                Parameters=[
                    {
                        'ParameterKey' : 'ControlArchitectureName',
                        'ParameterValue' : "online-trial-control-{}".format(self.stage)
                    },
                    {
                        'ParameterKey' : 'AdminUsername',
                        'ParameterValue' : os.getenv('username', 'admin')
                    },
                    {
                        'ParameterKey' : 'AdminPassword',
                        'ParameterValue' : os.getenv('password', 'admin')
                    }
                ],
                Capabilities=[
                    'CAPABILITY_IAM',
                ],
                OnFailure='DELETE',
                Tags=[
                    {
                        'Key': 'Stage',
                        'Value': self.stage
                    },
                    {
                        'Key': 'Type',
                        'Value': 'Trial'
                    }
                ]
            )
            return response['StackId']
        except Exception as err:
            print "{}\n".format(err)
        else:
            return None

    def run(self, event):
        """
        Runs the TrialStackBuilder
        """
        try:
            if event['source'] is None:
                raise ValueError('Cannot find any event to the lambda')
            stack_count = int(os.getenv('stack_count', '5'))
            if stack_count is None:
                raise ValueError('Cannot find any stack count')
            source = event['source']
            self.template = self.get_template()
            if self.template is None:
                raise ValueError('Cant build stacks without a template')
            if source == 'aws.events':
                number_stack = self.count_unassigned_stack(self.list_stack())
                if number_stack is None:
                    raise ValueError('Cannot count any unassigned stack')
                if number_stack == 0:
                    # future requirement, send message to slack/teams/whatevs
                    print "***** 0 stacks ready *****"
                if number_stack < stack_count:
                    stack_to_create = stack_count - number_stack
                    print 'Number of stacks to be created: {} '.format(stack_to_create)
                    for _ in range(stack_to_create):
                        stack_id = self.create_stack()
                        if stack_id is None:
                            raise ValueError('Cannot create the stack')
                        # print("The stack is created and its StackId is {} ".format(stack_id))
                    return 200
                print 'There is already {} unassigned stack(s)'.format(stack_count)
                return 200
            else:
                response = self.create_stack()
                if response is None:
                    raise ValueError('Cannot create the stack')
                else:
                    # print("The stack is created and its StackId is {} ".format(response))
                    return 200
        except Exception as err:
            print "{}\n".format(err)
        else:
            return 'FAILURE'

TSB = TrialStackBuilder()

def lambda_handler(event, context):
    """
    lambda_handler
    """
    try:
        res = TSB.run(event)
        if res == 'FAILURE':
            raise ValueError('The function has failed')
        return 200
    except Exception as err:
        print "{}".format(err)
    else:
        return 'FAILURE'
