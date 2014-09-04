EMF NOC Config Builders
=======================

You'll need to:

aptitude install python-gdata python-gdata-doc python-ipaddr

Overview
--------

These script generate various bits of EMF config from our master Google Docs spreadsheet.
A sanitised version of the spreadsheet will be uploaded here in due course.

gen-dhcp.py - Generates the DHCP server scopes

gen-icinga.py - generates switch and link monitoring

gen-icinga.php - 2012 icinga generation, not used this time around, has additional monitoring
for servers but not links

gen-labels.py - generates labels for the switches (after gen-switch.py --template=label)

gen-opennms.py - ?

gen-roundup.py - generates a list of users to paste into roundup-admin

gen_switch.py - unnecessary symlink for unknown reason

gen-switch.py - generates the complete switch configs

gen-zones.py - generates the DNS forward and reverse zones

mopup.sh - loops through all the configs and tells the switches to pull them over tftp using clogin

nocsheet.py - shared library for all of the above

sanitise-rancid.sh - remove passwords/communities/crypto keys before storing configs to github


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
