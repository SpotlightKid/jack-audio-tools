#!/usr/bin/env python
"""Export plugin settings from a Carla project file (.carxp) as LV2 preset bundles."""

import argparse
import logging
import os
import re
import shutil
import sys
from os.path import basename, exists, expanduser, isabs, isdir, isfile, join, splitext

import rdflib
from rdflib import Graph, Literal, BNode, URIRef
from rdflib.namespace import Namespace, NamespaceManager, RDF, RDFS, XSD

from .loadcarxp import parse_carxp


log = logging.getLogger('lv2preset')


class NS:
    atom = rdflib.Namespace('http://lv2plug.in/ns/ext/atom#')
    lv2 = rdflib.Namespace('http://lv2plug.in/ns/lv2core#')
    patch = rdflib.Namespace('http://lv2plug.in/ns/ext/patch#')
    pset = rdflib.Namespace('http://lv2plug.in/ns/ext/presets#')
    state = rdflib.Namespace('http://lv2plug.in/ns/ext/state#')

    @classmethod
    def bind_all(cls, nsmanager):
        for name in dir(cls):
            ns = getattr(cls, name)
            if isinstance(ns, rdflib.Namespace):
                nsmanager.bind(name, ns, override=True, replace=True)


def safe_name(name):
    return "".join(c if re.match(r'\w', c) else '_' for c in name)


def get_graph():
    graph = Graph()
    NS.bind_all(NamespaceManager(graph))
    return graph


def create_lv2_preset(label, plugin):
    graph = get_graph()
    preset = URIRef('')
    graph.add((preset, RDF.type, NS.pset.Preset))
    graph.add((preset, NS.lv2.appliesTo, URIRef(plugin.uri)))
    graph.add((preset, RDFS.label, Literal(label)))

    for param in plugin.params:
        port = BNode()
        graph.add((port, NS.lv2.symbol, Literal(param.symbol)))
        graph.add((port, NS.pset.value, Literal(param.value)))
        graph.add((preset, NS.lv2.port, port))

    if plugin.properties:
        state = BNode()

        for prop in plugin.properties.values():
            if prop.type == str(NS.atom.Path):
                value = URIRef(prop.value)
            else:
                # XXX: handle other Atom types?
                value = Literal(prop.value)

            graph.add((state, URIRef(prop.key), value))

        graph.add((preset, NS.state.state, state))

    return graph.serialize(format='turtle').decode()


def create_manifest(uri, filename):
    graph = get_graph()
    preset = URIRef(filename)
    graph.add((preset, RDF.type, NS.pset.Preset))
    graph.add((preset, NS.lv2.appliesTo, URIRef(uri)))
    graph.add((preset, RDFS.seeAlso, URIRef(filename)))

    return graph.serialize(format='turtle').decode()


def link_or_copy_path(path, dst, always_copy=False):
    if exists(path):
        success = False

        if not always_copy:
            try:
                os.symlink(path, dst)
            except OSError as exc:
                log.warning("Could not symlink '%s' to LV2 bundle: %s", path, exc)
            else:
                path = basename(dst)
                success = True

        if (not success or always_copy) and isfile(path):
            try:
                shutil.copy2(path, dst)
            except (OSError, IOError) as exc:
                log.warning("Could not copy '%s' to LV2 bundle: %s", path, exc)
            else:
                path = basename(dst)
    else:
        log.warning("Path '%s' does not exist locally. The preset might not restore the full "
                    "state of the plugin.", path)

    return path


def main(args=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('-d', '--debug', action='store_true',
                    help="Enable debug log messages")
    ap.add_argument('-l', '--label',
                    help="Label of LV2 preset(s)")
    ap.add_argument('-b', '--base-dir', default=expanduser('~'),
                    help="Base directory to prepend to relative file paths referenced by plugins "
                         "(default: %(default)s)")
    ap.add_argument('-c', '--copy-files', action='store_true',
                    help="Always copy referenced files to LV2 bundle instead of sym-linking them")
    ap.add_argument('-o', '--output-dir', default=expanduser('~/.lv2'),
                    help="Output directory (default: %(default)s)")
    ap.add_argument('carlaproject',
                    help="Carla project file (.carxp)")
    ap.add_argument('plugin_uris', nargs='*', metavar="URI",
                    help="Only write presets for plugins with given URIs")

    args = ap.parse_args(args)

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format="%(levelname)s: %(message)s")

    project = parse_carxp(args.carlaproject, ignore_carla_properties=True)

    for plugin in project.plugins.values():
        if args.plugin_uris and plugin.uri not in args.plugin_uris:
            continue

        if not plugin.params and not plugin.properties:
            continue

        if args.label:
            label = args.label
        else:
            label = splitext(basename(args.carlaproject))[0].replace('_', ' ')

        bundle_name = "%s_%s.preset.lv2" % (safe_name(plugin.name), safe_name(label))
        bundle_path = join(args.output_dir, bundle_name)
        ttl_name = "%s.ttl" % (safe_name(label),)
        ttl_path = join(bundle_path, ttl_name)
        manifest_path = join(bundle_path, 'manifest.ttl')

        if not isdir(args.output_dir):
            os.mkdir(args.output_dir)

        if exists(bundle_path):
            log.error("Preset LV2 bundle directory '%s' already exists and will not be "
                      "overwritten.", bundle_path)
            continue

        os.mkdir(bundle_path)

        for prop in plugin.properties.values():
            if prop.type == str(NS.atom.Path):
                path = prop.value

                if not isabs(path):
                    path = join(args.base_dir, path)

                prop.value = link_or_copy_path(path, join(bundle_path, basename(path)),
                                               always_copy=args.copy_files)

        with open(manifest_path, 'w') as manifest:
            manifest.write(create_manifest(plugin.uri, ttl_name))

        with open(ttl_path, 'w') as ttl:
            ttl.write(create_lv2_preset(label, plugin))

        log.info("Created preset bundle '%s'.", bundle_path)


if __name__ == '__main__':
    sys.exit(main() or 0)
