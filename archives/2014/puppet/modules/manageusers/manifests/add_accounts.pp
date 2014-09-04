class manageusers::add_accounts() {

  ##
  ## Accounts to create go in this file
  ##

#  manageusers::create_account { user1:
#    name       => "John Smith",
#    uid        => "700",
#    password   => '$1$abcedfghijklmnopqrstuvwxyz',
#    shell      => "/bin/bash",
#    groups     => ['sudo', 'user1'],
#    sshkeytype => "ssh-dss",
#    sshkey     => "MyKeyWouldGoHere"
#  }

#  manageusers::create_account { user2:
#    name       => "Jane Smith",
#    uid        => "701",
#    password   => '$1$abcedfghijklmnopqrstuvwxyz',
#    shell      => "/bin/bash",
#    groups     => ['sudo', 'user2'],
#    sshkeytype => "ssh-dss",
#    sshkey     => "MyKeyWouldGoHere"
#  }

#  manageusers::create_account { user5:
#    name       => "John Doe",
#    uid        => "703",
#    password   => '$1$abcedfghijklmnopqrstuvwxyz',
#    shell      => "/bin/bash",
#    groups     => ['sudo', 'user5'],
#    sshkeytype => "ssh-dss",
#    sshkey     => "MyKeyWouldGoHere"
#  }

#  manageusers::create_account { user6:
#    name       => "Bob Smith",
#    uid        => "706",
#    password   => '$1$abcedfghijklmnopqrstuvwxyz',
#    shell      => "/bin/bash",
#    groups     => ['sudo', 'user6'],
#    sshkeytype => "ssh-dss",
#    sshkey     => "MyKeyWouldGoHere"
#  }

  ##
  ## Example of how to install on a single system
  ##
#  if $fqdn == "ubuntu1404.example.com" {
#    manageusers::create_account { user8:
#      name       => "Single System",
#      uid        => "708",
#      password   => '$1$abcedfghijklmnopqrstuvwxyz',
#      shell      => "/bin/bash",
#      groups     => ['sudo', 'user8'],
#      sshkeytype => "ssh-dss",
#      sshkey     => "MyKeyWouldGoHere"
#    }
#  }

}
