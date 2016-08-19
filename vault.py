import os
import urllib2
import json
import sys
from urlparse import urljoin

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase


class LookupModule(LookupBase):

    def run(self, terms, variables, **kwargs):
        term_split = terms[0].split(' ', 1)
        key = term_split[0]

        try:
            parameters = term_split[1]

            parameters = parameters.split(' ')

            parameter_bag = {}
            for parameter in parameters:
                parameter_split = parameter.split('=')

                parameter_key = parameter_split[0]
                parameter_value = parameter_split[1]
                parameter_bag[parameter_key] = parameter_value

            data = json.dumps(parameter_bag)
        except:
            data = None

        try:
            field = terms[1]
        except:
            field = None

        url = os.getenv('VAULT_ADDR')
        if not url:
            raise AnsibleError('VAULT_ADDR environment variable is missing')

        token = os.getenv('VAULT_TOKEN')
        if not token:
            raise AnsibleError('VAULT_TOKEN environment variable is missing')

        request_url = urljoin(url, "v1/%s" % (key))

        try:
            req = urllib2.Request(request_url, data)
            req.add_header('X-Vault-Token', token)
            req.add_header('Content-Type', 'application/json')
            response = urllib2.urlopen(req)
        except urllib2.HTTPError as e:
            raise AnsibleError('Unable to read %s from vault: %s' % (key, e))
        except Exception as e:
            raise AnsibleError('Unable to read %s from vault: %s' % (key, e))

        result = json.loads(response.read())

        return [result['data'][field]] if field is not None else [result['data']]
