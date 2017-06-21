"""
Test case for Ami Updater
"""

import json
import unittest
import boto3
from moto import mock_ec2
from AmiUpdaterLambda import AMIUpdater

AmiUp = AMIUpdater()

class TestAmiUpdater(unittest.TestCase):
    """
    Tests for Ami Updater
    """
    def test_instance(self):
        """
        Test if the instance is created
        """
        self.assertIsNotNone(AmiUp.ec2_client)
    
    @mock_ec2
    def build_ami(self):
        client = boto3.client('ec2') 
        response = client.create_image(
            InstanceId='i-1234567890abcdef0',
            Name='ami-test'
        )
        print(response)
        
    @mock_ec2
    def test_findAmi(self):
        response = AmiUp.find_AMI("APS") 
        print(response)
        assert response != None
 
    
if __name__ == '__main__':
    unittest.main()