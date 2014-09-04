# /etc/puppet/modules/sudo/manifests/init.pp

class sudo {

    package { sudo: ensure => latest }


    file { "/etc/sudoers":
        owner => 'root',
        group => 'root',
        mode  => '0440',
        source  => "puppet:///modules/sudo/sudoers",
        require => Package["sudo"],
    }
}
