import os
import urllib2
import json
import sys
from urlparse import urljoin

from ansible import utils, errors
from ansible.utils import template

class LookupModule(object):

    def __init__(self, basedir=None, **kwargs):
        self.basedir = basedir

    def run(self, terms, inject=None, **kwargs):

        try:
            terms = template.template(self.basedir, terms, inject)
        except Exception, e:
            pass

        url = os.getenv('VAULT_ADDR')
        if not url:
            raise errors.AnsibleError('VAULT_ADDR environment variable is missing')

        token = os.getenv('VAULT_TOKEN')
        if not token:
            raise errors.AnsibleError('VAULT_TOKEN environment variable is missing')

        request_url = urljoin(url, "v1/%s" % (terms))
        try:
            headers = { 'X-Vault-Token' : token }
            req = urllib2.Request(request_url, None, headers)
            response = urllib2.urlopen(req)
        except urllib2.HTTPError as e:
            raise errors.AnsibleError('Unable to read %s from vault: %s' % (terms, e))
        except:
            raise errors.AnsibleError('Unable to read %s from vault' % terms)
        result = json.loads(response.read())
        return [result['data']['value']]
