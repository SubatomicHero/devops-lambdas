from __future__ import print_function
import json
import os
import boto3
import json
import six


def lambda_handler(event, context):
    try :
        IRH = TrialStackBuilder()
        
    except Exception as err:
        message = "{0}\n".format(err)
        print(message)
        raise err
    else:
        print("All OK")
        return 200

class TrialStackBuilder:
    def __init__(self):
        try:
            self.cloud_client = boto3.client('cloudformation')
        except Exception as err:
            message = "{0}\n".format(err)
            print(message)
            raise err
        
    