from datetime import datetime

import json
import os
import boto3
import time
import requests



os.environ['sqs_url'] = ""
os.environ['trial_request_table'] = ""
os.environ['api_host'] = "https://453-liz-762.mktorest.com/"
os.environ['client_id'] = "35a7e1a3-5e60-40b2-bd54-674680af2adc"
os.environ['client_secret'] = "iPPgKiB224jsa02duwPcKy9ox7078P7S"

class TrialRequestHandler:
    def __init__(self, url = os.environ['sqs_url'], host = os.environ['api_host'], id = os.environ['client_id'], secret = os.environ['client_secret']):
        self.dynamo_client = boto3.client('dynamodb')
        self.sqs_client = boto3.client('sqs')
        self.sqsUrl = url
        self.host1 = "{}/identity/oauth/token".format(host)
        self.host2 = "{}/rest/v1/leads.json".format(os.environ['api_host'])
        self.client_id = id
        self.client_pass = secret

    def _get_access_token(self, host, id, secret):
        """Authenticates with Marketo, returning the token to use for future requests"""
        try:
            if host and id and secret :
                p = {
                    'grant_type':'client_credentials',
                    'client_id': id,
                    'client_secret': secret
                }
                r = requests.get(host, params=p)
                data = json.loads(r.content.decode('utf-8'))
                print("Access token acquired")
                return data['access_token']
            else:
                raise ValueError('Needed valid host, id and secret')
        except requests.HTTPError as err:
            print("_authenticate(): {}".format(err))

    def details_marketo(self, host, lead_id, access_token):
        """function to obtain the details regarding the lead_id passed as a parameter"""
        try:
            if lead_id and access_token :
                print("details_marketo(): Getting lead info for {}".format(lead_id))
                p = {
                    'access_token': access_token,
                    'filterType': 'id',
                    'filterValues': lead_id
                }
                r = requests.get(host, params=p)
                data = json.loads(r.content.decode('utf-8'))
                print(data)
                return data
            else:
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
                request_time = '0'
                dt = datetime.strptime(response_m['result'][0]['createdAt'], "%Y-%m-%dT%H:%M:%SZ")
                request_time = int(time.mktime(dt.timetuple()) + (dt.microsecond / 1000000.0))
                
                response = self.dynamo_client.update_item(
                    TableName=os.environ['trial_request_table'],
                    Key={
                        'LeadId': {"N": str(lead_id)},
                        'Date': {"S": curr_date}
                    },
                    UpdateExpression="set #Fulfilled=:f, #Attempts=:a, #RequestTime=:rt, #RequestMsg=:rm",
                    ExpressionAttributeNames={
                        '#Fulfilled': "Fulfilled",
                        '#Attempts': "Attempts",
                        '#RequestTime': "RequestTime",
                        '#RequestMsg': "RequestMsg"
                    },
                    ExpressionAttributeValues={
                        ':f': {"S": fulfilled_test},
                        ':a': {"N": str(count_attempts)},
                        ':rt': {"S": str(request_time)},
                        ':rm': {"S": json.dumps(response_m)}
                })
                print("Update item succeeded")
                return True 
            else:
                raise ValueError('Valid lead_id, response_m, fulfilled_test and count_attempts are needed')
        except:
            raise IOError('an error has been found. Data not inserted into the table')
        else:
            return None

    def send_to_SQS(self, sqsUrl, response):
        """function to send the response from marketo to the SQS"""
        try:
            if response:
                response = self.sqs_client.send_message(QueueUrl = sqsUrl, MessageBody = json.dumps(response))
                return response
            else:
                raise ValueError('Valid message is needed')
        except IOError as ioerr:
            raise IOError("an error has been found. Message not been sent to the queue: {}".format(ioerr))
        except Exception as err:
            print("{}\n".format(err))
        else:
            return None

    def run(self):
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
                        access_token = self._get_access_token(self.host1, self.client_id, self.client_pass)
                        response = self.details_marketo(self.host2, lead_id, access_token)
                        count_attempts = 1
                        while response is None and count_attempts <= 10:
                            try:
                                print("Trying again after 10 seconds")
                                count_attempts += 1
                                time.sleep(10)
                                access_token = self._get_access_token(self.host1, self.client_id, self.client_pass)
                                response = self.details_marketo(self.host2, lead_id, access_token)
                            except IOError as ioerr:
                                print("Marketo error: {}".format(ioerr))
                        if response:
                            print("Details received from marketo: {}".format(response))
                        fulfilled_test = 'y' if response is not None else 'n'
                        try:
                            if self.insert_into_dynamo(lead_id, response, fulfilled_test, count_attempts) is True:
                                print("Record inserted to DB")
                                if self.send_to_SQS(self.sqsUrl, response) is not None:
                                    print("Message sent to queue")
                            else:
                                print("Not sending message to queue, unable to get response from Marketo")
                        except IOError as ioerr:
                            print("no response from dynamodb (unfulfilled)")
        except EOFError:
            print("lambda handler failed")
        else: 
            return None

TRH = TrialRequestHandler()

# main lambda function
def lambda_handler(event, context):
    try:
        res = TRH.run()
        if res == 'FAILURE':
            print ('The run function has failed')
            raise ValueError
        print("All OK")
        return 200
    except Exception as err:
        print("{}\n".format(err))
    else:
        return ('FAILURE')

