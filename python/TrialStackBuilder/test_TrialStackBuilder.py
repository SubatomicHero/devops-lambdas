import boto
import boto3
import botocore.exceptions
from boto.exception import SQSError
from boto.sqs.message import RawMessage, Message

import requests
import sure  # noqa
import time
import json 
from moto import  mock_sqs, mock_ec2, mock_cloudformation, mock_lambda
from nose.tools import assert_raises
from TrialStackBuilderLambda import TrialStackBuilder



TSB = TrialStackBuilder()


@mock_lambda
def test_lambda_handler():
    

test_lambda_handler()