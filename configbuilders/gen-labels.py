#!/usr/bin/env python
import argparse
import copy
import io
import os
import sys
import xml.etree.ElementTree as ET

import cairosvg
import click
import qrcode
import qrcode.image.svg
from PIL import Image
from brother_ql import BrotherQLRaster, create_label
from brother_ql.backends import backend_factory

from nbh import NetboxHelper

DOMAIN_SUFFIX = '.emf.camp'


def _find_etree_parent(search_root, search_element):
    for el in search_root:
        if el == search_element:
            return search_root
        else:
            found = _find_etree_parent(el, search_element)
            if found: return found

    return None


def get_etree_parent(svg, element):
    return _find_etree_parent(svg, element)


def get_qr_code(url):
    """ Generate a QR code SVG fragment from a URL.
        Return the result as an elementtree. """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=14,
        border=1,
    )
    qr.add_data(url)
    qr.make()
    img = qr.make_image(image_factory=qrcode.image.svg.SvgFragmentImage)
    bio = io.BytesIO()
    img.save(bio)
    return ET.fromstring(bio.getvalue())


def svg_from_template(path, vars, qr_code):
    nsmap = {
        'svg': 'http://www.w3.org/2000/svg'
    }

    with open(path, 'rb') as f:
        svg = ET.fromstring(f.read())

    elements = svg.findall('.//svg:tspan', namespaces=nsmap)
    for element in elements:
        for var, value in vars.items():
            if element.text and '[' + var + ']' in element.text:
                if type(value) == str and '\n' in value:
                    # multiline replacement
                    parent = get_etree_parent(svg, element)
                    linenum = 0
                    for line in value.split("\n"):
                        if linenum == 0:
                            # first line, just do a substitution
                            element.text = element.text.replace('[' + var + ']', str(line))
                        else:
                            # subsequent lines, clone the tspan and offset it downwards
                            new_element = copy.deepcopy(element)
                            new_element.text = line
                            new_element.attrib['y'] = str(
                                float(new_element.attrib['y']) + (
                                        linenum * 40))  # TODO figure out what the line height is somehow
                            parent.append(new_element)
                        linenum += 1

                else:
                    # Replacement within the same line
                    element.text = element.text.replace('[' + var + ']', str(value))

    qrg = svg.find('.//svg:g[@id="qr_code"]', namespaces=nsmap)
    if not qrg:
        print("qr_code element not found in template", file=sys.stderr)
        sys.exit(1)
    qr_svg = get_qr_code(qr_code)
    for el in qr_svg:
        qrg.append(el)

    return svg


def render_svg(svg, out_height=696):
    width = float(svg.get('width'))
    height = float(svg.get('height'))

    # Set the SVG document height to the correct pixel size
    # for the label printer. We're using continuous-width
    # labels so scale the width.

    # The SVG's internal coordinate system is maintained by
    # the viewBox attribute, so we don't need to scale every
    # coordinate in it, just the document size.
    out_width = width / height * out_height
    svg.set("width", "%spx" % out_width)
    svg.set("height", "%spx" % out_height)

    return cairosvg.svg2png(bytestring=ET.tostring(svg), background_color="#ffffff")


