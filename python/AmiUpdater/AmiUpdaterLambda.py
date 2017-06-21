import boto3
import six

class AMIUpdater(object):
    def __init__(self):
        try:
            self.ec2_client = boto3.client('ec2')
        except Exception as err:
            print('{}\n'.format(err))
            raise err
            
    def find_AMI(self, productname):
        """
        Finds AMIs with the tag product equals to APS
        """
        try:
            if productname and isinstance(productname, six.string_types) and productname.strip():
                response = self.ec2_client.describe_images(
                    Filters=[
                        {
                            'Name': 'tag-key',
                            'Values': [
                                'Product',
                            ]
                        },
                    ]
                )
                if response is None:
                    raise ValueError('No AMI could be found')
                return response
            raise ValueError('The value of the tag key Product is not valid')
        except Exception as err:
            print('{}\n'.format(err))
        else:
            return None
            
    def amiUpdate(self, amiList):
        try:
            if amiList is None:
                raise ValueError('No valid Ami')
            for ami in amiList['Images']:
                for tag in ami['Tags']:
                    if tag['Key'] == 'Version':
                        if tag['Value'] == 'LATEST':
                            response = self.remove_tag(ami['ImageId'])
                            if response is None:
                                raise ValueError('Remove tag has failed')
                            print('The tag of the ami with id "{}" is removed'.format(ami['ImageId']))
                        else:
                            print('The tag of the ami with id "{}" is already removed'.format(ami['ImageId']))
            return 200
        except Exception as err:
            print('{}\n'.format(err))
        else:
            return None
            
            
    def remove_tag(self, amiName):
        try:
            if amiName and isinstance(amiName, six.string_types) and amiName.strip():
                response = self.ec2_client.create_tags(
                    Resources = [ amiName ],
                    Tags = [
                        {
                           'Key': 'Version',
                           'Value': ''
                        },    
                    ]
                )
                if response is None:
                    raise ValueError('Cannot remove tag')
                return response
            raise ValueError('AMI not valid')
        except Exception as err:
            print('{}\n'.format(err))
        else:
            return None
            
    def run(self, event):
        """
        Runs the AmiUpdater
        """
        try:
            if 'Product' in event:
                amiList = self.find_AMI(event['Product'])
                if amiList is None:
                    raise ValueError('Failed to find any ami')
                response = self.amiUpdate(amiList)
                return 200
            raise ValueError('Cannot find any event "product"')
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