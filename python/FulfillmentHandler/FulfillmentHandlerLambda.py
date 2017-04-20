# // TODO implement and deploy in s3 bucket
# // Read from the trial request table for an unfulfilled request
# // Create an object to post to the SNS Topic that contains two keys
# // "source" and "lead". Source is "onlinetrial", "lead" is the lead id from the item
# // Publish that object/message onto the SNS Topic
# // (Fulfillment is satisfied by the trial request handler, not this handler)

from __future__ import print_function
import json, os, boto3, json, six, ast

class FulfillmentHandler:
    def __init__(self, table = os.environ['trial_request_table']):
        try:
            self.sns_client = boto3.client('sns')
            self.dynamo_client = boto3.client('dynamodb')
            self.trial_request_table = table
        except Exception as err:
            print("{}\n".format(err))
            raise err
            
    def readFromTable(self, table):
        try:
            response = self.dynamo_client.get_item(
                TableName = table.name,
                Key={
                    'leadID': {
                        'S' : 'n'
                    }

                }
            )
            return response
        except Exception as err:
            print("{}\n".format(err))
        else:
            return None

    def run(self):
        try :
            resp = self.readFromTable(self.trial_request_table)
            if resp is None:
                raise ValueError('Cannot read fron table')
            print ('All ok')
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