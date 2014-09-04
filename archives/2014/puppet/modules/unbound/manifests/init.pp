# /etc/puppet/modules/unbound/manifests/init.pp

class unbound {

    package { unbound: ensure => latest }

    service { "unbound":
    	    ensure  => "running",
	    enable  => "true",
	    require => Package["unbound"],
	    status => 'service unbound status | grep "unbound is running"'
	    }

    file { "/etc/unbound/unbound.conf":
        owner => 'root',
        group => 'root',
        mode  => '0440',
        source  => "puppet:///modules/unbound/unbound.conf",
        require => Package["unbound"],
	notify => Service["unbound"],
    }
}
