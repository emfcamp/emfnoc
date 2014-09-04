# /etc/puppet/modules/nocusers/manifests/init.pp

#superusers are users who have accounts on both noc servers and all other hosted servers

# uids are assigned in the noc spreadsheet

class superusers {

      manageusers::create_account { david:
      		name       => "David Croft",
		uid        => "1000",
		password   => 'REDACTED',
		shell      => "/bin/bash",
		groups     => ['sudo', 'adm'],
		sshkeytype => "ssh-rsa",
		sshkey     => "REDACTED",
		}

#additional key for david
      ssh_authorized_key { "david-flamingo":
      		ensure => present,
		user => 'david',
		type => 'ssh-rsa',
		key => 'REDACTED',
		}

#additional key for david
      ssh_authorized_key { "david-albatross":
      		ensure => present,
		user => 'david',
		type => 'ssh-rsa',
		key => 'REDACTED',
		}

#additional key for david
      ssh_authorized_key { "david-jmp":
      		ensure => present,
		user => 'david',
		type => 'ssh-rsa',
		key => 'REDACTED',
		}


      manageusers::create_account { jasper:
      		name       => "Jasper Wallace",
		uid        => "2001",
		password   => 'REDACTED',
		shell      => "/bin/bash",
		groups     => ['sudo', 'adm'],
		sshkeytype => "ssh-rsa",
		sshkey     => "REDACTED",
		}

      manageusers::create_account { will:
      		name       => "Will Hargrave",
		uid        => "2004",
		password   => 'REDACTED',
		shell      => "/bin/bash",
		groups     => ['sudo', 'adm'],
		sshkeytype => "ssh-rsa",
		sshkey     => "REDACTED",
		}

}
