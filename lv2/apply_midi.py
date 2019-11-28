#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Send MIDI to the MIDI input of an LV2 plugin and print events it sends to its MIDI output."""

import argparse
import logging
import sys
from ctypes import (CFUNCTYPE, POINTER, byref, c_char_p, c_float, c_int32,
                    c_void_p, cast, pointer, sizeof)
from threading import Lock

import numpy as np

from . import lilv


log = logging.getLogger()

map_func_t = CFUNCTYPE(lilv.LV2_URID, lilv.LV2_URID_Map_Handle, c_char_p)
unmap_func_t = CFUNCTYPE(c_char_p, lilv.LV2_URID_Unmap_Handle, lilv.LV2_URID)


def get_plugin(world, plugin_uri):
    # Find plugin
    plugin_uri_node = world.new_uri(plugin_uri)
    plugins = world.get_all_plugins()

    return plugins[plugin_uri_node]


class URIDMapper:
    def __init__(self):
        self._next_id = 1
        self._map = {}
        self._rmap = {}
        self._lock = Lock()

    def uri_to_id(self, handle, uri):
        if isinstance(uri, lilv.Node):
            uri = str(uri).encode()

        try:
            urid = self._map[uri]
        except KeyError:
            with self._lock:
                urid = self._next_id
                self._map[uri] = urid
                self._rmap[urid] = uri
                self._next_id += 1

        return urid

    def id_to_uri(self, handle, urid):
        try:
            return self._rmap[urid]
        except KeyError:
            return 0


def make_options_feature(world):
    ns = world.ns
    urimap = lambda uri: world.urid_mapper.uri_to_id(None, uri)
    samplerate = c_int32(world.samplerate)
    blocksize = c_int32(world.blocksize)

    options = [
        lilv.LV2_Options_Option(lilv.LV2_OPTIONS_INSTANCE, 0,
                                urimap(ns.params.sampleRate), sizeof(c_float),
                                urimap(ns.atom.Float), cast(byref(samplerate), c_void_p)),
        lilv.LV2_Options_Option(lilv.LV2_OPTIONS_INSTANCE, 0,
                                urimap(ns.bufsz.nominalBlockLength), sizeof(c_int32),
                                urimap(ns.atom.Int), cast(byref(blocksize), c_void_p)),
        lilv.LV2_Options_Option(lilv.LV2_OPTIONS_INSTANCE, 0,
                                urimap(ns.bufsz.maxBlockLength), sizeof(c_int32),
                                urimap(ns.atom.Int), cast(byref(blocksize), c_void_p)),
        lilv.LV2_Options_Option(lilv.LV2_OPTIONS_INSTANCE, 0, 0, 0, 0, None)
    ]
    return lilv.LV2_Feature(str(ns.options.options).encode(),
                            cast((lilv.LV2_Options_Option * len(options))(*options), c_void_p))


def make_map_feature(world):
    ns = world.ns

    urid_map = lilv.LV2_URID_Map(lilv.LV2_URID_Map_Handle(), world.map_cfunc)
    urid_unmap = lilv.LV2_URID_Unmap(lilv.LV2_URID_Unmap_Handle(), world.unmap_cfunc)
    map_feature = lilv.LV2_Feature(str(ns.urid.map).encode(),
                                   cast(pointer(urid_map), c_void_p))
    unmap_feature = lilv.LV2_Feature(str(ns.urid.unmap).encode(),
                                     cast(pointer(urid_unmap), c_void_p))
    return map_feature, unmap_feaure


def instantiate_plugin(world, plugin):
    """Create instance of an LV2 plugin.

    :param world: lilv.World instance
    :param plugin: lilv.Plugin instance
    :return lilv.Instance: LV2 plugin instance

    """
    map_feature, unmap_feature = make_map_feature(world)
    options_feature = make_options(world)

    # Make array of pointers to LV2_Features, terminated by NULL pointer
    features = (POINTER(lilv.LV2_Feature) * 4)(
        pointer(map_feature),
        pointer(unmap_feature),
        pointer(options_feature),
        None
    )
    instance = lilv.Instance(plugin, world.samplerate, features)
    return instance


