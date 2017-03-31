from __future__ import print_function
import os
import cfnresponse
import boto3
import json

def handler(event, context):
  logicalId = event['LogicalResourceId']
  try:
    client = boto3.client('apigateway')
    if event['RequestType'] == 'Create':
      response = client.create_domain_name(
        domainName=os.environ['domain_name'],
        certificateArn=os.environ['certificate_arn']
      )
      responseData = {'DistributionName': response['distributionDomainName']}
      cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData, logicalId)
    elif event['RequestType'] == 'Delete':
      client.delete_domain_name(
        domainName=os.environ['domain_name']
      )
      cfnresponse.send(event, context, cfnresponse.SUCCESS, {}, logicalId)
  except Exception as err:
    message = "{0}\n".format(err)
    print(message)
    cfnresponse.send(event, context, cfnresponse.FAILED, {}, logicalId)
