from datetime import datetime

import json
import os
import boto3
import time
import requests

class TrialRequestHandler:
    def __init__(self, url=os.getenv('sqs_url'), host=os.getenv('api_host'), id=os.getenv('client_id'), secret=os.getenv('client_secret')):
        self.dynamo_client = boto3.client('dynamodb')
        self.sqs_client = boto3.client('sqs')
        self.sqsUrl = url
        self.host = host
        self.client_id = id
        self.client_pass = secret

    def _get_access_token(self, host, id, secret):
        """Authenticates with Marketo, returning the token to use for future requests"""
        try:
            if host and id and secret:
                host = "{}/identity/oauth/token".format(host)
                p = {
                    'grant_type':'client_credentials',
                    'client_id': id,
                    'client_secret': secret
                }
                r = requests.get(host, params = p)
                data = json.loads(r.content.decode('utf-8'))
                print("Access token acquired")
                return data['access_token']
            raise ValueError('Needed valid host, id and secret')
        except requests.HTTPError as err:
            print("_authenticate(): {}".format(err))
        else:
            return None

    def details_marketo(self, host, lead_id, access_token):
        """function to obtain the details regarding the lead_id passed as a parameter"""
        try:
            if lead_id and access_token:
                host = "{}/rest/v1/leads.json".format(host)
                print("details_marketo(): Getting lead info for {}".format(lead_id))
                p = {
                    'access_token': access_token,
                    'filterType': 'id',
                    'filterValues': lead_id
                }
                r = requests.get(host, params=p)
                if r is None:
                    print("Cannot get the lead details for {}".format(lead_id))
                    return None
                print("Returning lead info")
                return json.loads(r.content.decode('utf-8'))
            raise ValueError('No valid lead_id')
        except requests.HTTPError as err:
            print("details_marketo(): {}".format(err))
        else:
            return None

    def insert_into_dynamo(self, lead_id, response_m, fulfilled_test, count_attempts):
        """function to insert the request in the dynamodB table for the Trial Request Handler"""
        try:
            if lead_id and response_m and fulfilled_test and count_attempts:
                curr_date = time.strftime("%d/%m/%Y")
                request_time = lambda: int(round(time.time() * 1000))
                response = self.dynamo_client.update_item(
                    TableName = os.environ['trial_request_table'],
                    Key = {
                        'LeadId': {"N": str(lead_id)},
                        'Date': {"S": curr_date}
                    },
                    UpdateExpression = "set #Fulfilled=:f, #Attempts=:a, #RequestTime=:rt, #RequestMsg=:rm",
                    ExpressionAttributeNames = {
                        '#Fulfilled': "Fulfilled",
                        '#Attempts': "Attempts",
                        '#RequestTime': "RequestTime",
                        '#RequestMsg': "RequestMsg"
                    },
                    ExpressionAttributeValues = {
                        ':f': {"S": fulfilled_test},
                        ':a': {"N": str(count_attempts)},
                        ':rt': {"S": str(request_time)},
                        ':rm': {"S": json.dumps(response_m)}
                })
                print("Update item succeeded")
                return True 
            raise ValueError('Valid lead_id, response_m, fulfilled_test and count_attempts are needed')
        except IOError:
            raise IOError('an error has been found. Data not inserted into the table')
        except ValueError as verr:
            print("{}".format(verr))
        else:
            return None

    def send_to_SQS(self, sqsUrl, response):
        """function to send the response from marketo to the SQS"""
        try:
            return self.sqs_client.send_message(
                QueueUrl=sqsUrl,
                MessageBody=json.dumps(response)
            )
        except IOError as ioerr:
            raise IOError("an error has been found. Message not been sent to the queue: {}".format(ioerr))
        else:
            return None

    def run(self, event):
        try:
            if 'Records' in event:
                print('Getting message from SNS')
                for record in event['Records']:
                    message = json.loads(record['Sns']['Message'])
                    get_source = message['source']
                    lead_id = message['lead']
                    print("From SNS: {}".format(message))
                    if get_source == "onlinetrial":
                        print("Processing online trial request")

                        # Get the access token to make a request
                        access_token = self._get_access_token(self.host, self.client_id, self.client_pass)
                        if access_token is None:
                            raise ValueError('Cannot get the access token')

                        # Get the lead details from Marketo
                        count_attempts = 1
                        response = self.details_marketo(self.host, lead_id, access_token)
                        while response is None and count_attempts <= 10:
                            print("Trying again after 10 seconds")
                            count_attempts += 1
                            time.sleep(10)
                            response = self.details_marketo(self.host, lead_id, access_token)
                        if response:
                            print("Details received from marketo: {}".format(response))

                        fulfilled_test = 'y'
                        if 'errors' in response and len(response['errors'] > 0):
                            print("Error getting lead details: {}".format(response['errors']))
                            fulfilled_test = 'n'

                        if self.insert_into_dynamo(lead_id, response, fulfilled_test, count_attempts) is True:
                            print("Record inserted to DB")
                            send = self.send_to_SQS(self.sqsUrl, response)
                            if send is None:
                                raise ValueError('Message send unsuccessful')
                            print("Message sent to queue")
                        else:
                            raise ValueError("Not sending message to queue, unable to get response from Marketo")
                return 200
        except ValueError as err:
            print("{}\n".format(err))
        else:
            return None

TRH = TrialRequestHandler()

# main lambda function
def lambda_handler(event, context):
    try:
        res = TRH.run(event)
        if res is None:
            raise ValueError('The run function has failed')
        print("All OK")
        return 200
    except Exception as err:
        print("{}\n".format(err))
    else:
        return('FAILURE')
