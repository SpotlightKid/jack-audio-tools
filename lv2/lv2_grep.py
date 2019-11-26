#!/usr/bin/env python
"""
Print URIs of all installed LV2 plugins matching the given regular expression.
"""

import argparse
import re
import sys

import lilv


def main(args=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('-i', '--ignore-case', action="store_true",
                    help="Ignore case")
    ap.add_argument('pattern', help="LV2 plugin URI pattern")

    args = ap.parse_args(args)
    rx = re.compile(args.pattern, re.I if args.ignore_case else 0)
    world = lilv.World()
    world.load_all()

    for node in world.get_all_plugins():
        uri = str(node.get_uri())

        if rx.search(uri):
            print(uri)


if __name__ == '__main__':
    sys.exit(main() or 0)
