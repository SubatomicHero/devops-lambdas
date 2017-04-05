import boto3
from moto import mock_sqs
from moto import mock_dynamodb2
import datetime
import time
import json


def test_lambda_handler():
    event = {
      "Records": [
        {
          "EventVersion": "1.0",
          "EventSubscriptionArn": "arn:aws:sns:EXAMPLE",
          "EventSource": "aws:sns",
          "Sns": {
            "SignatureVersion": "1",
            "Timestamp": "1970-01-01T00:00:00.000Z",
            "Signature": "EXAMPLE",
            "SigningCertUrl": "EXAMPLE",
            "MessageId": "95df01b4-ee98-5cb9-9903-4c221d41eb5e",
            "Message": { "source": "onlinetrials", "lead": "nnnnnnn" },
            "MessageAttributes": {
              "Test": {
                "Type": "String",
                "Value": "TestString"
              },
              "TestBinary": {
                "Type": "Binary",
                "Value": "TestBinary"
              }
            },
            "Type": "Notification",
            "UnsubscribeUrl": "EXAMPLE",
            "TopicArn": "arn:aws:sns:EXAMPLE",
            "Subject": "TestInvoke"
          }
        }
      ]
    }
    try:
        message = event['Records'][0]['Sns']['Message']
        get_source = message['source']
        lead_id = message['lead']
        print("From SNS: " + get_source)
        if (get_source == 'onlinetrials'):
            response = {'result': [{'updatedAt': '2015-08-10T06:53:11Z', 'lastName': 'Taylor', 'firstName': 'Dan', 'createdAt': '2014-09-18T20:56:57Z', 'email': 'daniel.taylor@alfresco.com', 'id': 1558511}], 'success': True, 'requestId': 'e809#14f22884e5f'}
            count_attemps = 0
            while response == "":
                try:
                    count_attemps = count_attemps + 1
                    if count_attemps == 15:
                        break
                except IOError:
                    print("no response from marketo")
            if(response != ""):
                try:
                    fulfilled_test = 'y'
                    test_insert_into_dynamo()
                    sqs_result = test_send_to_SQS()
                    result = "Inserted fulfilled in dynamodb"
                except IOError:
                    print("no response from dynamodb")
            else:
                try:
                    fulfilled_test = 'n'
                    test_insert_into_dynamo()
                    result = "Inserted unfulfilled in dynamodb"
                except IOError:
                    print("no response from dynamodb")
            assert result == "Inserted fulfilled in dynamodb"
            print result
    except EOFError:
        print("lambda handler failed for some error")


def test_details_marketo():
    try:
        email_test = 'daniel.taylor@alfresco.com'
        result = details_marketo(email_test)
        expected_result = {'result': [{'updatedAt': '2015-08-10T06:53:11Z', 'lastName': 'Taylor', 'firstName': 'Dan', 'createdAt': '2014-09-18T20:56:57Z', 'email': 'daniel.taylor@alfresco.com', 'id': 1558511}], 'success': True, 'requestId': 'e809#14f22884e5f'}
        assert result == expected_result
        print("test passed")
    except IOError:
        print("test failed. an error has been found")

@mock_dynamodb2
def test_insert_into_dynamo():
    dynamodb = boto3.client('dynamodb', region_name='us-west-2')

    table_t = dynamodb.create_table(
    TableName='trial_request_table',
    KeySchema=[
        {
            'AttributeName': 'LeadId',
            'KeyType': 'HASH'  # Partition key
        },
        {
            'AttributeName': 'Date',
            'KeyType': 'RANGE'  # Sort key
        }
    ],
    AttributeDefinitions=[
        {
            'AttributeName': 'LeadId',
            'AttributeType': 'N'
        },
        {
            'AttributeName': 'Date',
            'AttributeType': 'S'
        },
        {
            'AttributeName': 'Fulfilled',
            'AttributeType': 'S'
        },
        {
            'AttributeName': 'Attempts',
            'AttributeType': 'N'
        },
        {
            'AttributeName': 'RequestTime',
            'AttributeType': 'N'
        },
        {
            'AttributeName': 'Request',
            'AttributeType': 'S'
        },
    ],
    ProvisionedThroughput={
        'ReadCapacityUnits': 10,
        'WriteCapacityUnits': 10
    })

    try:
        curr_date = time.strftime("%d/%m/%Y")
        lead_id = "daniel.taylor@alfresco.com"
        response_m = {'result': [{'updatedAt': '2015-08-10T06:53:11Z', 'lastName': 'Taylor', 'firstName': 'Dan', 'createdAt': '2014-09-18T20:56:57Z', 'email': 'daniel.taylor@alfresco.com', 'id': 1558511}], 'success': True, 'requestId': 'e809#14f22884e5f'}
        fulfilled_test = 'y'
        count_attemps = 10
        if response_m == "":
            response = dynamodb.update_item(
                TableName='trial_request_table',
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
            response = dynamodb.update_item(
                TableName='trial_request_table',
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

        assert result['ResponseMetadata']['HTTPStatusCode'] == 200
        print("test passed")
    except IOError:
        print("test failed. an error has been found")


@mock_sqs
def test_send_to_SQS():
    try:
        response_m = {'result': [{'updatedAt': '2015-08-10T06:53:11Z', 'lastName': 'Taylor', 'firstName': 'Dan', 'createdAt': '2014-09-18T20:56:57Z', 'email': 'daniel.taylor@alfresco.com', 'id': 1558511}], 'success': True, 'requestId': 'e809#14f22884e5f'}
        sqs = boto3.client('sqs', region_name='us-west-2')
        queue = sqs.create_queue(QueueName='OnlineTrialRequestSQS', Attributes={'DelaySeconds': '5'})
        queue_url_message = sqs.get_queue_url(QueueName='OnlineTrialRequestSQS')
        queue_url = queue_url_message['QueueUrl']
        resp = sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(response_m))
        assert resp['ResponseMetadata']['HTTPStatusCode'] == 200
        print(resp)
        print(resp.get('MessageId'))
        print(resp.get('MD5OfMessageBody'))
        print("test passed")
    except IOError:
        print("test failed. an error has been found")


# test_details_marketo()
test_insert_into_dynamo()
test_send_to_SQS()
test_lambda_handler()
