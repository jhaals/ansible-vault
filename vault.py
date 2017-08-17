import os
# compatibility with Python >= 2.7.13
try:
    import urllib2
except ImportError:
    import urllib.request as urllib2

import json
import errno
import ssl
import shlex
from distutils.version import StrictVersion
from sys import version_info

# compatibility with Python >= 2.7.13
try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin

from ansible.errors import AnsibleError
import ansible.utils
try:
    from ansible.plugins.lookup import LookupBase
except ImportError:
    # ansible-1.9.x
    class LookupBase(object):
        def __init__(self, basedir=None, runner=None, **kwargs):
            self.runner = runner
            self.basedir = basedir or (self.runner.basedir
                                       if self.runner
                                       else None)

        def get_basedir(self, variables):
            return self.basedir

_use_vault_cache = os.environ.get("ANSIBLE_HASHICORP_VAULT_USE_CACHE", "yes").lower() in ("yes", "1", "true")
_vault_cache = {}

DISABLE_VAULT_CAHOSTVERIFY = "no"


class LookupModule(LookupBase):

    def run(self, terms, inject=None, variables=None, **kwargs):
        # Ansible variables are passed via "variables" in ansible 2.x, "inject" in 1.9.x

        basedir = self.get_basedir(variables)

        if hasattr(ansible.utils, 'listify_lookup_plugin_terms'):
            # ansible-1.9.x
            terms = ansible.utils.listify_lookup_plugin_terms(terms, basedir, inject)

        term_split = terms[0].split(' ', 1)
        key = term_split[0]

        # the environment variable takes precendence over the Ansible variable.
        cafile = os.getenv('VAULT_CACERT') or (variables or inject).get('vault_cacert')
        capath = os.getenv('VAULT_CAPATH') or (variables or inject).get('vault_capath')
        cahostverify = (os.getenv('VAULT_CAHOSTVERIFY') or
                        (variables or inject).get('vault_cahostverify') or 'yes') != DISABLE_VAULT_CAHOSTVERIFY

        python_version_cur = ".".join([str(version_info.major),
                                       str(version_info.minor),
                                       str(version_info.micro)])
        python_version_min = "2.7.9"
        if StrictVersion(python_version_cur) < StrictVersion(python_version_min):
            if cafile or capath:
                raise AnsibleError('Unable to read %s from vault:'
                                   ' Using Python %s, and vault lookup plugin requires at least %s'
                                   ' to use an SSL context (VAULT_CACERT or VAULT_CAPATH)'
                                   % (key, python_version_cur, python_version_min))
            elif cahostverify:
                raise AnsibleError('Unable to read %s from vault:'
                                   ' Using Python %s, and vault lookup plugin requires at least %s'
                                   ' to verify Vault certificate. (set VAULT_CAHOSTVERIFY to \'%s\''
                                   ' to disable certificate verification.)'
                                   % (key, python_version_cur, python_version_min, DISABLE_VAULT_CAHOSTVERIFY))

        try:
            parameters = term_split[1]
            parameters = shlex.split(parameters)

            parameter_bag = {}
            for parameter in parameters:
                parameter_split = parameter.split('=', 1)

                parameter_key = parameter_split[0]
                parameter_value = parameter_split[1]
                parameter_bag[parameter_key] = parameter_value

            data = json.dumps(parameter_bag)
        except Exception:
            data = None

        try:
            field = terms[1]
        except IndexError:
            field = None

        # the environment variable takes precendence over the Ansible variable.
        url = os.getenv('VAULT_ADDR') or (variables or inject).get('vault_addr')
        if not url:
            raise AnsibleError('Vault address not set. Specify with'
                               ' VAULT_ADDR environment variable or vault_addr Ansible variable')

        # Support for Approle backend
        approle_role_id = os.getenv('ANSIBLE_HASHICORP_VAULT_ROLE_ID')
        approle_secret_id = os.getenv('ANSIBLE_HASHICORP_VAULT_SECRET_ID')
        approle_role_path = os.getenv('ANSIBLE_HASHICORP_VAULT_ROLE_PATH', 'v1/auth/approle/login')

        # first check if an approle token is already cached
        vault_token = _vault_cache.get('ANSIBLE_HASHICORP_VAULT_APPROLE_TOKEN', None)

        # if approle role-id and secret-id are set, use approle to get a token
        # and if caching is activated, the token will be stored in the cache
        if not vault_token and approle_role_id and approle_secret_id:
            vault_token = self._fetch_approle_token(
                cafile, capath, approle_role_id, approle_secret_id, approle_role_path, url, cahostverify)
            if vault_token and _use_vault_cache:
                _vault_cache['ANSIBLE_HASHICORP_VAULT_APPROLE_TOKEN'] = vault_token

        # the environment variable takes precedence over the file-based token.
        # intentionally do *not* support setting this via an Ansible variable,
        # so as not to encourage bad security practices.
        github_token = os.getenv('VAULT_GITHUB_API_TOKEN')
        if not vault_token:
            vault_token = os.getenv('VAULT_TOKEN')
        if not vault_token and not github_token:
            token_path = os.path.join(os.getenv('HOME'), '.vault-token')
            try:
                with open(token_path) as token_file:
                    vault_token = token_file.read().strip()
            except IOError as err:
                if err.errno != errno.ENOENT:
                    raise AnsibleError('Error occurred when opening ' + token_path + ': ' + err.strerror)
        if not github_token and not vault_token:
            raise AnsibleError('Vault or GitHub authentication token missing. Specify with'
                               ' VAULT_TOKEN/VAULT_GITHUB_API_TOKEN environment variable or in $HOME/.vault-token '
                               '(Current $HOME value is ' + os.getenv('HOME') + ')')

        if _use_vault_cache and key in _vault_cache:
            result = _vault_cache[key]
        else:
            if not vault_token:
                token_result = self._fetch_github_token(cafile, capath, github_token, url, cahostverify)
                vault_token = token_result['auth']['client_token']
            result = self._fetch_remotely(cafile, capath, data, key, vault_token, url, cahostverify)
            if _use_vault_cache:
                _vault_cache[key] = result

        if type(result) is dict:
            if field is not None:
                return [result['data'][field]]
            elif 'data' in result:
                return [result['data']]
        return [result]

    def _fetch_approle_token(self, cafile, capath, role_id, secret_id, approle_role_path, url, cahostverify):
        request_url = urljoin(url, approle_role_path)
        req_params = {
            'role_id': role_id,
            'secret_id': secret_id
        }
        result = self._fetch_client_token(cafile, capath, request_url, req_params, cahostverify)
        token = result['auth']['client_token']
        return token

    def _fetch_github_token(self, cafile, capath, github_token, url, cahostverify):
        request_url = urljoin(url, "v1/auth/github/login")
        req_params = {}
        req_params['token'] = github_token
        result = self._fetch_client_token(cafile, capath, request_url, req_params, cahostverify)
        return result

    def _fetch_client_token(self, cafile, capath, url, data, cahostverify):
        try:
            context = None
            if cafile or capath:
                context = ssl.create_default_context(cafile=cafile, capath=capath)
                context.check_hostname = cahostverify
            req = urllib2.Request(url, json.dumps(data))
            req.add_header('Content-Type', 'application/json')
            response = urllib2.urlopen(req, context=context) if context else urllib2.urlopen(req)
        except AttributeError as e:
            raise AnsibleError('Unable to retrieve personal token from vault: %s' % (e))
        except urllib2.HTTPError as e:
            raise AnsibleError('Unable to retrieve personal token from vault: %s' % (e))
        except Exception as e:
            raise AnsibleError('Unable to retrieve personal token from vault: %s' % (e))
        result = json.loads(response.read())
        return result

    def _fetch_remotely(self, cafile, capath, data, key, vault_token, url, cahostverify):
        try:
            context = None
            if cafile or capath:
                context = ssl.create_default_context(cafile=cafile, capath=capath)
                context.check_hostname = cahostverify
            request_url = urljoin(url, "v1/%s" % (key))
            req = urllib2.Request(request_url, data)
            req.add_header('X-Vault-Token', vault_token)
            req.add_header('Content-Type', 'application/json')
            response = urllib2.urlopen(req, context=context) if context else urllib2.urlopen(req)
        except AttributeError as e:
            raise AnsibleError('Unable to read %s from vault: %s' % (key, e))
        except urllib2.HTTPError as e:
            raise AnsibleError('Unable to read %s from vault: %s' % (key, e))
        except Exception as e:
            raise AnsibleError('Unable to read %s from vault: %s' % (key, e))
        body = response.read()
        if response.headers.get('Content-Type') == 'application/json':
            body = json.loads(body)
        return body
