define add_user ( $email, $uid, $shell, $password ) {

            $username = $title

            user { $username:
                    comment => "$email",
                    home    => "/home/$username",
                    shell   => "$shell",
                    uid     => $uid,
                    password => "$password",
		    ensure => "present"
            }

            group { $username:
                    gid     => $uid,
                    require => user[$username]
            }

            file { "/home/$username/":
                    ensure  => directory,
                    owner   => $username,
                    group   => $username,
                    mode    => 750,
                    require => [ user[$username], group[$username] ]
            }

            file { "/home/$username/.ssh":
                    ensure  => directory,
                    owner   => $username,
                    group   => $username,
                    mode    => 700,
                    require => file["/home/$username/"]
            }

           # exec { "/narnia/tools/setuserpassword.sh $username":
           #         path            => "/bin:/usr/bin",
           #         refreshonly     => true,
           #         subscribe       => user[$username],
           #         unless          => "cat /etc/shadow | grep $username| cut -f 2 -d : | grep -v '!'"
           # }

            # now make sure that the ssh key authorized files is around
            file { "/home/$username/.ssh/authorized_keys":
                    ensure  => present,
                    owner   => $username,
                    group   => $username,
                    mode    => 600,
                    require => file["/home/$username/"]
            }
    }

define add_ssh_key( $key, $type ) {

            $username       = $title

            ssh_authorized_key{ "${username}_${key}":
                    ensure  => present,
                    key     => $key,
                    type    => $type,
                    user    => $username,
                    require => file["/home/$username/.ssh/authorized_keys"]

            }

    }
