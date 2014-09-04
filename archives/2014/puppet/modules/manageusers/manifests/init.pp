# == Class: manageusers
#
# Module to manage users, groups, and ssh keys
#
# === Authors
#
# Jason E. Murray <jemurray@zweck.net>
#
# === Copyright
#
# Copyright 2014 Jason E. Murray
#
class manageusers {

  ##
  ## Setup OS dependencies
  ##
  include manageusers::os-specific

  ##
  ## Accounts to create
  ##
  include manageusers::add_accounts

  ##
  ## Accounts to remove
  ##
  include manageusers::remove_accounts

}

