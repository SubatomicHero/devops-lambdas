# AWS Lambdas -  Trial Request Handler
---

##### TRH.PY is the implementation of the lambda for the Trial Request Handler

To execute this file just need to do :

      "python TRH.py" on terminal

For now, it's not the final version because some variables are still not be using (just for the AWS Lambda)

##### mock_file.py is the test file where the services from AWS (SQS, SNS, dynamodb) are in form of a mock-up to be tested out with the code of the lambda

To execute all the tests on mock_file, you just have to do:

        python mock_file.py on terminal

To execute only the insertion of data in dynamo test, you just have to do:

        echo "test_insert_dynamo()" | python -i mock_file.py on terminal

To execute only the sending of the marketo result to the SQS service test, you just have to do:

         echo "test_send_to_SQS()" | python -i mock_file.py on terminal

To execute only the sending of the message to marketo to get the details test, you just have to do:

         echo "test_details_marketo()" | python -i mock_file.py on terminal
         This test is not final since got an error regarding the SSLv3 handshake (need to sort this out with Daniel Taylor)
