# /etc/puppet/modules/nocusers/manifests/init.pp

#nocusers are users who have accounts on all noc servers, but not other hosted servers

# uids are assigned in the noc spreadsheet

class nocusers {

      manageusers::create_account { prt:
      		name       => "Paul Thornton",
		uid	   => "2002",
		password   => 'REDACTED',
		shell      => "/bin/bash",
		groups     => ['sudo'],
		sshkeytype => "ssh-dss",
		sshkey     => "REDACTED",
		}

      manageusers::create_account { nihilus:
      		name       => "Christian Franke",
		uid	   => "2003",
		password   => 'REDACTED',
		shell      => "/bin/bash",
		groups     => [],
		sshkeytype => "ssh-rsa",
		sshkey     => "REDACTED",
		}

      manageusers::create_account { ak47:
      		name       => "Arjan Koopen",
		uid	   => "2005",
		password   => 'REDACTED',
		shell      => "/bin/bash",
		groups     => ['sudo'],
		sshkeytype => "ssh-rsa",
		sshkey     => "REDACTED",
		}

      manageusers::create_account { russ:
      		name       => "Russ Garrett",
		uid	   => "2006",
		password   => 'REDACTED',
		shell      => "/bin/bash",
		groups     => ['sudo'],
		sshkeytype => "ssh-rsa",
		sshkey     => "REDACTED",
		}

      manageusers::create_account { kay:
      		name       => "Kay Rechthien",
		uid	   => "2007",
		password   => 'REDACTED',
		shell      => "/bin/bash",
		groups     => ['sudo'],
		sshkeytype => "ssh-rsa",
		sshkey     => "REDACTED",
		}

      manageusers::create_account { tom:
      		name       => "Tom Bird",
		uid	   => "2008",
		password   => 'REDACTED',
		shell      => "/bin/bash",
		groups     => ['sudo'],
		sshkeytype => "ssh-rsa",
		sshkey     => "REDACTED",
		}

      manageusers::create_account { mat:
      		name       => "Mat Burnham",
		uid	   => "2009",
		password   => 'REDACTED',
		shell      => "/bin/bash",
		groups     => [],
		sshkeytype => "ssh-rsa",
		sshkey     => "REDACTED",
		}

      manageusers::create_account { leon:
      		name       => "Leon Weber",
		uid	   => "2010",
		password   => 'REDACTED',
		shell      => "/bin/bash",
		groups     => ['sudo'],
		sshkeytype => "ssh-rsa",
		sshkey     => "REDACTED",
		}

      manageusers::create_account { danrl:
      		name       => "Dan Luedtke",
		uid	   => "2011",
		password   => 'REDACTED',
		shell      => "/bin/bash",
		groups     => [],
		sshkeytype => "ssh-rsa",
		sshkey     => "REDACTED",
		}

}
