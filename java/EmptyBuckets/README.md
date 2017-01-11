EmptyBuckets Java Lambda for PAAS-ECM
---

This Lambda is triggered by the CloudFormation Template when DataStack is deleted, in order to delete the bucket containing the Alfresco content data (alf-data).

When the request type sent by the CFN template is different from "Delete" or when the bucket does not exist the Lambda function will exit sending a SUCCESS message to CFN template.
In case of AWS exception it will instead send a FAILURE message back to the template.
In all other cases it will first delete all the contents in the bucket (deleting the versions to make it more generic in case of version enabled buckets) and then the bucket itself.