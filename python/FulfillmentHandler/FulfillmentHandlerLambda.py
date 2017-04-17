# // TODO implement and deploy in s3 bucket
# // Read from the trial request table for an unfulfilled request
# // Create an object to post to the SNS Topic that contains two keys
# // "source" and "lead". Source is "onlinetrial", "lead" is the lead id from the item
# // Publish that object/message onto the SNS Topic
# // (Fulfillment is satisfied by the trial request handler, not this handler)

from __future__ import print_function
import json, os, boto3, json, six, ast

class FulfillmentHandler:
    def __init__(self):
        try:
            self.sns_client = boto3.client('sns')
            self.dynamo_client = boto3.client('dynamodb')
        except Exception as err:
            message = "{0}\n".format(err)
            print(message)
            raise err

    def run(self):
        try :
            print (0)
        except Exception as err:
            message = "{0}\n".format(err)
            print(message)
            return ('Failure due to : '+  "' ' ".join(str(x) for x in err.args))
        else:
            print("All OK")
            return 200
        
FH = FulfillmentHandler()

def lambda_handler(event, context):
    try:
        return FH.run()
    except Exception as err:
        print("{}".format(err))
        return 1