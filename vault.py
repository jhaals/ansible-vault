import os
import urllib2
import json
import sys
from urlparse import urljoin

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase


class LookupModule(LookupBase):

    def run(self, terms, variables, **kwargs):
        key = terms[0]
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
            headers = { 'X-Vault-Token' : token }
            req = urllib2.Request(request_url, None, headers)
            response = urllib2.urlopen(req)
        except urllib2.HTTPError as e:
            raise AnsibleError('Unable to read %s from vault: %s' % (key, e))
        except:
            raise AnsibleError('Unable to read %s from vault' % key)

        result = json.loads(response.read())

        return [result['data'][field]] if field is not None else [result['data']]
