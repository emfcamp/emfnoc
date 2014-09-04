# /etc/puppet/modules/emfresolvers/manifests/init.pp

class emfresolvers {

    file { "/etc/resolv.conf":
        owner => 'root',
        group => 'root',
        mode  => '0444',
        source  => "puppet:///modules/emfresolvers/resolv.conf",
    }
}
