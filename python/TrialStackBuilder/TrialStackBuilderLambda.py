import boto3
import json
import six
import uuid, os

class TrialStackBuilder:
    def __init__(self, bucketname=os.getenv('template_bucket_name', 'online-trial-control-tes-onlinetrialstacktemplate-gt9u28jnoe48'), stage=os.getenv('stage', 'test')):
        try:
            self.cloud_client = boto3.client('cloudformation')
            self.ec2_client = boto3.client('ec2')
            self.s3_client = boto3.client('s3')
            self.bucketname = bucketname
            self.stage = stage
            self.template = None
        except Exception as err:
            message = "{0}\n".format(err)
            print(message)
            raise err

    def listStack(self):
        try:
            response = self.cloud_client.describe_stacks()
            if response['Stacks'] is None:
                raise ValueError('There is no stack')
            
            # only return stacks that are trial stacks, not other stacks in the list
            stacks = []
            for stack in response['Stacks']:
                if stack['StackName'].startswith("trial-{}".format(self.stage)):
                    stacks.append(stack)
            print("Returning {} stack(s)".format(len(stacks)))
            return stacks
        except Exception as err:
            print("{}\n".format(err))
        else:
            return None

    def countUnassignedStack(self, stackList):
        try:
            count = 0
            for stack in stackList:
                if stack['StackStatus'] == "CREATE_IN_PROGRESS":
                    print("The stack {} is still creating".format(stack['StackName']))
                    count += 1
                elif stack['StackStatus'] == "CREATE_COMPLETE":
                    instanceId = self.findInstanceId(stack['Outputs'])
                    if instanceId == None:
                        raise ValueError('Cannot count stack without instance id')
                    print("The InstanceId of the stack is: {}".format(instanceId))
                    instance = self.findInstance(instanceId)
                    if instance == None:
                        raise ValueError('Cannot find any valid instance')
                    unassigned = self.findUnassignedInstance(instance['Tags'])
                    if unassigned == None:
                        raise ValueError('Cannot find any unassigned instance')
                    elif unassigned == True:   
                        count += 1 
                        print("The stack {} exists which is a unassigned stack.".format(stack['StackName']))
                    else:
                        print("The stack {}  is a not an unassigned stack.".format(stack['StackName']))
            return count
        except Exception as err:
            print("{}\n".format(err))
        else:
            return None
            
    def findUnassignedInstance(self, instanceTags):
        try:
            if instanceTags != None:
                for tag in instanceTags:
                    tagKey = tag['Key']
                    if tagKey == 'Allocated':
                        if tag['Value'] == 'false':
                            return True
                        elif tag['Value'] == 'true':
                            return False
                return False
            else:
                raise ValueError('There is no valid tag for the instance')
        except Exception as err:
            print("{}\n".format(err))
        else:
            return None
                    
    def findInstanceId(self, stackOutputs):
        try:
            if stackOutputs:
                for output in stackOutputs:
                    outputKey = output['OutputKey']
                    if outputKey and isinstance(outputKey, str) and outputKey.strip():
                        if outputKey == 'InstanceId':
                            return output['OutputValue']
            else:
                raise ValueError('There is no valid output for the instance')
        except Exception as err:
            print("{}\n".format(err))
        else:
            return None
    
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
                raise ValueError('Cannot find any valid instance id')
        except Exception as err:
            print("{}\n".format(err))
        else:
            return None
            
    def getTemplate(self):
        try :
            branch = 'develop' if self.stage == 'test' else 'master'
            filename = "online-trial-stack-{}.yaml".format(branch)
            response = self.s3_client.get_object(
                Bucket = self.bucketname,
                Key = filename
            )
            template = response['Body'].read()
            print ('Received the template from S3 Bucket')
            return template
        except Exception as err:
            print("{}\n".format(err))
        else:
            return None
                     
    def createStack(self):
        try:
            branch = 'develop' if self.stage == 'test' else 'master'
            unique_id = str(uuid.uuid1()).replace('-', '')
            name = "trial-{}-{}".format(self.stage, unique_id)
            response = self.cloud_client.create_stack(
                StackName = name,
                TemplateBody = self.template,
                Parameters = [
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
                Capabilities = [
                    'CAPABILITY_IAM',
                ],
                OnFailure = 'DELETE',
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
            print("{}\n".format(err))
        else:
            return None
        
    def run(self, event):
        try:
            if event['source'] is None:
                raise ValueError('Cannot find any event to the lambda')
            stack_count = int(os.getenv('stack_count', '5'))
            if stack_count is None:
                raise ValueError('Cannot find any stack count')
            source = event['source']
            print("The source is {}".format(source))
            self.template = self.getTemplate()
            if self.template is None:
                raise ValueError('Cant build stacks without a template')   
            if source == 'aws.events':
                numberStack = self.countUnassignedStack(self.listStack())
                if numberStack is None:
                    raise ValueError('Cannot count any unassigned stack')
                if numberStack == 0:
                    # future requirement, send message to slack/teams/whatevs
                    print("***** 0 stacks ready *****")
                if(numberStack < stack_count):
                    stackToCreate = stack_count - numberStack 
                    print ('Number of stacks to be created: {} '.format(stackToCreate))
                    for i in range(stackToCreate):
                        stack_id = self.createStack()
                        if stack_id is None:
                            raise ValueError('Cannot create the stack')
                        print("The stack is created and its StackId is {} ".format(stack_id))
                    return 200
                print ('There is already {} unassigned stack(s)'.format(stack_count))
                return 200
            else:
                response = self.createStack()
                if response == None:
                    raise ValueError('Cannot create the stack')
                else: 
                    print("The stack is created and its StackId is {} ".format(response))
                    return 200
        except Exception as err:
            print("{}\n".format(err))
        else:
            return 'FAILURE'
        
TSB = TrialStackBuilder()

def lambda_handler(event, context):
    try:
        res = TSB.run(event)
        if res == 'FAILURE':
            raise ValueError('The function has failed')
        return 200
    except Exception as err:
        print("{}".format(err))
    else:
        return 'FAILURE'