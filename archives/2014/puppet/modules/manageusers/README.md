# manageusers

#### Table of Contents

1. [Overview](#overview)
2. [Description](#description)
3. [Installation](#installation)
    * [Using Native Puppet Commands](#using-puppet)
    * [Manually Using GIT](#using-git)
4. [Usage](#usage)
    * [Adding Users](#adding-users)
    * [Removing Users](#removing-users)
    * [Start the System](#main-call)
5. [Limitations - OS compatibility, etc.](#limitations)
6. [Development - Guide for contributing to the module](#development)




## Overview

Puppet module to manage users, groups, and ssh keys on a group of systems that
all share a common user base.


## Description

This module is designed to be a simple system to manage a common set of
usernames, UIDs, GIDs, passwords, groups and ssh keys across common set of
servers.  The primary motivations behind this module are:

  * Single point of account management
  * No single point of failure like some SSO systems may introduce
  * user, group(s), and ssh keys are ALL required for account creation
  * Simple syntax that is easy to learn and easy to use
  * No external module dependencies


## Installation

Copy the module into your /etc/puppet/modules directory.

### Using Puppet (Native Command)

    puppet module install duxklr-manageusers

### Using GIT

    cd /etc/puppet/modules
    git clone git@github.com:duxklr/manageusers.git


## Usage

All user account configuration is stored in one of two files.  The entire
system is then called from the main site.pp.   Examples:


### Adding Users

Edit the /pathToPuppetConfig/modules/manageusers/manifests/add_accounts.pp to
add user accounts (similar to this):

    manageusers::create_account { user1:
        name       => "John Smith",
        uid        => "700",
        password   => '$1$abcedfghijklmnopqrstuvwxyz',
        shell      => "/bin/bash",
        groups     => ['sudo', 'user1'],
        sshkeytype => "ssh-dss",
        sshkey     => "AAAAB3NzaC1kc3MAAACBAJzMVL4afDQBJ3rcM9LlHqxg0rmkWDwoWehS4nIpBLJL9qGoyR1YBzPvpD1VufsUqgUXH9dYdfaiVum4IaTgyu2Tb0ezR4Nx2Jkcnp+8jFh/Cys3zgMvzJaIw/Au45E9h4vBdwvouj1Sg0YaY5mGuKZ2w121uPLawjc3DJsNSc+jAAAAFQCb7+Vtir8w+o/CIDiSPXr6MVj16QAAAIBFHMnBixvQax1ekLK70eR9TgYUAXsh0MHT8VT+XMUWlOC8u8yVEOTDzrU1ZL2vNWo4NZL6ex9ffx0JRS5hSCU/o8aVcoC4viCC7SGmntNb0nQo+iKUyTQbGcmMoPG9lO498prML66GbOYWzTedc4XT683kyWV4k0iVixyvLsfLnAAAAIB4PmZfjdTtYwC7cE/upvfC/HWpKHHAn66YW6PRTCwZPqCd2AvHAMX/l7nbk1u+BL0YtymawzNT97FcYuvM1UWrJ+fT8iIsTyHsoUkf76irVxcTBH0SReChHbYeWa2bATEvaj0u2597H4O7qYHJ6IZpTTAeWP0EeKDABfonAr+ZJw=="
    }


### Removing Users

Edit the /pathToPuppetConfig/modules/manageusers/manifests/remove_accounts.pp to remove user accounts (similar to this):

	user { user3:
		ensure => "absent"
	}

### Main Call

Once the user information is added.  Call the main system.  

Edit the /pathToPuppetConfig/manifests/site.pp and call the manageusers module (similar to this):

    node 'default' {
      include manageusers
    }


## Limitations

Tested and known to work with Ubuntu (10.x, 12.x, 14.x) and RedHat (5.x, 6.x).


## Development

Comments, suggestions, and code can be found here: https://github.com/duxklr/manageusers

