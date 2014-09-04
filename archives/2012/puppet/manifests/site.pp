import "classes/*.pp"

node default {
  include ssh
  include sudo
  include useful
  include users
  include resolver
  include snmpd
  include ntp
  include serialconsole
  file { '/etc/motd':
    source => 'puppet:///files/motd'
  }
}

# streaming1.ppmk.emfcamp.org
# vm for naxxfish, excludes sudo so he can be local admin
node streaming1 {
  include ssh
  include useful
  include users
  include resolver
  include snmpd
  include ntp
  include serialconsole
}

node resolver1 {
  include ssh
  include sudo
  include useful
  include users
  include snmpd
  include ntp
  include serialconsole
}

node resolver2 {
  include ssh
  include sudo
  include useful
  include users
  include snmpd
  include ntp
  include serialconsole
}

node host0 {
  include kvmhost
}

node host1 {
  include kvmhost
}

node host2 {
  include kvmhost
}

node host3 {
  include kvmhost
}

class kvmhost {
  include ssh
  include sudo
  include useful
  include users
  include snmpd
  include resolver
  include ntp
  package { 'bridge-utils': ensure=> installed }
  package { 'vlan': ensure=> installed }
  package { 'ifenslave-2.6': ensure=> installed }
  package { 'kvm': ensure=> installed }
  package { 'qemu-kvm': ensure=> installed }
  package { 'libvirt-bin': ensure=> installed }
  package { 'virtinst': ensure=> installed }
  package { 'virt-top': ensure=> installed }
  include serialconsole
}

# the shell server
node beasty {
  include ssh
#  include sudo # disabled s i can give mat root
  include useful
  include users
  include snmpd
  include resolver 
  include ntp
  package { 'bridge-utils': ensure=> installed }
  package { 'vlan': ensure=> installed }
  package { 'ifenslave-2.6': ensure=> installed }
  package { 'kvm': ensure=> installed }
  package { 'qemu-kvm': ensure=> installed }
  package { 'libvirt-bin': ensure=> installed }
  package { 'virtinst': ensure=> installed }
  package { 'virt-top': ensure=> installed }
}

class users {
  add_user { nat:	email    => "nat@nuqe.net",		uid => 5001,	shell => "/bin/bash",
   password => ''
  }
  
  add_ssh_key { nat:		type => "ssh-dss",key=> ""
  }

  user { root:  password => '' }

  # disable localadmin account, used for installs
  user { localadmin: ensure => absent }
}


class ssh {
  package { 'openssh-server':
    ensure => installed
  }

  # need to stop root ssh access

}

class sudo {
        package { sudo: ensure => latest }
        file { "/etc/sudoers":
                owner   => root,
                group   => root,
                mode    => 440,
                source  => "puppet:///files/sudoers",
                require => Package["sudo"],
        }
}

class useful {
  package { 'tshark': ensure => installed }
  package { 'iftop': ensure => installed }
  package { 'bind9-host': ensure => installed }
  package { 'mtr-tiny': ensure => installed }
  package { 'zsh': ensure => installed }
  package { 'locate': ensure => installed }
  package { 'curl': ensure => installed }
  package { 'screen': ensure=> installed }
  package { 'ccze': ensure=> installed }
  package { 'mpt-status': ensure=> purged }
  package { 'less': ensure=> installed }
  package { 'python-iplib': ensure=> installed }
  package { 'rsync': ensure=> installed }
  package { 'ipcalc': ensure=> installed }
  package { 'tcpdump': ensure=> installed }
}

class resolver {
	file { "/etc/resolv.conf":
		owner => root,
		group => root,
		mode => 644,
		source => "puppet:///files/resolv.conf"
	}
}

class ntp {
        package { 'ntp': ensure=> installed }
	file { "/etc/ntp.conf":
		owner => root,
		group => root,
		mode => 644,
		source => "puppet:///files/ntp.conf"
	}
}


class serialconsole {
	file { "/etc/inittab":
		owner => root,
		group => root,
		mode => 644,
		source => "puppet:///files/inittab-for-serial"
	}
	file { "/etc/default/grub":
		owner => root,
		group => root,
		mode => 644,
		source => "puppet:///files/grubdefault-for-serial"
	}
	exec { "/usr/sbin/update-grub":
  	  subscribe => File["/etc/default/grub"],
	    refreshonly => true,
	  }
}
