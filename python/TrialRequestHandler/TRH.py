from marketo import Marketo
from datetime import datetime

import json
import os
import boto3
import time

dynamo_client = boto3.client('dynamodb')
sqs_client = boto3.client('sqs')
sns_client = boto3.client('sns')

print('Getting message from SNS')

# main lambda function
def lambda_handler(event, context):
    try:
        message = event['Records'][0]['Sns']['Message']
        get_source = message['source']
        lead_id = message['lead']
        print("From SNS: {}".format(message))
        if get_source == 'onlinetrials':
            response = None
            count_attempts = 0
            while response == None:
                try:
                    response = details_marketo(lead_id)
                    count_attempts = count_attempts + 1
                    if count_attempts == 15:
                        break
                except IOError:
                    print("no response from marketo")
            if response != None:
                try:
                    fulfilled_test = 'y'
                    insert_into_dynamo(lead_id, response, fulfilled_test, count_attempts)
                    sqs_result = send_to_SQS(response)
                    return "Inserted fulfilled in dynamodb"
                except IOError:
                    print("no response from dynamodb")
            else:
                try:
                    fulfilled_test = 'n'
                    insert_into_dynamo(lead_id, response, fulfilled_test, count_attempts)
                    # notify IM solution
                    return "Inserted unfulfilled in dynamodb"
                except IOError:
                    print("no response from dynamodb")
    except EOFError:
        print("lambda handler failed for some error")


# function to obtain the details regarding the lead_id passed as a parameter
def details_marketo(lead_id):
    try:
        api_host = os.environ['api_host']
        client_id = os.environ['client_id']
        client_secret = os.environ['client_secret']
        m = Marketo(host = api_host, client_id = client_id, client_secret = client_secret)
        response_m = m.get_leads('id', lead_id)
        if(response_m != None):
            return response_m
        else:
            return None
    except IOError:
        print("an error has been found with the details")


# function to insert the request in the dynamodB table for the Trial Request Handler
def insert_into_dynamo(lead_id, response_m, fulfilled_test, count_attempts):
    try:
        curr_date = time.strftime("%d/%m/%Y")
        if response_m == None:
            response = dynamo_client.update_item(
                TableName=os.environ['trial_request_table'],
                Key={
                    'LeadId': {"N": str(lead_id)},
                    'Date': {"S": curr_date}
                },
                UpdateExpression= "set #Fulfilled = :f, #Attempts = :a, #RequestTime = :rt, #RequestMsg = :rm",
                ExpressionAttributeNames={
                    '#Fulfilled': "Fulfilled",
                    '#Attempts': "Attempts",
                    '#RequestTime': "RequestTime",
                    '#RequestMsg': "RequestMsg"
                },
                ExpressionAttributeValues={
                    ':f': {"S": fulfilled_test},
                    ':a': {"N": str(count_attempts)},
                    ':rt': {"N": '0'},
                    ':rm': {"S": str(response_m)}
            })
            if(response != None):
                print("UpdateItem succeeded:")
                return response
            else:
                print("UpdateItem Failed:")
                return None
        else:
            dt = datetime.strptime(response_m['result'][0]['createdAt'], "%Y-%m-%dT%H:%M:%SZ")
            request_time = time.mktime(dt.timetuple()) + (dt.microsecond / 1000000.0)
            request_time = int(request_time)
            response = dynamo_client.update_item(
                TableName=os.environ['trial_request_table'],
                Key={
                    'LeadId': {"N": str(lead_id)},
                    'Date': {"S": curr_date}
                },
                UpdateExpression= "set #Fulfilled = :f, #Attempts = :a, #RequestTime = :rt, #RequestMsg = :rm",
                ExpressionAttributeNames={
                    '#Fulfilled': "Fulfilled",
                    '#Attempts': "Attempts",
                    '#RequestTime': "RequestTime",
                    '#RequestMsg': "RequestMsg"
                },
                ExpressionAttributeValues={
                    ':f': {"S": fulfilled_test},
                    ':a': {"N": str(count_attempts)},
                    ':rt': {"N": str(request_time)},
                    ':rm': {"S": str(response_m)}
            })
            if(response != None):
                print("UpdateItem succeeded:")
                return response
            else:
                print("UpdateItem Failed:")
                return None
    except IOError:
        print("an error has been found. Data not inserted into the table")


# function to send the response from marketo to the SQS
def send_to_SQS(response):
    try:
        resp = sqs_client.send_message(QueueUrl=os.environ['sqs_url'],MessageBody=json.dumps(response))
        if(resp != None):
            return resp
        else:
            return None
    except IOError:
        print("an error has been found. Message not been sent to the queue")
