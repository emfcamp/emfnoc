#!/usr/bin/env python
"""
EMF2022 dhcpd config generator
"""

import logging

from emfnoc import EmfNoc
from nbh import NetboxHelper

from dhcp_generator import DhcpGenerator


def main():
    logging.basicConfig()
    helper = NetboxHelper.getInstance()
    config = EmfNoc.load_config()

    generator = DhcpGenerator(config, helper, "out")
    generator.render_subnets()
    generator.render_switch_autoconfig()


if __name__ == '__main__':
    main()