def generate(device):
    # Get all the interfaces for this device
    interfaces = helper.get_interfaces_for_device(device)
    interfaces = list(interfaces)  # make a copy since we'll need to iterate it repeatedly

    camper_vlan, port_map, vlan_map, links = get_interface_summary(device, interfaces)

    special_ports = ''

    for vlan_name in vlan_map:
        if '-' in vlan_name:
            pretty_vlan_name = vlan_name.split('-')[1]
        else:
            pretty_vlan_name = vlan_name
        port_sequences = port_map[vlan_map[vlan_name]]
        pretty_ports = pretty_port_sequence(port_sequences)

        if special_ports: special_ports += "\n"
        special_ports += '%s: %s' % (pretty_vlan_name, pretty_ports)

    if camper_vlan:
        pretty_camper_ports = pretty_port_sequence(port_map[camper_vlan])

        # Get the v4 and v6 prefixes for this camper-vlan

        prefixes = helper.netbox.ipam.prefixes.filter(vlan_vid=camper_vlan)
        camper_ipv4 = camper_ipv6 = None
        for prefix in prefixes:
            if (prefix.family.value == 4 and camper_ipv4) or prefix.family.value == 6 and camper_ipv6:
                print("Multiple camper prefixes for VLAN %d, help!" % camper_vlan, file=sys.stderr)
                sys.exit(1)
            if prefix.family.value == 4:
                camper_ipv4 = prefix.prefix
            elif prefix.family.value == 6:
                camper_ipv6 = prefix.prefix
    else:
        pretty_camper_ports = None
        camper_ipv4 = camper_ipv6 = None

    links_out = ''
    for link_switch, link_ports in links.items():
        if links_out: links_out += "\n"
        links_out += 'To %s: %s' % (link_switch, ','.join(link_ports))

    vars = {
        'SwitchName': device.name.replace(DOMAIN_SUFFIX, ''),
        'CamperVLAN': camper_vlan,
        'CamperIPv4': camper_ipv4,
        'CamperIPv6': camper_ipv6,
        'CamperPorts': pretty_camper_ports,
        'SwitchModel': device.device_type.model,
        'SwitchSerial': device.serial,
        'SwitchAsset': device.asset_tag,
        'Links': links_out,
        'Ports': special_ports
    }

    netbox_url = '%sdcim/devices/%d/' % (helper.config['url'], device.id)

    svg = svg_from_template('label-template.svg', vars, netbox_url)
    png = render_svg(svg)

    with open('out/labels/%s.svg' % device.name, 'wb') as f:
        f.write(ET.tostring(svg))
    with open('out/labels/%s.png' % device.name, 'wb') as f:
        f.write(png)

    return png


def short_interface(name):
    name = name.replace("TenGigabitEthernet", "Te")
    name = name.replace("GigabitEthernet", "Gi")
    name = name.replace("FastEthernet", "Fa")
    name = name.replace("Ethernet", "Eth")
    return name


def get_interface_summary(device, interfaces):
    # port_map, key: vlan_id, value: list of tuples with low and high interface numbers
    # e.g { 87: [(1,2), (23,24)] }
    port_map: dict[int, list[tuple[int, int]]] = {}
    # vlan_map: key: vlan_name, value: vlan_id
    vlan_map: dict[str, int] = {}
    # links: key: connected switch name, value: list of interfaces
    links = {}
    camper_vlan = None
    for interface in interfaces:
        if interface.mode and interface.mode.value == 'access' and interface.type.value != 'virtual':
            int_number = get_interface_shortnumber(interface.name)

            # Add this port's VLAN to the vlan_map and maybe set camper_vlan
            port_vid = interface.untagged_vlan.vid
            if interface.untagged_vlan.name.startswith("Camper-"):
                if camper_vlan is not None and camper_vlan != port_vid:
                    print("Multiple VLANs named Camper- on %s (%d and %d), I don't know what to do!" %
                          (device.name, camper_vlan, port_vid), file=sys.stderr)
                    sys.exit(1)
                camper_vlan = port_vid
            else:
                if port_vid not in vlan_map.values():
                    vlan_map[interface.untagged_vlan.name] = port_vid

            # Add this port to the vlan's port_map
            if port_vid not in port_map:
                port_map[port_vid] = [(int_number, int_number)]
            else:
                # if this number is adjacent to an existing tuple, adjust the tuple, e.g. adding port 4 to [(2, 3)],
                # we become [(2, 4)]

                added: bool = False
                for i in range(0, len(port_map[port_vid])):
                    if port_map[port_vid][i][0] == int_number + 1:
                        port_map[port_vid][i] = (int_number, port_map[port_vid][i][1])
                        added = True
                    if port_map[port_vid][i][1] == int_number - 1:
                        port_map[port_vid][i] = (port_map[port_vid][i][0], int_number)
                        added = True

                # We didn't add it to an existing tuple, so we need to make a new one
                if not added:
                    port_map[port_vid].append((int_number, int_number))

            # TODO Fix up any ranges that are now contiguous, e.g. [ (2,3), (4,5) ] becomes [(2,5)]
            # (may not be necessary if ports are always ordered)
        elif interface.type.value != 'virtual' and interface.connected_endpoint_reachable:
            connected_device_name = interface.connected_endpoint.device.name
            short_interface_name = short_interface(interface.name)
            if connected_device_name in links:
                links[connected_device_name].append(short_interface_name)
            else:
                links[connected_device_name] = [short_interface_name]

    return camper_vlan, port_map, vlan_map, links


