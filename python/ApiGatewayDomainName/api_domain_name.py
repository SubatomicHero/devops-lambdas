import logging
from os import environ
import cfnresponse
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

client = boto3.client('apigateway')

def handler(event, context):
  logicalId = event['LogicalResourceId']
  try:
    if event['RequestType'] == 'Create':
      response = client.create_domain_name(
        domainName=environ['domain_name'],
        certificateArn=environ['certificate_arn']
      )
      responseData = {'DistributionName': response['distributionDomainName']}
      cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData, logicalId)
    elif event['RequestType'] == 'Delete':
      client.delete_domain_name(domainName=environ['domain_name'])
      cfnresponse.send(event, context, cfnresponse.SUCCESS, {}, logicalId)
  except Exception as err:
    logger.error(str(err))
    cfnresponse.send(event, context, cfnresponse.FAILED, {}, logicalId)
