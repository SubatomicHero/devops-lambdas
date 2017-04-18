import requests
import json
import logging

logger = logging.getLogger(__name__)


class Marketo(object):

    def __init__(self, host, client_id, client_secret):
        self.host = host
        self.client_id = client_id
        self.client_secret = client_secret

        self.access_token = None

        self._authenticate()

    def get_leads(self, filter_type, filter_values, fields=""):
        r = self._request_handler(
                                method='get',
                                endpoint=self.host + "/rest/v1/leads.json",
                                params={
                                    'access_token': self.access_token,
                                    'filterType': filter_type,
                                    'filterValues': filter_values,
                                    'fields': fields
                                    }
                                )
        return json.loads(r.content.decode('utf-8'))

    def upsert_leads(self, leads, action="createOrUpdate", lookup_field="email", async_processing=False, partition_name=None):
        if type(leads) == dict:
            leads = [leads]

        params = {'access_token': self.access_token}

        data = {'action': action,
                'lookupField': lookup_field,
                'asyncProcessing': async_processing,
                'input': leads
                }

        if partition_name:
            data['partitionName'] = partition_name

        r = self._request_handler(
                                method='post',
                                endpoint=self.host + "/rest/v1/leads.json",
                                params=params,
                                data=json.dumps(data),
                                headers={
                                        'Content-Type': 'application/json',
                                        'Accept': 'application/json'
                                        }
                                )

        return json.loads(r.content.decode('utf-8'))

    def delete_leads(self, id_list):
        r = self._request_handler(
                                method='delete',
                                endpoint=self.host + "/rest/v1/leads.json",
                                params={
                                    'access_token': self.access_token,
                                    'id': ','.join(map(str, id_list)),
                                    },
                                headers={
                                        'Content-Type': 'application/json',
                                        'Accept': 'application/json'
                                        }
                                )
        return json.loads(r.content.decode('utf-8'))

    def _authenticate(self):
        logger.debug("Authenticating with Marketo")
        r = self._request_handler(
                                method='get',
                                endpoint=self.host + "/identity/oauth/token",
                                params={'grant_type': 'client_credentials',
                                        'client_id': self.client_id,
                                        'client_secret': self.client_secret
                                        }
                                )
        self.access_token = json.loads(r.content.decode('utf-8'))['access_token']
        logger.debug("Authenticated.  Access token: {}".format(self.access_token))

    def _check_marketo_errors(self, response):
        content = json.loads(response.content.decode('utf-8'))
        if 'success' in content and content['success'] == False:
            errors = []
            for error in content['errors']:
                if error['code'] == '601':
                    logger.warn("601 Access token invalid recieved from Marketo API")
                    raise MarketoAccessTokenInvalid("Access token invalid")
                if error['code'] == '602':
                    logger.warn("602 Access token expired recieved from Marketo API")
                    raise MarketoAccessTokenExpired("Access token expired")
                errors.append("{} - {}".format(error['code'], error['message']))
            if not errors:
                errors.append("No messages given, the API simply reported the request was unsuccessful.")
            raise MarketoAPIError("The Marketo API reported errors as a result of the last request:\n{}".format("\n - ".join(errors)))

    def _request_handler(self, method, endpoint, params, data="", headers=""):
        logger.debug("{} request to {}:  \nParams: {}\nData: {}\nHeaders: {}".format(
            method, endpoint, params, data, headers))
        retried = False

        while 1:
            response = getattr(requests, method)(endpoint,
                                            params=params,
                                            data=data,
                                            headers=headers
                                            )
            response.raise_for_status()
            try:
                self._check_marketo_errors(response)
                logger.debug("No errors found, returning result")
                return response
            except (MarketoAccessTokenInvalid, MarketoAccessTokenExpired) as e:
                logger.warn("Bad access token raised, requesting new token and retrying request")
                self._authenticate()
                if 'access_token' in params:
                    params['access_token'] = self.access_token
                if retried:
                    logger.debug("Already retried, still have a problem, raising exception")
                    raise
            retried = True


class MarketoAPIError(Exception):
    pass


class MarketoAccessTokenInvalid(Exception):
    pass


class MarketoAccessTokenExpired(Exception):
    pass
