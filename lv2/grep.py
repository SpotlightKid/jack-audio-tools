#!/usr/bin/env python
"""Print URIs of all installed LV2 plugins matching given regular expression.
"""

import argparse
import json
import re
import sys

import lilv


def main(args=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('-c', '--categories', action="store_true",
                    help="Add list of categories for each plugin (requires -j)")
    ap.add_argument('-i', '--ignore-case', action="store_true",
                    help="Ignore case")
    ap.add_argument('-j', '--json', action="store_true",
                    help="Print output as list of objects in JSON format")
    ap.add_argument('-p', '--pretty', action="store_true",
                    help="Pretty format JSON output with indentation and linebreaks")
    ap.add_argument('pattern', nargs='?', help="LV2 plugin URI pattern")
    args = ap.parse_args(args)

    if args.pattern:
        rx = re.compile(args.pattern, re.I if args.ignore_case else 0)

    world = lilv.World()
    world.load_all()

    results = []
    for node in world.get_all_plugins():
        uri = str(node.get_uri())

        if not args.pattern or rx.search(uri):
            if args.json:
                # load all resources in bundle
                world.load_resource(uri)
                name = node.get_name()
                plugin_data = {
                    'name': str(name) if name is not None else None,
                    'uri': uri
                }

                if args.categories:
                    categories = []

                    for cat in node.get_value(world.ns.rdf.type):
                        cat = str(cat)
                        if not cat.endswith('#Plugin'):
                            categories.append(str(cat).split('#', 1)[-1])

                    plugin_data['categories'] = categories

                results.append(plugin_data)
            else:
                print(uri)

    if args.json:
        json.dump(results, sys.stdout, indent=2 if args.pretty else None)


if __name__ == '__main__':
    sys.exit(main() or 0)
