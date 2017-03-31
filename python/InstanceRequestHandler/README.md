# AWS Lambdas -  Instance Request Handler
---
#####  Lambda function for the Instance Request Handler

The file InstanceRequestHandlerLambda.py contains the code of the lambda function.
We can either create a deployment package or upload the code to AWS Lambda console.
As the code requires the AWS SDK library, the code can be tested in the inline editor in the AWS Lambda console. 
Using the console, the code can be uploaded  to AWS Lambda. The console will zip up the code with the given configuration information  into a deployment package. Then the AWS Lambda service can run the deployment zip.

#####  Tests for the Lambda function 

The test file, test_InstanceReqHandler.py contains the test code for the lambda function.
To execute the tests, pass the command on terminal:

      "python test_InstanceReqHandler.py"