# ansible-vault lookup module
This is a lookup module for secrets stored in [HashiCorp Vault](https://vaultproject.io/).
Supports Ansible 1.9 and 2.x

### Installation
lookup plugins can be loaded from several different locations similar to $PATH, see [docs](http://docs.ansible.com/ansible/intro_configuration.html#lookup-plugins).

### Usage
The address to the Vault server and the auth token are fetched from environment variables

    export VAULT_ADDR=http://192.168.33.10:8200/
    export VAULT_TOKEN=56f48aef-8ad3-a0c4-447b-8e96990776ff

The plugin also supports Vault's CA-related environment variables, to
enable use of a server certificate issued by a not-widely-trusted
Certificate Authority

    export VAULT_CACERT=/etc/ssl/certs/localCA.pem
    export VAULT_CAPATH=/etc/ssl/localCA

ansible-vault then works as any other lookup plugin.

```yaml
- debug: msg="{{ lookup('vault', 'secret/foo', 'value') }}"
```

```yaml
# templates/example.j2

# Generic secrets
{{ lookup('vault', 'secret/hello').value }} # world
# Generic secrets with parameters
{{ lookup('vault', 'pki/issue/example-dot-com common_name=foo.example.com format=pem_bundle').certificate }}
# Specify field inside lookup
{{ lookup('vault', 'secret/hello', 'value') }} # world

# Dynamic secrets
{% set aws = lookup('vault', 'aws/creds/deploy') %}
access_key = {{ aws.access_key }} # AKSCAIZSFSYHFGA
secret_key = {{ aws.secret_key }} # 4XSLxDUS+hyXgoIHEhCKExHDGAJDHFiUA/adi
```

### What's the difference between `ansible-vault` and `hashi_vault`

- (Ansible Vault) No external dependencies; (hashi_vault) requires hvac
- (Ansible Vault) Uses the same environment variables as vault itself
- (Ansible Vault) Quicker update cycle
- (Ansible Vault) Supports dynamic secrets
- (Ansible Vault) Supports custom fields
