EmptyBuckets Java Lambda
---

This Lambda is triggered by a CloudFormation Template when the stack is deleted, in order to delete the bucket containing any data.

When the request type sent by the CFN template is different from "Delete" or when the bucket does not exist the Lambda function will exit sending a SUCCESS message to CFN template.
In case of AWS exception it will instead send a FAILURE message back to the template.
In all other cases it will first delete all the contents in the bucket (deleting the versions to make it more generic in case of version enabled buckets) and then the bucket itself.

This Lambda has been created using the [AWS Toolkit for Eclipse](http://docs.aws.amazon.com/toolkit-for-eclipse/v1/user-guide/lambda.html)

**TODO**: use [Maven](http://docs.aws.amazon.com/lambda/latest/dg/java-create-jar-pkg-maven-and-eclipse.html)

