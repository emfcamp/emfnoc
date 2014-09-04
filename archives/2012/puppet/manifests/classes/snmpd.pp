
class snmpd {

	$snmpacl = ['195.177.253.40', '195.177.253.110', '195.177.253.111', '195.177.253.113', '94.45.224.11', '94.45.224.12']
	$community = 'emf'

	#
	# different locations for bsmk / ppmk / the (?)
	#
	if '.bsmk.' in $::fqdn {
		$location = 'Blue Square Milton Keynes'
	} elsif '.thdo.' in $::fqdn {
		$location = 'Telehouse Docklands'
	} else {
		$location = 'Pineham Park'
	}

	package {'snmpd':
		ensure  => present,
		before => File['/etc/snmp/snmpd.conf'],
	}

	file {'/etc/default/snmpd':
		require => Package['snmpd'],
		ensure => file,
		mode => 0644,
		owner => 'root',
		group => 'root',
		source => "puppet:///files/snmpd"
	}

	file {'/etc/snmp/snmpd.conf':
		require => Package['snmpd'],
		ensure => file,
		mode => 0640,
		owner => 'root',
		group => 'root',
		content => template("snmpd/snmpd.conf.erb"),
		alias => snmpconf,
	}


	service { 'snmpd':
		ensure => running,
		enable => true,
		hasrestart => true,
		hasstatus  => false, # dosn't work if true since we don't run snmptrapd.
		subscribe  => [File['/etc/snmp/snmpd.conf'],File['/etc/default/snmpd']],
	}
}
