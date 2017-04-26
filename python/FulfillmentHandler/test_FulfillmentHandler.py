import boto, boto3, botocore.exceptions, requests, sure , time, json, unittest, time, random
from moto import  mock_sqs, mock_ec2, mock_cloudformation, mock_dynamodb2, mock_sns
from nose.tools import assert_raises
from FulfillmentHandlerLambda import FulfillmentHandler

FH = FulfillmentHandler()

class TestFulfillmentHandlerLambda(unittest.TestCase):
    def test_instance(self):
        self.assertIsNotNone(FH.sns_client)
        self.assertIsNotNone(FH.dynamo_res)

    @mock_dynamodb2
    def createTestTable(self, name):
        try:
            table = FH.dynamo_res.create_table(
                TableName = name,
                KeySchema = [
                    {
                        'AttributeName': 'LeadId',
                        'KeyType': 'HASH'  
                    },
                    {
                        'AttributeName': 'Date',
                        'KeyType': 'RANGE'  
                    }
                ],
                AttributeDefinitions = [
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
                ],
                ProvisionedThroughput = {
                    'ReadCapacityUnits': 10,
                    'WriteCapacityUnits': 10
                }
            )
            return table
        except Exception:
            print("test failed. no dynamoDB table created")

    def putItem(self, table, name, id, f):
        try:
            table.put_item(
                Item = {
                    'LeadId': id,
                    'Fulfilled' : f,
                    'Date' : str(table.creation_date_time)
                }
            )
        except Exception:
            print("test failed. no instance table updated")
    
    @mock_sns
    def createSNSTopic(self):
        try:
            sns_client = boto3.client('sns', region_name='us-east-1')
            topic = sns_client.create_topic(
                Name = 'topic'
            )
            if topic is None:
                raise ValueError('No sns topic could be created')
            return topic['TopicArn']
        except Exception:
            print("test failed. no sns topic could be created")

    @mock_dynamodb2
    def test_readFromTable_multipleReq(self):
        name = 'trial_request_table'
        table = self.createTestTable(name)
        id1 = str(random.randint(0, 100))
        self.putItem(table, name, id1, 'n')
        id2 = str(random.randint(0, 100))
        self.putItem(table, name, id2, 'y')
        id3 = str(random.randint(0, 100))
        self.putItem(table, name, id3, 'n')
        items = FH.readFromTable(name)
        assert len(items) == 2
        print ('Test dynamoDB read leadId from table (multiple unfulfilled request table): Passed\n')

    @mock_dynamodb2
    def test_readFromTable_noReq(self):
        name = 'trial_request_table'
        table = self.createTestTable(name)
        id1 = str(random.randint(0, 100))
        self.putItem(table, name, id1, 'y')
        items = FH.readFromTable(name)
        assert len(items) == 0
        print ('Test dynamoDB read leadId from table (no unfulfilled request table): Passed\n')

    @mock_dynamodb2
    def test_readFromTable_noTable(self):
        name = None
        items = FH.readFromTable(name)
        assert items == None
        print ('Test dynamoDB read leadId from table (no dynamoDB table): Passed\n')

    def test_createObject(self):
        id1 = str(random.randint(0, 100))
        obj = FH.createMessageObject(id1)
        assert obj['lead'] == id1
        assert obj['source'] == 'onlinetrial'
        print ('Test create sns object: Passed\n')

    @mock_sns
    def test_publishTopicSNS(self):
        topicArn = self.createSNSTopic()
        id1 = str(random.randint(0, 100))
        obj = FH.createMessageObject(id1)
        response = FH.publishTopicSNS(topicArn, obj)
        assert response['ResponseMetadata']['HTTPStatusCode'] ==  200
        assert response['ResponseMetadata']['RetryAttempts'] ==  0
        print ('Test publish sns topic : Passed\n')

    @mock_sns
    @mock_dynamodb2
    def test_run_success(self):
        name = 'trial_request_table'
        table = self.createTestTable(name)
        id1 = str(random.randint(0, 100))
        self.putItem(table, name, id1, 'n')
        id2 = str(random.randint(0, 100))
        self.putItem(table, name, id2, 'y')
        id3 = str(random.randint(0, 100))
        self.putItem(table, name, id3, 'n')
        topicArn = self.createSNSTopic()
        testInstance = FulfillmentHandler(name, topicArn)
        code = testInstance.run()
        assert code == 200 
        print ('Test run function returns 200: passed\n')

    @mock_sns
    @mock_dynamodb2
    def test_run_noReq(self):
        name = 'trial_request_table'
        table = self.createTestTable(name)
        id1 = str(random.randint(0, 100))
        self.putItem(table, name, id1, 'y')
        topicArn = self.createSNSTopic()
        testInstance = FulfillmentHandler(name, topicArn)
        code = testInstance.run()
        assert code == 200
        print ('Test run function with no unfulfilled request: passed\n')

    @mock_sns
    @mock_dynamodb2
    def test_run_noTopic(self):
        name = 'trial_request_table'
        table = self.createTestTable(name)
        id1 = str(random.randint(0, 100))
        self.putItem(table, name, id1, 'n')
        topicArn = None
        testInstance = FulfillmentHandler(name, topicArn)
        code = testInstance.run()
        assert code == None
        print ('Test run function with no topic: passed\n')
    
if __name__ == '__main__':
    unittest.main()