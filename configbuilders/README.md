
You'll need to:

aptitude install python-gdata python-gdata-doc python-ipaddr


== gen-switch.py ==

You'll need to:

aptitude install python-gdata python-gdata-doc python-ipaddr python-jinja2 graphviz

Create configuration file /etc/emf-gdata.conf containing:

[gdata]
email=
password=
noc_combined=
[switchconfig]
enable=
community=

== Generating labels ==

First, run the switch config generator with the special "labels" template.

./gen-switch.py  --generate --template=labels

Then turn it into a PDF:

./gen-labels.py

Oauth2 stuff:

https://developers.google.com/accounts/docs/OAuth2InstalledApp
http://iemblog.blogspot.co.uk/2011/10/getting-started-with-python-gdata.html
https://code.google.com/p/gdata-python-client/source/browse/samples/oauth/oauth_example.py
https://developers.google.com/api-client-library/python/guide/aaa_oauth
