#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""List all preset URIs of an LV2 plugin with the given URI."""

import sys
import lilv


PRESET_NS = 'http://lv2plug.in/ns/ext/presets'
RDFS_NS = 'http://www.w3.org/2000/01/rdf-schema'


def main(args=None):
    if args:
        plugin_uri = args[0]
    else:
        plugin_uri = 'http://kunz.corrupt.ch/products/tal-noisemaker'

    world = lilv.World()
    world.load_all()
    preset_ns = lilv.Namespace(world, PRESET_NS)
    rdfs_ns = lilv.Namespace(world, RDFS_NS)
    plugins = world.get_all_plugins()
    plugin_uri = world.new_uri(plugin_uri)

    if plugin_uri is None or plugin_uri not in plugins:
        return "Plugin with URI '%s' not found" % plugin_uri

    plugin = plugins[plugin_uri]
    presets = plugin.get_related(getattr(preset_ns, '#Preset'))

    preset_list = []

    for preset in presets:
        res = world.load_resource(preset)
        labels = world.find_nodes(preset, getattr(rdfs_ns, '#label'), None)

        if labels:
            label = str(labels[0])
        else:
            label = str(preset)
            print("Preset '&s' has no rdfs:label" % preset, file=sys.stderr)

        preset_list.append((label, str(preset)))

    for preset in sorted(preset_list):
        print("%s: %s" % preset)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]) or 0)