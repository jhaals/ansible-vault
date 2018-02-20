FROM python:3.6-slim

ENV VAULT_VERSION 0.9.3

RUN apt-get update && \
    apt-get install unzip curl -y

RUN curl -LO https://releases.hashicorp.com/vault/${VAULT_VERSION}/vault_${VAULT_VERSION}_linux_amd64.zip && \
    unzip vault_${VAULT_VERSION}_linux_amd64.zip -d /bin

RUN pip install --upgrade setuptools
RUN pip install ansible flake8
COPY . ansible-vault
WORKDIR ./ansible-vault

CMD ["./tests/test.sh"]
