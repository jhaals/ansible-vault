FROM python:2-wheezy

RUN apt-get update && apt-get install unzip
RUN curl -LO https://releases.hashicorp.com/vault/0.7.3/vault_0.7.3_linux_amd64.zip && \
    unzip vault_0.7.3_linux_amd64.zip -d /bin
RUN pip install ansible
COPY . ansible-vault

ENTRYPOINT ./ansible-vault/tests/test.sh