def pretty_port_sequence(port_sequences):
    pretty_ports = ''
    for port_sequence in port_sequences:
        if pretty_ports: pretty_ports += ', '
        if port_sequence[0] == port_sequence[1]:
            pretty_ports += '%d' % port_sequence[0]
        else:
            pretty_ports += '%d-%d' % port_sequence
    return pretty_ports


def prepare_label(img):
    imgio = io.BytesIO(img)
    img = Image.open(imgio)
    qlr = BrotherQLRaster("QL-800")
    qlr.exception_on_warning = True
    create_label(qlr, img, '62', rotate='90')
    return qlr


def print_label(qlr):
    be = backend_factory('network')
    printer_url = 'tcp://192.168.0.17:9100'

    BrotherQLBackend = be['backend_class']
    printer = BrotherQLBackend(printer_url)

    printer.write(qlr.data)

    # be = backend_factory('pyusb')
    # list_available_devices = be['list_available_devices']
    # BrotherQLBackend = be['backend_class']
    # ad = list_available_devices()
    # pprint(ad)
    # if len(ad) == 0:
    #     print("No printer found", file=sys.stderr)
    #     sys.exit(0)
    # string_descr = ad[0]['identifier'].replace('_', '/')
    #
    # printer = BrotherQLBackend(string_descr)
    #
    # start = time.time()
    # printer.write(qlr.data)
    # printing_completed = False
    # waiting_to_receive = False
    # while time.time() - start < 10:
    #     data = printer.read()
    #     if not data:
    #         time.sleep(0.005)
    #         continue
    #     try:
    #         result = interpret_response(data)
    #     except ValueError:
    #         print("TIME %.3f - Couln't understand response: %s" % (time.time() - start, data), file=sys.stderr)
    #         continue
    #     print('TIME %.3f - result: %s' % (time.time() - start, result))
    #     if result['errors']:
    #         print('Errors occured: %s' % result['errors'])
    #     if result['status_type'] == 'Printing completed':
    #         printing_completed = True
    #     if result['status_type'] == 'Phase change' and result['phase_type'] == 'Waiting to receive':
    #         waiting_to_receive = True
    #     if printing_completed and waiting_to_receive:
    #         break
    # if not (printing_completed and waiting_to_receive):
    #     print('Printing potentially not successful?', file=sys.stderr)


def get_interface_shortnumber(interface_name):
    # the last string of numbers are the number we need: gi0/0/23 -> 23
    int_number = 0
    for pos in range(len(interface_name) - 1, -1, -1):
        if interface_name[pos].isnumeric():
            int_number = int(interface_name[pos:])
        else:
            break
    # print("%s -> %d" % (interface_name, int_number))
    return int_number


if __name__ == "__main__":

    helper = NetboxHelper.getInstance()

    parser = argparse.ArgumentParser(description='Generate and optionally print device labels.')
    parser.add_argument('devices', metavar='DEVICE', type=str, nargs='*',
                        help='devices to generate labels for')
    parser.add_argument('--all', '-a', action='store_true',
                        help='generate for all devices')
    parser.add_argument('--print', '-p', action='store_true',
                        help='print each label after generating it')

    args = parser.parse_args()

    if not args.all and len(args.devices) == 0:
        print("Specify the device to generate or use --all", file=sys.stderr)
        sys.exit(1)

    if args.all and len(args.devices) > 0:
        print("Cannot specify a list of devices when using --all", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists('out'):
        os.mkdir('out')

    if not os.path.exists('out/labels'):
        os.mkdir('out/labels')

    if args.all:
        devices = helper.netbox.dcim.devices.all()  # TODO filter on switches
        devices = list(devices)
        with click.progressbar(devices, label='Labels',
                               item_show_func=lambda item: item.name if item is not None else 'Unknown') as bar:
            for device in bar:
                if 'switch' in device.device_role.slug:
                    generate(device)
    else:
        with click.progressbar(args.devices, label='Labels',
                               item_show_func=lambda item: item) as bar:
            for devicename in bar:

                device = helper.netbox.dcim.devices.get(name=devicename)
                if device is None:
                    device = helper.netbox.dcim.devices.get(name=devicename + DOMAIN_SUFFIX)
                if device is None:
                    print("No device named %s could be found" % devicename, file=sys.stderr)
                    sys.exit(1)

                png = generate(device)
                if args.print:
                    print_label(prepare_label(png))
