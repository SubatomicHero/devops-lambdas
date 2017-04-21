from marketo import Marketo
from datetime import datetime

import json
import os
import boto3
import time

dynamo_client = boto3.client('dynamodb')
sqs_client = boto3.client('sqs')

class TrialRequestHandler:
    def details_marketo(self, lead_id):
        """function to obtain the details regarding the lead_id passed as a parameter"""
        try:
            m = Marketo(host=os.environ['api_host'], client_id=os.environ['client_id'], client_secret=os.environ['client_secret'])
            return m.get_leads('id', lead_id)
        except IOError as ioerr:
            raise IOError("an error has been found with the details: {}".format(ioerr))
        else:
            return None

    def insert_into_dynamo(self, lead_id, response_m, fulfilled_test, count_attempts):
        """function to insert the request in the dynamodB table for the Trial Request Handler"""
        try:
            curr_date = time.strftime("%d/%m/%Y")
            request_time = '0'
            if not response_m:
                dt = datetime.strptime(response_m['result'][0]['createdAt'], "%Y-%m-%dT%H:%M:%SZ")
                request_time = int(time.mktime(dt.timetuple()) + (dt.microsecond / 1000000.0))
            
            response = dynamo_client.update_item(
                TableName=os.environ['trial_request_table'],
                Key={
                    'LeadId': {"N": str(lead_id)},
                    'Date': {"S": curr_date}
                },
                UpdateExpression="set #Fulfilled = :f, #Attempts = :a, #RequestTime = :rt, #RequestMsg = :rm",
                ExpressionAttributeNames={
                    '#Fulfilled': "Fulfilled",
                    '#Attempts': "Attempts",
                    '#RequestTime': "RequestTime",
                    '#RequestMsg': "RequestMsg"
                },
                ExpressionAttributeValues={
                    ':f': {"S": fulfilled_test},
                    ':a': {"N": str(count_attempts)},
                    ':rt': {"S": request_time},
                    ':rm': {"S": str(response_m)}
            })
            print("Update item succeeded")
            return True if response_m else False
        except:
            raise IOError('an error has been found. Data not inserted into the table')
        else:
            return None

    def send_to_SQS(self, response):
        """function to send the response from marketo to the SQS"""
        try:
            return sqs_client.send_message(QueueUrl=os.environ['sqs_url'], MessageBody=json.dumps(response))
        except IOError as ioerr:
            raise IOError("an error has been found. Message not been sent to the queue: {}".format(ioerr))
        else:
            return None

handler = TrialRequestHandler()

# main lambda function
def lambda_handler(event, context):
    try:
        if 'Records' in event:
            print('Getting message from SNS')
            for record in event['Records']:
                message = record['Sns']['Message']
                get_source = message['source']
                lead_id = message['lead']
                print("From SNS: {}".format(message))
                if get_source is 'onlinetrials':
                    print("Processing online trial request")
                    response = handler.details_marketo(lead_id)
                    count_attempts = 0
                    while response is None and count_attempts < 10:
                        try:
                            print("Trying again after 10 seconds")
                            count_attempts += 1
                            time.sleep(10)
                            response = handler.details_marketo(lead_id)
                        except IOError as ioerr:
                            print("Marketo error: {}".format(ioerr))
                    
                    if response:
                        print("Details received from marketo: {}".format(response))
                    fulfilled_test = 'y' if response is not None else 'n'
                    try:
                        if handler.insert_into_dynamo(lead_id, response, fulfilled_test, count_attempts) is True:
                            print("Record inserted to DB")
                            if handler.send_to_SQS(response) is not None:
                                print("Message sent to queue")
                        else:
                            print("Not sending message to queue, unable to get response from Marketo")
                    except IOError as ioerr:
                        print("no response from dynamodb (unfulfilled)")
    except EOFError:
        print("lambda handler failed")
