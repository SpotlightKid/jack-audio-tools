#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  transporter.py
#
"""Query or change the JACK transport state."""

import argparse
import string
import sys

import jack


STATE_LABELS = {
    jack.ROLLING: "rolling",
    jack.STOPPED: "stopped",
    jack.STARTING: "starting",
    jack.NETSTARTING: "waiting for network sync",
}


def main(args=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        '-c', '--client-name',
        metavar='NAME',
        default='transporter',
        help="JACK client name (default: %(default)s)")
    ap.add_argument(
        'command',
        nargs='?',
        default='status',
        choices=['query', 'rewind', 'start', 'status', 'stop', 'toggle'],
        help="Transport command")

    args = ap.parse_args(args if args is not None else sys.argv[1:])

    try:
        client = jack.Client(args.client_name)
    except jack.JackError as exc:
        return "Could not create JACK client: %s" % exc

    state = client.transport_state
    result = 0

    if args.command == 'status':
        print("JACK transport is %s." % STATE_LABELS[state._code])
        result = 1 if state == jack.STOPPED else 0
    elif args.command == 'query':
        print("State: %s" % STATE_LABELS[state._code])
        info = client.transport_query()[1]

        for field in sorted(info):
            label = string.capwords(field.replace('_', ' '))
            print("%s: %s" % (label, info[field]))

        result = 1 if state == jack.STOPPED else 0
    elif args.command == 'start':
        if state == jack.STOPPED:
            client.transport_start()
    elif args.command == 'stop':
        if state != jack.STOPPED:
            client.transport_stop()
    elif args.command == 'toggle':
        if state == jack.STOPPED:
            client.transport_start()
        else:
            client.transport_stop()
    elif args.command == 'rewind':
        client.transport_frame = 0

    client.close()
    return result


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]) or 0)