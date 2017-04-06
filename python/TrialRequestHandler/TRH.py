from marketo import Marketo
from datetime import datetime

import json
import os
import boto3
import time

print('Getting message from SNS')

# main lambda function
def lambda_handler(event, context):
    try:
        dynamo_client = boto3.client('dynamodb')
        sqs_client = boto3.client('sqs')
        sns_client = boto3.client('sns')

        handler = TrialRequestHandler()
        message = event['Records'][0]['Sns']['Message']
        get_source = message['source']
        lead_id = message['lead']
        print("From SNS: {}".format(message))
        if get_source == 'onlinetrials':
            response = None
            count_attempts = 0
            while not response:
                try:
                    response = handler.details_marketo(lead_id,os.environ['api_host'], os.environ['client_id'], os.environ['client_secret'])
                    count_attempts = count_attempts + 1
                    if count_attempts == 15:
                        break
                except IOError:
                    print("no response from marketo")
            if response:
                try:
                    fulfilled_test = 'y'
                    ins_db = handler.insert_into_dynamo(dynamo_client, os.environ['trial_request_table'],lead_id, response, fulfilled_test, count_attempts)
                    if ins_db:
                        ins_sqs = handler.send_to_SQS(sqs_client, os.environ['sqs_url'], response)
                        if ins_sqs:
                            return "Inserted fulfilled in dynamodb and SQS"
                        return "failed to insert in SQS"
                    return "failed to insert into dynamodb"
                except IOError:
                    print("no response from dynamodb")
            else:
                try:
                    fulfilled_test = 'n'
                    ins_db = handler.insert_into_dynamo(dynamo_client, os.environ['trial_request_table'],lead_id, response, fulfilled_test, count_attempts)
                    if ins_db:
                        # notify IM solution
                        return "Inserted unfulfilled in dynamodb"
                    return "failed to insert into dynamodb"

                except IOError:
                    print("no response from dynamodb")
    except EOFError:
        print("lambda handler failed")


class TrialRequestHandler:

    # function to obtain the details regarding the lead_id passed as a parameter
    def details_marketo(self,lead_id, ah, ci, cs):
        try:
            api_host = ah
            client_id = ci
            client_secret = cs
            m = Marketo(host=api_host, client_id=client_id, client_secret=client_secret)
            response_m = m.get_leads('id', lead_id)
            if response_m:
                return response_m
            return None
        except IOError:
            print("an error has been found with the details")

    # function to insert the request in the dynamodB table for the Trial Request Handler
    def insert_into_dynamo(self,dyn_db, table_id,lead_id, response_m, fulfilled_test, count_attempts):
        try:
            curr_date = time.strftime("%d/%m/%Y")
            if not response_m:
                response = dyn_db.update_item(
                    TableName=table_id,
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
                        ':rt': {"N": '0'},
                        ':rm': {"S": str(response_m)}
                })
                if response:
                    print("UpdateItem succeeded:")
                    return response
                print("UpdateItem Failed:")
                return None
            else:
                dt = datetime.strptime(response_m['result'][0]['createdAt'], "%Y-%m-%dT%H:%M:%SZ")
                request_time = time.mktime(dt.timetuple()) + (dt.microsecond / 1000000.0)
                request_time = int(request_time)
                response = dyn_db.update_item(
                    TableName=table_id,
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
                        ':rt': {"N": str(request_time)},
                        ':rm': {"S": str(response_m)}
                })
                if response:
                    print("UpdateItem succeeded:")
                    return response
                print("UpdateItem Failed:")
                return None
        except IOError:
            print("an error has been found. Data not inserted into the table")

    # function to send the response from marketo to the SQS
    def send_to_SQS(self,sqs_serv,sqs_queue,response):
        try:
            resp = sqs_serv.send_message(QueueUrl=sqs_queue, MessageBody=json.dumps(response))
            if resp:
                return resp
            return None
        except IOError:
            print("an error has been found. Message not been sent to the queue")