def run_plugin(world, plugin, data):
    """Function docstring.

    :param world: lilv.World instance
    :param plugin: lilv.Plugin instance
    :param data: bytes
    :return None

    """
    ns = world.ns
    blocksize = world.blocksize
    audio_input_buffers    = []
    audio_output_buffers   = []
    control_input_buffers  = []
    control_output_buffers = []
    instance = instantiate_plugin(world, plugin)

    for index in range(plugin.get_num_ports()):
        port = plugin.get_port_by_index(index)

        if port.is_a(ns.lv2.InputPort):
            if port.is_a(ns.lv2.AudioPort):
                audio_input_buffers.append(np.zeros(blocksize, np.float32))
                instance.connect_port(index, audio_input_buffers[-1])
            elif port.is_a(ns.lv2.ControlPort):
                default = float(port.get(ns.lv2.default))
                control_input_buffers.append(np.array([default], np.float32))
                instance.connect_port(index, control_input_buffers[-1])
            elif port.is_a(ns.atom.AtomPort):
                pass
            else:
                raise ValueError("Unhandled port type")
        elif port.is_a(ns.lv2.OutputPort):
            if port.is_a(ns.lv2.AudioPort):
                audio_output_buffers.append(np.zeros(blocksize, np.float32))
                instance.connect_port(index, audio_output_buffers[-1])
            elif port.is_a(ns.lv2.ControlPort):
                control_output_buffers.append(np.array([0], np.float32))
                instance.connect_port(index, control_output_buffers[-1])
            elif port.is_a(ns.atom.AtomPort):
                pass
            else:
                raise ValueError("Unhandled port type")

    # Run the plugin:
    instance.activate()

    period = 0
    while True:
        log.debug("Running period %i with block size %i", period, blocksize)

        for ch, buf in enumerate(audio_input_buffers):
            np.copyto(buf, data[ch][:blocksize])
            data[ch] = data[ch][blocksize:]

        instance.run(blocksize)
        period += 1

        if len(data[ch]) < blocksize:
            # XXX: temporary hack
            break

    instance.deactivate()

    for i, buf in enumerate(audio_output_buffers):
        log.debug("Audio output buffer %i: %r", i, buf)


def main(args=None):
    """Function docstring.

    :param args: command line arguments as a list of strings
    :return int: program exit code

    """
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('-d', '--debug', action="store_true",
                    help="Enable debug logging")
    ap.add_argument('-b', '--block-size', type=int, default="64",
                    help="Buffer size in samples per block (default: %(default)s)")
    ap.add_argument('-r', '--sample-rate', type=int, metavar="Hz", default="48000",
                    help="Sample rate in Hertz to run plugin at (default: %(default)s)")
    ap.add_argument('plugin_uri', metavar="URI",
                    help="LV2 plugin URI")
    args = ap.parse_args(args)

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format="%(levelname)s: %(message)s")

    # Initialise Lilv
    world = lilv.World()
    world.urid_mapper = URIDMapper()
    world.map_cfunc = map_func_t(world.urid_mapper.uri_to_id)
    world.unmap_cfunc = unmap_func_t(world.urid_mapper.id_to_uri)
    ns = world.ns
    ns.bufsz = lilv.Namespace(world, "http://lv2plug.in/ns/ext/buf-size#")
    ns.options = lilv.Namespace(world, "http://lv2plug.in/ns/ext/options#")
    ns.params = lilv.Namespace(world, "http://lv2plug.in/ns/ext/parameters#")
    ns.urid = lilv.Namespace(world, "http://lv2plug.in/ns/ext/urid#")
    world.samplerate = args.sample_rate
    world.blocksize = args.block_size

    world.load_all()

    try:
        plugin = get_plugin(world, args.plugin_uri)
    except KeyError:
        return "Plugin with URI '%s' not found." % args.plugin_uri

    log.debug("Found plugin: %s", plugin.get_name())
    n_audio_inputs = plugin.get_num_ports_of_class(ns.lv2.AudioPort, ns.lv2.InputPort)
    n_atom_inputs = plugin.get_num_ports_of_class(ns.atom.AtomPort, ns.lv2.InputPort)

    # ~ if n_atom_inputs < 1:
        # ~ return "Plugin has no MIDI input."

    try:
        run_plugin(world, plugin, [[.5] * 64])
    except Exception as exc:
        log.exception("Failed to run plugin '%s': %s", plugin.get_name(), exc)


if __name__ == '__main__':
    sys.exit(main() or 0)
