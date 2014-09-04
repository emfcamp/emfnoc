class manageusers::remove_accounts() {

  ##
  ## Accounts that should be removed
  ##
  user { user3:
    ensure => "absent"
  }

  user { user4:
    ensure => "absent"
  }

  user { user7:
    ensure => "absent"
  }


}
