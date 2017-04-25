from __future__ import print_function
import json, os, boto3, json, six, ast, time

os.environ['trial_request_table'] = 'online-trial-control-test-OnlineTrialRequestDynamoDbTable-15CBTG54YDU3W'
os.environ['topic_arn'] = 'arn:aws:sns:us-east-1:179276412545:online-trial-control-test-OnlineTrialRequestSNSTopic-3MIYCD0W0S9Z'

class FulfillmentHandler:
    def __init__(self, table = os.environ['trial_request_table'], topic = os.environ['topic_arn']):
        try:
            self.sns_client = boto3.client('sns')
            self.dynamo_res = boto3.resource('dynamodb')
            self.tableName = table
            self.topicArn = topic
        except Exception as err:
            print("{}".format(err))
            raise err
            
    def readFromTable(self, tableName):
        try:
            if tableName is None or not (isinstance(tableName, six.string_types)):
                raise ValueError('Table name is not valid')
            table = self.dynamo_res.Table(tableName)
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
            if len(response['Items']) == 0:
                raise ValueError('No unfulfilled request found')
            return response['Items'][0]['LeadId']
        except Exception as err:
            print("{}".format(err))
        else:
            return None
    
    def createMessageObject(self, leadId):
        try:
            if leadId is None or not (isinstance(leadId, six.string_types)):
                raise ValueError('No valid leadId')
            obj = { 
                'source': {
                    'DataType': 'String',
                    'StringValue': 'onlinetrial'
                },
                'lead': {
                    'DataType': 'String',
                    'StringValue': leadId
                }
            }
            return obj
        except Exception as err:
            print("{}".format(err))
        else:
            return None

    def publishTopicSNS(self, topicArn, obj):
        try:
            if topicArn is None or not (isinstance(topicArn, six.string_types)):
                raise ValueError('No valid topicArn')
            response = self.sns_client.publish(
                TopicArn = topicArn,
                Message = 'string',
                MessageAttributes = obj
            )
            if response is None:
                raise ValueError('Cannot publish the topic')
            return response
        except Exception as err:
            print("{}".format(err))
        else:
            return None

    def run(self):
        try:
            leadId = self.readFromTable(self.tableName)
            if leadId is None:
                raise ValueError('Cannot read from table')
            print ('The unfulfilled request with the leadId {}, is retrieved from the trial request table.'.format(leadId))
            obj = self.createMessageObject(leadId)
            if obj is None:
                raise ValueError('Cannot create an object')
            print ('The object containing the keys "source":{} and "lead":{} is created'.format(obj['source']['StringValue'], obj['lead']['StringValue']))
            response = self.publishTopicSNS(self.topicArn, obj)
            if response is None:
                raise ValueError('Cannot publish SNS message')
            print ('The object is successfully published to SNS')
            return 200
        except Exception as err:
            print("{}".format(err))
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
        return 'FAILURE'