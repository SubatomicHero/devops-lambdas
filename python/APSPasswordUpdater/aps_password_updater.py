import os
import json
import base64
import logging
import requests
import cfnresponse

def handler(event, context):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if event['RequestType'] == 'Create':
        api = "{}/api/enterprise/users/1".format(os.getenv('url'))
        logger.info(api)
        username = os.getenv('username')
        password = os.getenv('old_password')
        base64string = base64.encodestring(('%s:%s' % (username, password)).encode()).decode()
        base64string = base64string.replace('\n', '')
        headers = {
            "Content-Type":"application/json",
            "Authorization": "Basic {}".format(base64string)
        }
        data = {
            "action":"updatePassword",
            "newPassword": "{}".format(os.getenv('new_password')),
            "oldPassword": "{}".format(os.getenv('old_password'))
        }
        try:
            response = requests.post(api, data=json.dumps(data), headers=headers)
            logger.info(response.status_code)
            if response.status_code == 200:
                cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
            else:
                cfnresponse.send(event, context, cfnresponse.FAILED, {})
        except requests.HTTPError as error:
            logger.error("%s", error)
            cfnresponse.send(event, context, cfnresponse.FAILED, {})
    else:
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
