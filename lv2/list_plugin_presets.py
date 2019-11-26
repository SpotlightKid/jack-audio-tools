#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""List all presets of an LV2 plugin with the given URI."""

import sys
import lilv


NS_PRESETS = 'http://lv2plug.in/ns/ext/presets#'


def get_presets(world, plugin):
    ns_presets = lilv.Namespace(world, NS_PRESETS)
    presets = plugin.get_related(ns_presets.Preset)
    preset_list = []

    for preset in presets:
        world.load_resource(preset)
        labels = world.find_nodes(preset, world.ns.rdfs.label, None)

        if labels:
            label = str(labels[0])
        else:
            label = None

        preset_list.append((label, str(preset)))

    return preset_list


def main(args=None):
    args = sys.argv[1:] if args is None else args

    if args:
        uri = args[0]
    else:
        return "Usage: lv2_list_plugin_presets <plugin URI>"

    world = lilv.World()
    world.load_all()
    plugins = world.get_all_plugins()

    try:
        plugin = plugins[uri]
    except KeyError as exc:
        return "error: no plugin with URI '%s' found." % uri
    except ValueError as exc:
        return "error: %s" % exc

    presets = get_presets(world, plugin)
    for label, preset_uri in sorted(presets, key=lambda x: x[0] or ''):
        if label is None:
            print("Preset '%s' has no rdfs:label" % preset, file=sys.stderr)

        print("Label: %s" % label or "")
        print("URI: %s\n" % preset_uri)


if __name__ == '__main__':
    sys.exit(main() or 0)
