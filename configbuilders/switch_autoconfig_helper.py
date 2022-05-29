import os
import yaml


_TFTP_SERVER_RENDERERS = {}
_TFTP_FILE_RENDERERS = {}


def _tftp_server_renderer(provider_name):
    def decorator(fn):
        _TFTP_SERVER_RENDERERS[provider_name] = fn
        return fn
    return decorator


def _tftp_file_renderer(provider_name):
    def decorator(fn):
        _TFTP_FILE_RENDERERS[provider_name] = fn
        return fn
    return decorator


@_tftp_server_renderer("next-server")
@_tftp_server_renderer("siname")
def _tftp_siname(tftp_servers):
    return "next-server " + tftp_servers[0].hostname


@_tftp_server_renderer("option-66")
@_tftp_server_renderer("tftp-server-name")
def _tftp_option66(tftp_servers):
    return f'option tftp-server-name "{tftp_servers[0]["hostname"]}"'


@_tftp_server_renderer("option-150")
@_tftp_server_renderer("tftp-server-address")
def _tftp_option150(tftp_servers):
    return (
        "option tftp-server-address " +
        ', '.join(server['address'] for server in tftp_servers)
    )


@_tftp_file_renderer("option-67")
@_tftp_file_renderer("bootfile-name")
def _tftp_option67(filename):
    return f'option bootfile-name "{filename}"'


@_tftp_file_renderer("filename")
def _tftp_bootp_file(filename):
    return f'filename "{filename}"'


def render_tftp_server(method, tftp_servers):
    return _TFTP_SERVER_RENDERERS[method](tftp_servers)


def render_tftp_file(method, filename):
    passthrough_prefix = "PASSTHRU."
    if method.startswith(passthrough_prefix):
        option_name = method[len(passthrough_prefix):]
        return f'option {option_name} "{filename}"'
    else:
        return _TFTP_FILE_RENDERERS[method](filename)


class SwitchAutoconfigHelper:

    def __init__(self, configdict):
        self._config = configdict.copy()

    @classmethod
    def load(cls, yaml_input=None):
        """
        Load config from yaml_input.

        yaml_input, if given, can be any argument accepted by yaml.safe_load().
        If not given, "switch_autoconfig_params.yml" adjacent to this code file
        will be loaded.
        """
        if not yaml_input:
            file = os.path.join(
                os.path.dirname(__file__),
                "switch_autoconfig_params.yml"
            )
            with open(file, 'r') as fh:
                yaml_input = fh.read()
        return cls(yaml.safe_load(yaml_input))

    @property
    def scope(self):
        return self._config['scope']

    def network_info(self, section_name):
        return self._config['network'][section_name]

    def _manufacturer_section(self, manuf_slug):
        return self._config['switches'][manuf_slug]

    def for_manufacturer(self, manuf_slug):
        return self._manufacturer_section(manuf_slug).get('defaults', dict())

    def for_model(self, manuf_slug, model_slug):
        config = self.for_manufacturer(manuf_slug).copy()
        manuf_section = self._manufacturer_section(manuf_slug)
        if 'models' in manuf_section and manuf_section['models'] is not None:
            config.update(
                manuf_section['models'].get(model_slug, dict())
            )
        return config

    def for_device_tuple(self, manuf_slug, model_slug, device_name):
        config = self.for_model(manuf_slug, model_slug).copy()
        config.update(self.overrides_for_device_tuple(
            manuf_slug, model_slug, device_name
        ))
        return config

    def overrides_for_device_tuple(self, manuf_slug, model_slug, device_name):
        manuf_section = self._manufacturer_section(manuf_slug)
        ret = dict()
        if 'devices' in manuf_section and manuf_section['devices'] is not None:
            ret = manuf_section['devices'].get(device_name, dict())
        return ret

    def for_nbh_device(self, device):
        return self.for_device_tuple(
            device.device_type.manufacturer.slug,
            device.device_type.slug,
            device.name
        )

    def overrides_for_nbh_device(self, device):
        return self.overrides_for_device_tuple(
            device.device_type.manufacturer.slug,
            device.device_type.slug,
            device.name
        )
