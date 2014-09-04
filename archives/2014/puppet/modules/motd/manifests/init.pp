# /etc/puppet/modules/motd/manifests/init.pp

class motd {
      file {'motd':
            ensure  => file,
      	    path    => '/etc/motd',
	    mode    => 0644,
 	    content => "

  29th Aug 2014
       to             __,--'\\
  31st Aug 2014 __,--'    :. \\.
           _,--'              \\`.
          /|\\       `          \\ `.
         / | \\        `:        \\  `/
        / '|  \\        `:.       \\
       / , |   \\ www.emfcamp.org  \\
      /    |:   \\              `:. \\
     /| '  |     \\ :.           _,-'`.
   \\' |,  / \\   ` \\ `:.     _,-'_|    `/
      '._;   \\ .   \\   `_,-'_,-'
    \\'    `- .\\_   |\\,-'_,-'
                `--|_,`'             ${fqdn}
                                     ${operatingsystem} ${operatingsystemrelease} / ${processorcount} CPU / ${memorytotal} RAM

",

	}
}
