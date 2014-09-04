class manageusers::os-specific () {

  ##
  ## Older versions of Ubuntu require libshadow to manage the passwords
  ##
  if $operatingsystem =~ /Ubuntu|Debian/ and $lsbdistrelease <= 12.04 {
    package { "libshadow-ruby1.8":
      ensure => "installed"
    }
  }

  ##
  ## Redhat requires reby-shadow to manage passwords
  ##
  if $operatingsystem =~ /RedHat|CentOS/  {
    package { "ruby-shadow":
      ensure => "installed"
    }
  }

}
