"""
Test case for Ami Updater
"""

import json
import unittest
import boto3
import boto
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
        print('Test instance : passed ')

    @mock_ec2
    def add_servers(self, ami_id="ami-12345abc"):
        """
        Adds ec2 instances
        """
        conn = boto.connect_ec2('the_key', 'the_secret')
        return conn.run_instances(ami_id).instances[0]

    
    @mock_ec2
    def build_ami(self, id):
        """
        Builds the ami with the instance id provided
        """
        instance = self.add_servers()
        instance.add_tag('Product', 'APS')
        id = instance.id
        response = AmiUp.ec2_client.create_image(
            InstanceId = id,
            Name = 'ami-test'
        )
        imageId = response['ImageId']
        ec2 = boto3.resource('ec2')
        image = ec2.Image(imageId)
        image.create_tags(
            Tags=[
                {
                    'Key': 'Product',
                    'Value': 'APS'
                },
                {
                    'Key': 'Version',
                    'Value': 'LATEST'
                },
            ]
        )
        return imageId
        
    @mock_ec2
    def test_findAmi(self):
        """
        Tests finding the ami with the tag
        """
        instance = self.add_servers()
        imageId = self.build_ami(instance.id)
        response =  AmiUp.find_AMI('APS')
        assert response['Images'][0]['ImageId'] == imageId
        print('Test finding the ami with tag product : passed ')

    @mock_ec2
    def test_amiUpdate(self):
        """
        Tests updating of amis in the list
        """
        instance = self.add_servers()
        imageId = self.build_ami(instance.id)
        list =  AmiUp.find_AMI('APS')
        result = AmiUp.amiUpdate(list)
        assert result == 200
        print('Test updating of amis : passed ')
 
    @mock_ec2
    def test_amiUpdate_alreadyupdated(self):
        """
        Tests checking of amis already updated in the list
        """
        instance = self.add_servers()
        imageId = self.build_ami(instance.id)
        ec2 = boto3.resource('ec2')
        image = ec2.Image(imageId)
        image.create_tags(
            Tags=[
                {
                    'Key': 'Version',
                    'Value': ''
                },
            ]
        )
        list =  AmiUp.find_AMI('APS')
        result = AmiUp.amiUpdate(list)
        assert result == 200
        print('Test checking of amis already updated : passed ')

    @mock_ec2
    def test_removeTag(self):
        """
        Tests removing tags
        """
        instance = self.add_servers()
        imageId = self.build_ami(instance.id)
        result = AmiUp.remove_tag(imageId)
        assert result['ResponseMetadata']['HTTPStatusCode'] == 200
        print('Test removing tags : passed ')

    @mock_ec2
    def test_removeTag_fail(self):
        """
        Tests failing of the removing tags
        """
        result = AmiUp.remove_tag('')
        assert result == None
        print('Test failed removing tags : passed ')

    @mock_ec2
    def test_run(self):
        """
        Tests run function
        """
        event = {"Product":"APS"}
        result = AmiUp.run(event)
        assert result == 200
        print('Test run function : passed ')

    @mock_ec2
    def test_run_fail_NoEvent(self):
        """
        Tests failure of run functiob
        """
        event = {}
        result = AmiUp.run(event)
        assert result == None
        print('Test  failed run function : passed ')

if __name__ == '__main__':
    unittest.main()