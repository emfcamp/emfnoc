EMF NOC Config Builders
=======================

You'll need to:

aptitude install python-gdata python-gdata-doc python-ipaddr


Generating switch config
------------------------

You'll need to:

aptitude install python-gdata python-gdata-doc python-ipaddr python-jinja2 graphviz

Create configuration file /etc/emf-gdata.conf containing:

```
[gdata]
email=<google login>
password=<google password>
noc_combined=<spreadsheet id of the spreadsheet, get it from the url>
[switchconfig]
enable=<unencrypted enable password>
community=<unencrypted snmp community>
```

Then run
./gen-switch.py --download
./gen-switch.py --generate

Generating labels
-----------------

First, run the switch config generator with the special "labels" template.

./gen-switch.py  --generate --template=labels

Then turn it into a PDF:

./gen-labels.py

Oauth2 stuff:

https://developers.google.com/accounts/docs/OAuth2InstalledApp
http://iemblog.blogspot.co.uk/2011/10/getting-started-with-python-gdata.html
https://code.google.com/p/gdata-python-client/source/browse/samples/oauth/oauth_example.py
https://developers.google.com/api-client-library/python/guide/aaa_oauth
