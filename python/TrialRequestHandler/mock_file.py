import boto3
from moto import mock_sns
from moto import mock_sqs
from moto import mock_dynamodb2
from TRH import insert_into_dynamo
from TRH import details_marketo
from TRH import lambda_handler
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

    message = event['Records'][0]['Sns']['Message']
    get_source = message['source']
    lead_id = message['lead']
    print("From SNS: " + get_source)
    if (get_source == 'onlinetrials'):
        response = {'result': [{'updatedAt': '2015-08-10T06:53:11Z', 'lastName': 'Taylor', 'firstName': 'Dan', 'createdAt': '2014-09-18T20:56:57Z', 'email': 'daniel.taylor@alfresco.com', 'id': 1558511}], 'success': True, 'requestId': 'e809#14f22884e5f'}
        count_attemps = 0
        while response == "":
            count_attemps = count_attemps + 1
            if count_attemps == 15:
                break
        if(response != ""):
            fulfilled_test = 'y'
            test_send_to_SQS()
            test_insert_into_dynamo()
            result = "OP1"
        else:
            fulfilled_test = 'n'
            test_insert_into_dynamo()
            result = "OP2"

        assert result == "OP1"
        print result


def test_details_marketo():
    email_test = 'daniel.taylor@alfresco.com'
    result = details_marketo(email_test)
    expected_result = {'result': [{'updatedAt': '2015-08-10T06:53:11Z', 'lastName': 'Taylor', 'firstName': 'Dan', 'createdAt': '2014-09-18T20:56:57Z', 'email': 'daniel.taylor@alfresco.com', 'id': 1558511}], 'success': True, 'requestId': 'e809#14f22884e5f'}
    assert result == expected_result
    print("test passed")

@mock_dynamodb2
def test_insert_into_dynamo():
    dynamodb = boto3.resource('dynamodb', region_name='us-west-2')

    table_t = dynamodb.create_table(
    TableName='trial_request_table',
    KeySchema=[
        {
            'AttributeName': 'LeadId',
            'KeyType': 'HASH'  #Partition key
        },
        {
            'AttributeName': 'Date',
            'KeyType': 'RANGE'  #Sort key
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



    lead_id = "daniel.taylor@alfresco.com"
    response_m = {'result': [{'updatedAt': '2015-08-10T06:53:11Z', 'lastName': 'Taylor', 'firstName': 'Dan', 'createdAt': '2014-09-18T20:56:57Z', 'email': 'daniel.taylor@alfresco.com', 'id': 1558511}], 'success': True, 'requestId': 'e809#14f22884e5f'}
    fulfilled_test = 'y'
    count_attemps = 10
    result = insert_into_dynamo(table_t,lead_id,response_m,fulfilled_test,count_attemps)

    assert result['ResponseMetadata']['HTTPStatusCode'] == 200
    print("test passed")


@mock_sqs
def test_send_to_SQS():
    response_m = {'result': [{'updatedAt': '2015-08-10T06:53:11Z', 'lastName': 'Taylor', 'firstName': 'Dan', 'createdAt': '2014-09-18T20:56:57Z', 'email': 'daniel.taylor@alfresco.com', 'id': 1558511}], 'success': True, 'requestId': 'e809#14f22884e5f'}
    sqs = boto3.resource('sqs', region_name='us-west-2')
    queue = sqs.create_queue(QueueName='OnlineTrialRequestSQS', Attributes={'DelaySeconds': '5'})
    resp = queue.send_message(MessageBody=json.dumps(response_m))
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 200
    print(resp)
    print(resp.get('MessageId'))
    print(resp.get('MD5OfMessageBody'))
    print("test passed")


#test_details_marketo()
test_insert_into_dynamo()
test_send_to_SQS()
test_lambda_handler()
