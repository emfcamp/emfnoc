# EMF NOC - Configuration Builders

These various scripts generate portions of the EMF network infrastructure, spanning both physical appliances (switches)
to services (DHCP) under VMs. The authoritative source of truth is a master Google Docs spreadsheet, which is used
once to populate swathes of data into Netbox.

## Configuration

You will need a configuration file in ini format (specifically, Python ConfigParser).
This should go in `./emfnoc.conf` (for testing), `~/.emfnoc.conf` (preferred), or `/etc/emfnoc.conf` (global).

The sections you need depend on what script you are running.

Scripts that put data *into* Netbox need the `[gdata]` section to access the Google spreadsheet.
Scripts that put data into Netbox or take data from Netbox need the `[netbox]` section to access Netbox.

### Ini settings for Google Sheets

`populate-netbox.py` needs a connection to the NOC Combined spreadsheet to get the high-level data to populate Netbox
with.

Go to https://console.developers.google.com/iam-admin/projects?pli=1

Click on create project, fill in a name and tick the boxes.

Go to https://console.cloud.google.com/apis/credentials and select  your project
and create credentials, this will give you the OAuth Client ID and Client Secret.

Add this section to your config file:

```ini
[gdata]
noc_combined=<spreadsheet id of the spreadsheet, get it from the url>
oauth_client_id=<client id>
oauth_client_secret=<secret>
```

Run `populate-netbox.py` with the --download option. It will automatically open a web browser for you to authorise
access to Google Sheets. The access token is then stored in `.emf-gdata-token.json` so you shouldn't need to do this
again this year.

### Ini settings for Netbox

Most of the scripts pull data from or insert data into Netbox. You need to configure the Netbox connection parameters
in a `[netbox]` section in your config file.

First create an API token using the Profile option after clicking your name in the top right of Netbox and then going
to the API Tokens tab. Make the token read-only if you're only reading from Netbox, for safety.

Then add a Netbox section to your config file:

```ini
[netbox]
url=https://netbox.noc.emfcamp.org/
token=<token>
mgmt_vlan=87
mgmt_subnet_length=/24
mgmt_domain=emf.camp
tenant=emf2022
vlan_group=emf2022-site-vlans
site=eastnor
```

| Key | Meaning |
|-----|---------|
| url | base URL of Netbox installation |
| token | API token (can be read-only for config builders) |
| mgmt_vlan | Management VLAN (used by `populate-netbox.py`) |
| tenant | *slug* of the Netbox tenant to create everything under (used by `populate-netbox.py`) |

### Populating Netbox

```
./populate-netbox.py --download
./populate-netbox.py --populate-all
```


### Prerequisites

The majority of the scripts are written in Python and require a few modules for IP address calculations, template
generation, etc.

```
pip install -r requirements.txt
```

### dhcpd

You need this in your config file:

```ini
[dhcpd]
domain_campers=gchq.org.uk
domain_orga=emf.camp
dns_ipv4=78.158.87.11,78.158.87.12
dns_ipv6=2a05:e201:0:57::11,2a05:e201:0:57::12
sntp_ipv6=2a05:e201:0:57::11,2a05:e201:0:57::12
```

### Scripts

* `gen-dhcp.py` - Generates the DHCP server scopes

* `gen-icinga.py` - generates switch and link monitoring

* `gen-icinga.php` - 2012 icinga generation, not used this time around, has additional monitoring for servers but not
  links, because davidc couldn't be bothered to learn python last time round

* `gen-labels.py` - generates labels for the switches (after gen-switch.py --template=label)

* `gen-opennms.py` - incompelte OpenNMS generation

* `gen-roundup.py` - generates a list of users to paste into roundup-admin

* `gen_switch.py` - unnecessary symlink for unknown reason

* `gen-switch.py` - generates the complete switch configs

* `gen-zones.py` - generates the DNS forward and reverse zones

* `mopup.sh` - loops through all the configs and tells the switches to pull them over tftp using clogin (Rancid)

* `nocsheet.py` - shared library for all of the above

* `sanitise-rancid.sh` - remove passwords/communities/crypto keys before storing configs to github

* `gen-phones.py` - generates the icinga config for the phones, needs to be run on the voip server

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

## Generating the phones icinga config

You'll need to be able to read `/etc/asterisk/sip.conf`, so add youself to the asterisk group or something

You'll need to add a manager user so:

```
cd /etc/asterisk/manager.d
```

add `something.conf` containing:

```
[username]
secret = secret
deny=0.0.0.0/0.0.0.0
permit = 127.0.0.1/255.255.255.0
read = all
write = all
writetimeout = 1000
```

The script uses the `python-asterisk` package on debian, which needs a config file too, so add `~/.py-asterisk.conf`
containing:

```
[py-asterisk]
default connection: fish

[connection: fish]
hostname: localhost
port: 5038
username: username from manager.d/something.conf
secret: secret from manager.d/something.conf
```

Oauth2 stuff:

* https://developers.google.com/accounts/docs/OAuth2InstalledApp
* http://iemblog.blogspot.co.uk/2011/10/getting-started-with-python-gdata.html
* https://code.google.com/p/gdata-python-client/source/browse/samples/oauth/oauth_example.py
* https://developers.google.com/api-client-library/python/guide/aaa_oauth
