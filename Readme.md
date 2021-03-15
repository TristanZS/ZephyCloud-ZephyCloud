# ZephyCloud project

## Summary:

Zephycloud allow the ZephyTools desktop application to run computations on the cloud
It should be deployed on a server.


## Usage

You should use the `make` command.
Run `make help` to see main actions.
More fine-grained actions could be found in tools and tools/common
You can also run specific tests launching tests/run.py

A docker-based environment can be used for development, using the `make dev` command.
All the tooling and testing scripts should work on both windows linux and mac, 
but for now only linux have been tested ?

You should have some secrets shared on our dashboard to be able to configure and run it.

## Documentation:

Specific documentation is located in the "docs" folder.


## Requirements:

For most actions you will need:
* GNU make
* python 2
* gpg
* some python 2 libraries:
  * jinja2
  * ruamel.yaml
  * gnupg
  * beautifulsoup4 (bs4)
  * pycrypto
  * pyopenssl
  * python-hosts
  * paramiko
  * boto3
  * alembic
  * lxml
  * requests 
  * sqlalchemy_utils
  * psycopg2
  * tblib

### To run development environment:

You will need recent version of :
* docker
* docker-compose 
* some python 2 libraries:
  * flask
 

### To deploy on server:

You will need the basic requirements (see above) and also in the path:
* ssh client 
* gpg


### To test:

You sill need a shell and the following python libraries: 
* unittest2 
* lettuce 
* python-levenshtein
* nose
* flask  
* requests
* coverage
* mock
* mockredispy
* moto
* sqlalchemy_utils
* psycog2-binary

You also need:
* docker
* docker-compose
* binfmt-support for your linux kernel 
	
## Dev env:

If you launch a dev environment, using docker, it will bve available at the address:
```https://zephycloud.*YOUR_USER_NAME*.dev```

You will be able to found a certificate authority for your browser in folder:
* **Windows**: C:\Windows\System32\Certlog\aziugo_localdev_root_ca.crt
* **Linux**: /usr/local/share/cert_pems/aziugo/aziugo_localdev_root_ca.crt

You should add this in your browser certificate authority list

## Dashboard login:

If you are tired of typing your login and your password again and again, 
you can create a file called .aziugo_dashboard in your home folder.
Here an example of the .aziugo_dashboard:
```
User: samuel.deal
Password: XXXXXXXX
```

## That's all folks

Have fun :-)
