import os
from urlparse import urljoin
from ansible import utils, errors
from ansible.utils import template

try:
    import requests
except ImportError:
    raise errors.AnsibleError("Module 'requests' is required to do vault lookups")

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
        r = requests.get(request_url, headers={"X-Vault-Token": token})

        if r.status_code != 200:
           raise errors.AnsibleError("Failed to get %s from Vault: %s" % (terms, ','.join(r.json()['errors'])))

        return [r.json()['data']['value']]
