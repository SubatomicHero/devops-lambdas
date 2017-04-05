from marketo import Marketo

import json
import os
import boto3
import datetime
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
        print("From SNS: " + get_source)
        if get_source == 'onlinetrials':
            response = ""
            count_attemps = 0
            while response == "":
                try:
                    response = details_marketo(lead_id)
                    count_attemps = count_attemps + 1
                    if count_attemps == 15:
                        break
                except IOError:
                    print("no response from marketo")
            if response != "":
                try:
                    fulfilled_test = 'y'
                    insert_into_dynamo(lead_id, response, fulfilled_test, count_attemps)
                    sqs_result = send_to_SQS(response)
                    return "Inserted fulfilled in dynamodb"
                except IOError:
                    print("no response from dynamodb")
            else:
                try:
                    fulfilled_test = 'n'
                    insert_into_dynamo(lead_id, response, fulfilled_test, count_attemps)
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
        return response_m
    except IOError:
        print("an error has been found with the details")


# function to insert the request in the dynamodB table for the Trial Request Handler
def insert_into_dynamo(lead_id, response_m, fulfilled_test, count_attemps):
    try:
        curr_date = time.strftime("%d/%m/%Y")
        if response_m == "":
            response = dynamo_client.update_item(
                TableName=os.environ['trial_request_table'],
                Key={
                    'LeadId': {"N": str(lead_id)},
                    'Date': {"S": curr_date}
                },
                UpdateExpression= "set #Fulfilled = :f, #Attemps = :a, #RequestTime = :rt, #RequestMsg = :rm",
                ExpressionAttributeNames={
                    '#Fulfilled': "Fulfilled",
                    '#Attemps': "Attemps",
                    '#RequestTime': "RequestTime",
                    '#RequestMsg': "RequestMsg"
                },
                ExpressionAttributeValues={
                    ':f': {"S": fulfilled_test},
                    ':a': {"N": str(count_attemps)},
                    ':rt': {"N": '0'},
                    ':rm': {"S": str(response_m)}
            })
            print("UpdateItem succeeded:")
            return response
        else:
            dt = datetime.datetime.strptime(response_m['result'][0]['createdAt'], "%Y-%m-%dT%H:%M:%SZ")
            request_time = time.mktime(dt.timetuple()) + (dt.microsecond / 1000000.0)
            request_time = int(request_time)
            response = dynamo_client.update_item(
                TableName=os.environ['trial_request_table'],
                Key={
                    'LeadId': {"N": str(lead_id)},
                    'Date': {"S": curr_date}
                },
                UpdateExpression= "set #Fulfilled = :f, #Attemps = :a, #RequestTime = :rt, #RequestMsg = :rm",
                ExpressionAttributeNames={
                    '#Fulfilled': "Fulfilled",
                    '#Attemps': "Attemps",
                    '#RequestTime': "RequestTime",
                    '#RequestMsg': "RequestMsg"
                },
                ExpressionAttributeValues={
                    ':f': {"S": fulfilled_test},
                    ':a': {"N": str(count_attemps)},
                    ':rt': {"N": str(request_time)},
                    ':rm': {"S": str(response_m)}
            })
            print("UpdateItem succeeded:")
            return response
    except IOError:
        print("an error has been found. Data not inserted into the table")


# function to send the response from marketo to the SQS
def send_to_SQS(response):
    try:
        resp = sqs_client.send_message(QueueUrl=os.environ['sqs_url'],MessageBody=json.dumps(response))
        return resp
    except IOError:
        print("an error has been found. Message not been sent to the queue")
