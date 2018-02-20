#!/bin/bash
export VAULT_ADDR='http://127.0.0.1:8200'
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export ANSIBLE_CONFIG=$DIR/ansible.cfg
ERR=0
vault server -dev &
VAULT_PID=$!
sleep 1
vault secrets enable pki
vault write pki/root/generate/internal common_name=myvault.com
vault write pki/config/urls issuing_certificates="http://127.0.0.1:8200/v1/pki/ca" crl_distribution_points="http://127.0.0.1:8200/v1/pki/crl"
vault write pki/roles/example-dot-com \
       allowed_domains="example.com" \
       allow_subdomains="true" max_ttl="72h"
vault write pki/issue/example-dot-com \
        common_name=blah.example.com
vault write secret/hello value=world
vault write secret/user password="secret password"
ansible-playbook $DIR/test-playbook.yaml
if [ $? -ne 0 ]; then
    ERR=1
fi
kill $VAULT_PID
exit $ERR
