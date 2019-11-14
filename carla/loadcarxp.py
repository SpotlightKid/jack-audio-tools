#!/usr/bin/env python

import argparse
import ast
import logging
import sys
import xml.etree.ElementTree as ET
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, List


log = logging.getLogger(__name__)
NS_CARLA = 'http://kxstudio.sf.net/ns/carla'


class ParseError(ValueError):
    pass


def is_bool(s):
    if isinstance(s, str):
        return s.strip().lower() in ('1', 'on', 'true', 'y', 'yes')

    return bool(s)


def elem_text(elem):
    if elem is not None:
        return elem.text.strip()
    return None


@dataclass
class Param:
    index: int
    name: str
    symbol: str
    value: float
    midi_cc: int = -1
    midi_channel: int = -1


@dataclass
class Property:
    type: str
    key: int
    value: str


@dataclass
class PluginInstance:
    index: int
    name: str
    uri: str
    type: str = 'LV2'
    active: bool = True
    params: List[Param] = field(default_factory=list)
    properties: Dict = field(default_factory=dict)


@dataclass
class CarlaProject:
    plugins: OrderedDict = field(default_factory=OrderedDict)
    connections: List[tuple] = field(default_factory=list)


def parse_carxp(filename, ignore_carla_properties=False):
    try:
        tree = ET.parse(filename)
    except ET.ParseError as exc:
        raise ParseError(str(exc))

    root = tree.getroot()

    if root.tag != 'CARLA-PROJECT':
        raise ParseError("Not a Carla project file: %s" % filename)

    plugins = OrderedDict()

    for index, pnode in enumerate(root.findall("./Plugin")):
        type = elem_text(pnode.find('./Info/Type'))
        name = elem_text(pnode.find('./Info/Name'))

        if type != 'LV2':
            log.warning("Plugin type '%s' not supported.", type)
            log.info("Skipping plugin '%s'.", name)
            continue

        plugin = PluginInstance(
            index=index,
            name=name,
            uri=elem_text(pnode.find('./Info/URI')),
            type=type,
            active=is_bool(elem_text(pnode.find('./Data/Active')))
        )

        for paramnode in pnode.findall('./Data/Parameter'):
            midi_cc = paramnode.find('MidiCC')
            midi_channel = paramnode.find('MidiChannel')
            value = elem_text(paramnode.find('Value'))

            if value:
                value = ast.literal_eval(value)

            plugin.params.append(
                Param(
                    index=int(elem_text(paramnode.find('Index'))),
                    name=elem_text(paramnode.find('Name')),
                    symbol=elem_text(paramnode.find('Symbol')),
                    value=value,
                    midi_cc=int(midi_cc.text) if midi_cc is not None else -1,
                    midi_channel=int(midi_channel.text) if midi_channel is not None else -1
                )
            )

        for propnode in pnode.findall('./Data/CustomData'):
            type = elem_text(propnode.find('Type'))

            if ignore_carla_properties and type.startswith(NS_CARLA):
                continue

            key = propnode.find('Key').text.strip()
            plugin.properties[key] = Property(
                type=type,
                key=key,
                value=elem_text(propnode.find('Value'))
            )

        plugins[plugin.name] = plugin

    connections = []
    for cnode in root.findall('./ExternalPatchbay/Connection'):
        connections.append((
            elem_text(cnode.find('Source')),
            elem_text(cnode.find('Target')),
        ))

    return CarlaProject(plugins, connections)


def main(args=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('-d', '--debug', action='store_true',
                    help="Enable debug log messages")
    ap.add_argument('carla_project',
                    help="Carla project file (*.carxp)")
    args = ap.parse_args(args)

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    try:
        project = parse_carxp(args.carla_project)
    except ParseError as exc:
        return str(exc)

    for plugin in project.plugins.values():
        print(plugin)
        print()

    for src, dst in project.connections:
        print("%s -> %s" % (src, dst))


if __name__ == '__main__':
    sys.exit(main() or 0)
