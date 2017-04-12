from __future__ import print_function
import json
import os
import boto3
import json
import six
import ast
import uuid


os.environ['stack_count'] = '5'
os.environ['template_bucket_name'] = 'online-trial-control-tes-onlinetrialstacktemplate-ak21n1yv3vdc'
os.environ['stage'] = 'test'



class TrialStackBuilder:
    def __init__(self):
        try:
            self.cloud_client = boto3.client('cloudformation')
            self.ec2_client = boto3.client('ec2')
            self.s3_client = boto3.client('s3')
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
            
                
    def createStack(self):
        try:
            name = str(uuid.uuid1())
            name =  'TrialStack'+name.replace('-','')
            branch = 'develop' if os.environ['stage'] == 'test' else 'master'
            filename = "online-trial-stack-{}.yaml".format(branch)
            URL = "https://s3.amazonaws.com/{}/{}".format(os.environ['template_bucket_name'], filename)
            response = self.cloud_client.create_stack(
                StackName=name,
                TemplateURL=URL,
                Parameters=[
                {
                    'ParameterKey':'ControlArchitectureName',
                    'ParameterValue':"online-trial-stack-{}".format(branch)
                },
                ],
                Capabilities=[
                    'CAPABILITY_IAM',
                ],
                OnFailure='ROLLBACK',
            )   
            print("The stack with name {} is created and its StackId {} is ".format(name, response['StackId']))
            return response['StackId']
        except Exception as err:
            message = "{0}\n".format(err)
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
                stackList = TSB.listStack()
                numberStack = TSB.countUnassignedStack(stackList)
                if numberStack == None:
                    raise TypeError  
                if(numberStack < stack_count):
                    stackToCreate = stack_count - numberStack 
                    print ('Number of stacks to be created: '+ str(stackToCreate))
                    for i in range(stackToCreate):
                        response = TSB.createStack()
                        if response == None:
                            raise TypeError
                else:
                    print ('Number of stacks to be created: '+ str(0))
                    print("All OK")
                    return 200
            else:
                response = TSB.createStack()
                if response == None:
                    raise TypeError
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