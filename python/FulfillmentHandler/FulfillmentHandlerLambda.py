from __future__ import print_function
import json, os, boto3, json, six, ast, time

class FulfillmentHandler:
    def __init__(self, table=os.getenv('trial_request_table', None), topic=os.getenv('topic_arn', None)):
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
                print ('No unfulfilled request found')
            return response['Items']
        except Exception as err:
            print("{}".format(err))
        else:
            return None
    
    def createMessageObject(self, leadId):
        return { 
            'source': 'onlinetrial',
            'lead': str(leadId)
        }

    def publishTopicSNS(self, topicArn, obj):
        try:
            if topicArn is None or not (isinstance(topicArn, six.string_types)):
                raise ValueError('No valid topicArn')
            response = self.sns_client.publish(
                TopicArn = topicArn,
                Message = json.dumps({'default': json.dumps(obj)}),
                MessageStructure = 'json'
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
            items = self.readFromTable(self.tableName)
            for item in items:
                leadId = item['LeadId']
                if leadId is None:
                    raise ValueError('We need a lead before trying to create an object')
                print('The unfulfilled request with the leadId {}, is retrieved from the trial request table.'.format(leadId))
                obj = self.createMessageObject(leadId)
                print('The object containing the keys "source":{} and "lead":{} is created'.format(obj['source'], obj['lead']))
                response = self.publishTopicSNS(self.topicArn, obj)
                if response is None:
                    raise ValueError('Cannot publish SNS message')
                print('The object is successfully published to SNS')
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