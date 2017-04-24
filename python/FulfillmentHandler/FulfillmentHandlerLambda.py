# // TODO implement and deploy in s3 bucket
# // Read from the trial request table for an unfulfilled request
# // Create an object to post to the SNS Topic that contains two keys
# // "source" and "lead". Source is "onlinetrial", "lead" is the lead id from the item
# // Publish that object/message onto the SNS Topic
# // (Fulfillment is satisfied by the trial request handler, not this handler)

from __future__ import print_function
import json, os, boto3, json, six, ast, time

os.environ['trial_request_table'] = '!Ref OnlineTrialRequestDynamoDbTable'
os.environ['topic_arn'] = '!Ref OnlineTrialRequestSNSTopic'

class FulfillmentHandler:
    def __init__(self):
        try:
            self.sns_res = boto3.resource('sns')
            self.dynamo_res = boto3.resource('dynamodb')
        except Exception as err:
            print("{}\n".format(err))
            raise err
            
    def readFromTable(self, dynamodb, name):
        try:
            table = dynamodb.Table(name)
            response = table.scan(
                ScanFilter = {
                    'Fulfilled': {
                        'AttributeValueList': [
                            'n'
                        ],
                        'ComparisonOperator': 'EQ'
                    }
                },
            )
            if response['Items'] is None:
                raise ValueError('No item found in the dynamoDb table')
            elif len(response['Items']) == 0:
                raise ValueError('No unfulfilled request found')
            return response['Items'][0]['LeadId']
        except Exception as err:
            print("{}\n".format(err))
        else:
            return None
    
    def createMessageObject(self, leadId):
        obj = { 
            'source': {
                'DataType': 'string',
                'StringValue': 'onlinetrial'
            },
            'lead': {
                'DataType': 'string',
                'StringValue': str(leadId)
            }
        }
        return obj

    def publishTopicSNS(self, sns_client, topic, obj):
        try:
            topic = sns.Topic('arn:aws:sns:us-east-1:179276412545:online-trial-control-test-OnlineTrialRequestSNSTopic-3MIYCD0W0S9Z')
            response = sns_client.publish(
                TopicArn = 'arn:aws:sns:us-east-1:179276412545:online-trial-control-test-OnlineTrialRequestSNSTopic-3MIYCD0W0S9Z',
                Message = 'string',
                MessageAttributes = obj
            )
            return response
        except Exception as err:
            print("{}\n".format(err))
        else:
            return None

    def run(self):
        try:
            leadId = self.readFromTable(self.dynamo_client, os.environ['trial_request_table'])
            if leadId is None:
                raise ValueError('Cannot read fron table')
            obj = self.createMessageObject(leadId)
            return 200
        except Exception as err:
            print("{}\n".format(err))
        else:
            return None
        
FH = FulfillmentHandler()

def lambda_handler(event, context):
    try:
        res = FH.run()
        if res is None:
            raise ValueError('The function has failed')
        print("All OK")
        return 200
    except Exception as err:
        print("{}".format(err))
    else:
        return None