# EMF NOC - Configuration Builders
These various scripts generate portions of the EMF network infrastructure, spanning both physical appliances (switches) to services (DHCP) under VM's. The authoritative source of truth is a master Google Docs spreadsheet, a sanitised version of the spreadsheet with only the necessary data can be found in `../archives/2014/documents/NOC Team Combined - REDACTED.xlsx`

### Prereqsuites
The majority of the scripts are written in Python and require a few modules for IP address calculations, template generation, etc.

Under a Debian based Linux distro:

    aptitude install python-gdata python-gdata-doc python-ipaddr python-jinja2 graphviz bind9utils

For OSX hosts (not fully vetted):

    sudo pip install gdata ipaddr jinja2

Go to https://console.developers.google.com/iam-admin/projects?pli=1

Click on create project, fill in a name and tick the boxes, choose Google Sheets API, click on credentials, (you may need to create a credential first?), and that's where the `oauth_client_id` and `secret` are.

Create configuration file `/etc/emf-gdata.conf` containing:

```
[gdata]
noc_combined=<spreadsheet id of the spreadsheet, get it from the url>
oauth_client_id=
oauth_client_secret=

[switchconfig]
enable=<unencrypted enable password>
community=<unencrypted snmp community>
```

### Scripts

* `gen-dhcp.py` - Generates the DHCP server scopes

* `gen-icinga.py` - generates switch and link monitoring

* `gen-icinga.php` - 2012 icinga generation, not used this time around, has additional monitoring
for servers but not links, because davidc couldn't be bothered to learn python last time round

* `gen-labels.py` - generates labels for the switches (after gen-switch.py --template=label)

* `gen-opennms.py` - incompelte OpenNMS generation

* `gen-roundup.py` - generates a list of users to paste into roundup-admin

* `gen_switch.py` - unnecessary symlink for unknown reason

* `gen-switch.py` - generates the complete switch configs

* `gen-zones.py` - generates the DNS forward and reverse zones

* `mopup.sh` - loops through all the configs and tells the switches to pull them over tftp using clogin (Rancid)

* `nocsheet.py` - shared library for all of the above

* `sanitise-rancid.sh` - remove passwords/communities/crypto keys before storing configs to github


Generating switch config
------------------------

The first time you run a configbuilder command it will give you a url to go to.

Go there, and it will give you an oauth token to add to emf-gdata.conf as well.

Then run
```
./gen-switch.py --download
./gen-switch.py --generate
```

Generating labels
-----------------

First, run the switch config generator with the special "labels" template.

```
./gen-switch.py  --generate --template=labels
```

Then turn it into a PDF:

```
./gen-labels.py
```

Oauth2 stuff:

* https://developers.google.com/accounts/docs/OAuth2InstalledApp
* http://iemblog.blogspot.co.uk/2011/10/getting-started-with-python-gdata.html
* https://code.google.com/p/gdata-python-client/source/browse/samples/oauth/oauth_example.py
* https://developers.google.com/api-client-library/python/guide/aaa_oauth
