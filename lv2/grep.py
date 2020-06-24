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
    ap.add_argument('-i', '--ignore-case', action="store_true",
                    help="Ignore case")
    ap.add_argument('-j', '--json', action="store_true",
                    help="Print output as list of objects in JSON format")
    ap.add_argument('pattern', help="LV2 plugin URI pattern")

    args = ap.parse_args(args)
    rx = re.compile(args.pattern, re.I if args.ignore_case else 0)
    world = lilv.World()
    world.load_all()

    results = []
    for node in world.get_all_plugins():
        uri = str(node.get_uri())

        if rx.search(uri):
            if args.json:
                # load all resources in bundle
                world.load_resource(uri)
                name = node.get_name()
                results.append({'name': str(name) if name is not None else None, 'uri': uri})
            else:
                print(uri)

    if args.json:
        json.dump(results, sys.stdout, indent=2)


if __name__ == '__main__':
    sys.exit(main() or 0)
