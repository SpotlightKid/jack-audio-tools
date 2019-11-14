#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""List all presets of an LV2 plugin with the given URI."""

import sys
import lilv


NS_PRESETS = 'http://lv2plug.in/ns/ext/presets#'


def print_presets(world, plugin):
    presets = plugin.get_related(world.ns.presets.Preset)
    preset_list = []

    for preset in presets:
        world.load_resource(preset)
        labels = world.find_nodes(preset, world.ns.rdfs.label, None)

        if labels:
            label = str(labels[0])
        else:
            label = None
            print("Preset '%s' has no rdfs:label" % preset, file=sys.stderr)

        preset_list.append((label, str(preset)))

    for label, preset_uri in sorted(preset_list, key=lambda x: x[0] or ''):
        print("Label: %s" % label or "")
        print("URI: %s\n" % preset_uri)


def main(args=None):
    args = sys.argv[1:] if args is None else args

    if args:
        uri = args[0]
    else:
        return "Usage: lv2_list_plugin_presets <plugin URI>"

    world = lilv.World()
    world.load_all()
    world.ns.presets = lilv.Namespace(world, NS_PRESETS)
    plugins = world.get_all_plugins()

    try:
        plugin = plugins[uri]
    except KeyError as exc:
        return "error: no plugin with URI '%s' found." % uri
    except ValueError as exc:
        return "error: %s" % exc

    print_presets(world, plugin)


if __name__ == '__main__':
    sys.exit(main() or 0)
