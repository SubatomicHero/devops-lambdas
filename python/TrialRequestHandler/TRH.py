from __future__ import print_function
from marketo import Marketo

import json
import os
import boto3
import datetime
import time


os.environ['api_host'] = "https://453-LIZ-762.mktorest.com"
os.environ['client_id'] = "35a7e1a3-5e60-40b2-bd54-674680af2adc"
os.environ['client_secret'] = "iPPgKiB224jsa02duwPcKy9ox7078P7S"
os.environ['trial_request_table'] = "OnlineTrialRequestDynamoDbTable"


#TO BE USED ONLY ON THE FINAL VERSION
#DYNAMO_DB = boto3.resource('dynamodb', region_name='us-west-2')
#dyn_table = DYNAMO_DB.Table(os.environ['trial_request_table'])
#sqs = boto3.resource('sqs')
#queue = sqs.get_queue_by_name(QueueName=os.environ['sqs_url'])


print('Getting message from SNS')

#main lambda function
def lambda_handler(event, context):

    message = event['Records'][0]['Sns']['Message']
    get_source = message['source']
    lead_id = message['lead']
    print("From SNS: " + get_source)
    if (get_source == 'onlinetrials'):
        response = ""
        count_attemps = 0
        while response == "":
            #TO BE USED ONLY ON THE FINAL VERSION
            #response = details_marketo(lead_id)
            count_attemps = count_attemps + 1
            if count_attemps == 15:
                break
        if(response != ""):
            fulfilled_test = 'y'
            send_to_SQS(response)
            #TO BE USED ONLY ON THE FINAL VERSION
            #insert_into_dynamo(dyn_table,lead_id,response,fulfilled_test,count_attemps)
            return "OP1"
        else:
            fulfilled_test = 'n'
            #TO BE USED ONLY ON THE FINAL VERSION
            #insert_into_dynamo(dyn_table,lead_id,response,fulfilled_test,count_attemps)
            return "OP2"

#function to obtain the details regarding the lead_id passed as a parameter
def details_marketo(lead_id):
        api_host = os.environ['api_host']
        client_id = os.environ['client_id']
        client_secret = os.environ['client_secret']
        m = Marketo(host = api_host, client_id = client_id, client_secret = client_secret)
        response_m = m.get_leads('email', lead_id)
        return response_m

#function to insert the request in the dynamodB table for the Trial Request Handler
def insert_into_dynamo(table, lead_id, response_m, fulfilled_test, count_attemps):

    curr_date = time.strftime("%d/%m/%Y")
    if response_m == "":
        response = table.put_item(
        Item={
            'LeadId': lead_id,
            'Date': curr_date,
            'Fulfilled': fulfilled_test,
            'Attempts' : count_attemps,
            'RequestTime' : response_m,
            'Request' : response_m
            })
        print("PutItem succeeded:")
        return response
    else:
        dt = datetime.datetime.strptime(response_m['result'][0]['createdAt'], "%Y-%m-%dT%H:%M:%SZ")
        request_time = time.mktime(dt.timetuple()) + (dt.microsecond / 1000000.0)
        request_time = int(request_time)
        response = table.put_item(
        Item={
            'LeadId': lead_id,
            'Date': curr_date,
            'Fulfilled': fulfilled_test,
            'Attempts' : count_attemps,
            'RequestTime' : request_time,
            'Request' : response_m
            })
        print("PutItem succeeded:")
        return response

#function to send the response from marketo to the SQS
def send_to_SQS(queue,response):
    resp = queue.send_message(MessageBody=json.dumps(response))
    return resp
