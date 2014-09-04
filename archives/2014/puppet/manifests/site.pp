# /etc/puppet/manifests/site.pp

node default {
    include sudo
    include motd
    include emfhosts
    include emfresolvers

    if $fqdn != 'services1.emf.camp' and $fqdn != 'services2.emf.camp' {
       include ntp
    }
    file {'/etc/mailname':
          ensure  => file,
          mode    => 0644,
          content => "${fqdn}",
      }
    mailalias {'root':
    	  recipient => 'noc@emfcamp.org'
      }
    include superusers
}


node nocserver inherits default {
    include nocusers

    if $fqdn != 'jmp.emf.camp' {

        package { 'nfs-common':
             ensure => latest,
	     }

        mount { "/home":
    	  device  => "78.158.87.21:/home",
	  fstype  => "nfs",
	  ensure  => "mounted",
	  options => "soft,intr,bg",
	  atboot  => true,
	  require => Package["nfs-common"],
	  }
    }

}

node otherserver inherits default {
}

node 'pbx.emf.camp' inherits nocserver {
    
}

node 'puppet.emf.camp' inherits nocserver {
     
}

node 'content.emf.camp' inherits otherserver {
     
}

node 'phone.emf.camp' inherits otherserver {
     
}

node 'schedule.emf.camp' inherits otherserver {
     
}

node 'jmp.emf.camp' inherits nocserver {
     
}

node 'services1.emf.camp', 'services2.emf.camp' inherits nocserver {
     include unbound
     include nsd
     include ntpserver
}

node 'monitor1.emf.camp', 'monitor2.emf.camp' inherits nocserver {

}

node 'lights.emf.camp' inherits otherserver {
     
}


node 'radio.emf.camp' inherits otherserver {
     
}

node 'deadend.emf.camp' inherits nocserver {
     
}

