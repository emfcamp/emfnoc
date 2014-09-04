# /etc/puppet/modules/nsd/manifests/init.pp

class nsd {

    package { nsd3: ensure => latest }

    service { "nsd3":
    	    ensure  => "running",
	    enable  => "true",
	    require => Package["nsd3"],
	    status => 'pidfile=`nsd-checkconf -o pidfile /etc/nsd3/nsd.conf`; kill -0 `cat $pidfile`'
	    }

    file { "/etc/nsd3/nsd.conf":
        owner => 'root',
        group => 'root',
        mode  => '0444',
        source  => "puppet:///modules/nsd/nsd.conf",
        require => Package["nsd3"],
	notify => Service["nsd3"],
    }

    file { "/var/cache/nsd":
    	ensure => "directory",
    	owner  => "nsd",
    	group  => "nsd",
    	mode   => 755,
    }

    file { "/var/cache/nsd/slaves":
    	ensure => "directory",
    	owner  => "nsd",
    	group  => "nsd",
    	mode   => 755,
    }

}
