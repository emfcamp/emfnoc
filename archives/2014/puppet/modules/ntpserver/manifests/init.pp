# /etc/puppet/modules/ntp/manifests/init.pp

class ntpserver {

    package { ntp: ensure => latest }

    service { "ntp":
    	    ensure  => "running",
	    enable  => "true",
	    require => Package["ntp"]
	    }

    file { "/etc/ntp.conf":
        owner => 'root',
        group => 'root',
        mode  => '0444',
        source  => "puppet:///modules/ntpserver/ntp.conf",
        require => Package["ntp"],
	notify => Service["ntp"],
    }
}
