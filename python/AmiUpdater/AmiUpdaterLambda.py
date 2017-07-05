import boto3
import six

class AMIUpdater(object):
    def __init__(self):
        try:
            self.ec2_client = boto3.client('ec2')
        except Exception as err:
            print('{}\n'.format(err))
            raise err
            
    def find_AMI(self, productname, branchname):
        """
        Finds AMIs with the tag product equals to APS
        """
        try:
            if productname and isinstance(productname, six.string_types) and productname.strip() and branchname and isinstance(branchname, six.string_types) and branchname.strip():
                response = self.ec2_client.describe_images(
                    Filters = [
                        {
                            'Name': 'tag-key',
                            'Values': [
                                'Product'
                            ]
                        },
                        {
                            'Name': 'tag-value',
                            'Values': [
                                productname
                            ]
                        },
                        {
                            'Name': 'tag-key',
                            'Values': [
                                'Version'
                            ]
                        },
                        {
                            'Name': 'tag-value',
                            'Values': [
                                'LATEST'
                            ]
                        },
                        {
                            'Name': 'tag-key',
                            'Values': [
                                'Branch'
                            ]
                        },
                        {
                            'Name': 'tag-value',
                            'Values': [
                                branchname
                            ]
                        }
                    ]
                )
                if response is None:
                    raise ValueError('No AMI could be found')
                return response
            raise ValueError('The value of the tag value of the key Product is not valid')
        except Exception as err:
            print('{}\n'.format(err))
        else:
            return None
            
    def amiUpdate(self, amiList):
        """
        Update the list of amis
        """
        try:
            if amiList is None:
                raise ValueError('No valid Ami')
            for ami in amiList['Images']:
                print('The ami with id "{}" is being updated'.format(ami['ImageId']))
                response = self.remove_tag(ami['ImageId'])
                if response is None:
                    raise ValueError('Remove tag has failed')
            return 200
        except Exception as err:
            print('{}\n'.format(err))
        else:
            return None
            
            
    def remove_tag(self, ImageId):
        """
        Update the tag value of Version
        """
        try:
            if ImageId and isinstance(ImageId, six.string_types) and ImageId.strip():
                response = self.ec2_client.create_tags(
                    Resources = [ ImageId ],
                    Tags = [
                        {
                          'Key': 'Version',
                          'Value': ''
                        },    
                    ]
                )
                if response is None:
                    raise ValueError('Cannot remove tag')
                print('The tag of the ami with id "{}" is removed'.format(ImageId))
                return response
            raise ValueError('AMI not valid')
        except Exception as err:
            print('{}\n'.format(err))
            return None
        else:
            return None
            
    def removeLatestAmi(self, amiList, latestAmi):
        """
        Remove the latest ami from the list of ami to be updated
        """
        try:
            if amiList is None:
                raise ValueError('No valid Ami')
            if latestAmi is None:
                raise ValueError('No valid Ami id')
            for ami in amiList['Images']:
                if ami['ImageId'] == latestAmi:
                    amiList['Images'].remove(ami)
                    print('The ami with the id {} is the latest ami'.format(latestAmi))
                    break
            return amiList
        except Exception as err:
            print('{}\n'.format(err))
        else:
            return None
            
    def run(self, event):
        """
        Runs the AmiUpdater
        """
        try:
            if 'Product' in event and 'Branch' and 'LatestAMI' in event:
                amiList = self.find_AMI(event['Product'], event['Branch'])
                if amiList is None:
                    raise ValueError('Failed to find any ami')
                amiList = self.removeLatestAmi(amiList, event['LatestAMI'])
                if amiList is None:
                    raise ValueError('Failed to find the latest ami')
                response = self.amiUpdate(amiList)
                if response is None:
                    raise ValueError('Failed to update ami')
                print('Update of AMI was successfull')
                return 200
            raise ValueError('Cannot find events')
        except Exception as err:
            print('{}\n'.format(err))
        else:
            return None

AmiUp = AMIUpdater()

def lambda_handler(event, context):
    """"
    Lambda function 
    """ 
    try:
        result = AmiUp.run(event)
        if result is None:
            raise ValueError('The lambda function has failed')
        return ('Update of AMI was successfull')
    except Exception as err:
        print("{}\n".format(err))
        return ('Update of AMI was failed')
    else:
        return None