from __future__ import print_function
import json
import os
import boto3
import json
import six
import ast
import uuid, os

class TrialStackBuilder:
    def __init__(self,bucketname = os.environ['template_bucket_name'], stage = os.environ['stage']):
        try:
            self.cloud_client = boto3.client('cloudformation')
            self.ec2_client = boto3.client('ec2')
            self.s3_client= boto3.client('s3')
            self.bucketname = bucketname
            self.stage = stage
            self.template = None
        except Exception as err:
            message = "{0}\n".format(err)
            print(message)
            raise err

    def listStack(self ):
        stackList = []
        try:
            response = self.cloud_client.describe_stacks()
            stackList = response['Stacks']
        except Exception as err:
            message = "{0}\n".format(err)
            print(message)
            return None
        else :
            return stackList

    def countUnassignedStack(self ,stackList):
        count = 0
        try :
            for stack in stackList:
                if stack['StackStatus']=="CREATE_IN_PROGRESS" :
                    print("The stack {} is still creating".format(stack['StackName']))
                    count +=1
                elif stack['StackStatus']=="CREATE_COMPLETE" :
                    instanceId = self.findInstanceId(stack['Outputs'])
                    if instanceId == None :
                        raise TypeError
                    print("The InstanceId of the stack is: {}".format(instanceId))
                    instance = self.findInstance(instanceId)
                    if instance == None:
                        raise TypeError
                    unassigned = self.findUnassignedInstance(instance['Tags'])
                    if unassigned == None:
                        raise TypeError
                    if unassigned == True :   
                        count += 1 
                        print("The stack {} exists which is a unassigned stack.".format(stack['StackName']))
                    else:
                        print("The stack {}  is a not an unassigned stack.".format(stack['StackName']))
        except Exception as err:
            message = "{0}\n".format(err)
            print(message)
            return None
        else:
            return count
            
    def findUnassignedInstance(self ,instanceTags):
        if instanceTags != None:
            for tag in instanceTags:
                tagKey = tag['Key']
                if tagKey=='Allocated' :
                    if tag['Value']=='false':
                        return True
                    elif tag['Value']=='true':
                        return False
            return False
                
        else :
            return False
                    
        
    def findInstanceId(self ,stackOutputs):
        if stackOutputs :
            for output in stackOutputs:
                outputKey = output['OutputKey']
                if outputKey and isinstance(outputKey, str) and  outputKey.strip():
                    if outputKey == 'InstanceId':
                        return output['OutputValue']
                    
        else:
            return None
    
    def findInstance(self ,instanceId):
        if instanceId and isinstance(instanceId, six.string_types) and  instanceId.strip():
            try:
                instance = self.ec2_client.describe_tags(
                    Filters=[
                        {
                            'Name': 'resource-id',
                            'Values': [
                                instanceId,
                            ],
                        },
                    ],
                )
                return instance
            except Exception as err:
                message = "{0}\n".format(err)
                print(message)
                return None
        else:
            return None
            
    def getTemplate(self):
        branch = 'develop' if self.stage == 'test' else 'master'
        filename = "online-trial-stack-{}.yaml".format(branch)
        try :
            response = self.s3_client.get_object(
                Bucket=self.bucketname,
                Key=filename
            )
            template = response['Body'].read()
            return template
        except Exception as err:
            message = "{0}\n".format(err)
            print(message)
            return None
                     
    def createStack(self):
        try:
            branch = 'develop' if self.stage == 'test' else 'master'
            name = str(uuid.uuid1())
            name =  'TrialStack'+name.replace('-','')
            print (self.stage)
            response = self.cloud_client.create_stack(
                StackName=name,
                TemplateBody = self.template,
                Parameters=[
                {
                    'ParameterKey':'ControlArchitectureName',
                    'ParameterValue':"online-trial-control-{}".format(self.stage)
                },
                ],
                Capabilities=[
                    'CAPABILITY_IAM',
                ],
                OnFailure='ROLLBACK',
            )   
            return response['StackId']
        except Exception as err:
            message = "{0}\n".format(err)
            print(message)
            return None
        
    def run(self,event):
        try :
            if event['source']== None:
                raise TypeError
            try :
                stack_count = ast.literal_eval(os.environ['stack_count'])
            except Exception as err:
                raise err
            source = event['source']
            if source == 'aws.events':
                self.template = self.getTemplate()
                print ('Recieved the template from S3 Bucket')
                stackList = self.listStack()
                numberStack = self.countUnassignedStack(stackList)
                if numberStack == None:
                    raise TypeError  
                if(numberStack < stack_count):
                    stackToCreate = stack_count - numberStack 
                    print ('Number of stacks to be created: '+ str(stackToCreate))
                    for i in range(stackToCreate):
                        response = self.createStack()
                        print (response)
                        if response == None:
                            raise TypeError
                        else : 
                            print("The stack is created and its StackId is {} ".format(response))
                else:
                    print ('There is already {} unassigned stacks : '+ str(0))
                    print("All OK")
                    return 200
            else:
                self.template = self.getTemplate()
                print ('Recieved the template from S3 Bucket')
                response = self.createStack()
                if response == None:
                    raise TypeError
                else : 
                    print("The stack with name {} is created and its StackId is {} ".format(name, response))
                return 200
    
        except Exception as err:
            message = "{0}\n".format(err)
            print(message)
            return ('Failure due to : '+  "' ' ".join(str(x) for x in err.args))
        else:
            print("All OK")
            return 200
        
TSB = TrialStackBuilder()

def lambda_handler(event, context):
    try:
        return TSB.run(event)
    except Exception as err:
        print("{}".format(err))
        return 1