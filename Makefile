.PHONY: build test

test: build
	docker run -it ansible_vault/py2 flake8
	docker run -it ansible_vault/py2 ./tests/test.sh
	docker run -it ansible_vault/py3 flake8
	docker run -it ansible_vault/py3 ./tests/test.sh

build:
	docker build -t ansible_vault/py2 -f tests/Dockerfile.py2 .
	docker build -t ansible_vault/py3 -f tests/Dockerfile.py3 .
