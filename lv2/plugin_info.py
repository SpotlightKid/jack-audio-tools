#!/usr/bin/env python
"""Generate JSON document with information about a single or all installed LV2 plugins."""

import os
from math import fmod
from os.path import dirname

import lilv


NS_MOD = "http://moddevices.com/ns/mod#"
NS_PATCH = 'http://lv2plug.in/ns/ext/patch#'
NS_PORT_PROPERTIES = "http://lv2plug.in/ns/ext/port-props#"
NS_PRESET = 'http://lv2plug.in/ns/ext/presets#'
NS_UNITS = "http://lv2plug.in/ns/extensions/units#"

LV2_CATEGORIES = {
    'AllpassPlugin': ('Filter', 'Allpass'),
    'AmplifierPlugin': ('Dynamics', 'Amplifier'),
    'AnalyserPlugin': ('Utility', 'Analyser'),
    'BandpassPlugin': ('Filter', 'Bandpass'),
    'ChorusPlugin': ('Modulator', 'Chorus'),
    'CombPlugin': ('Filter', 'Comb'),
    'CompressorPlugin': ('Dynamics', 'Compressor'),
    'ConstantPlugin': ('Generator', 'Constant'),
    'ConverterPlugin': ('Utility', 'Converter'),
    'DelayPlugin': ('Delay',),
    'DistortionPlugin': ('Distortion',),
    'DynamicsPlugin': ('Dynamics',),
    'EQPlugin': ('Filter', 'Equaliser'),
    'ExpanderPlugin': ('Dynamics', 'Expander'),
    'FilterPlugin': ('Filter',),
    'FlangerPlugin': ('Modulator', 'Flanger'),
    'FunctionPlugin': ('Utility', 'Function'),
    'GatePlugin': ('Dynamics', 'Gate'),
    'GeneratorPlugin': ('Generator',),
    'HighpassPlugin': ('Filter', 'Highpass'),
    'InstrumentPlugin': ('Generator', 'Instrument'),
    'LimiterPlugin': ('Dynamics', 'Limiter'),
    'LowpassPlugin': ('Filter', 'Lowpass'),
    'MIDIPlugin': ('MIDI', 'Utility'),
    'MixerPlugin': ('Utility', 'Mixer'),
    'ModulatorPlugin': ('Modulator',),
    'MultiEQPlugin': ('Filter', 'Equaliser', 'Multiband'),
    'OscillatorPlugin': ('Generator', 'Oscillator'),
    'ParaEQPlugin': ('Filter', 'Equaliser', 'Parametric'),
    'PhaserPlugin': ('Modulator', 'Phaser'),
    'PitchPlugin': ('Spectral', 'Pitch Shifter'),
    'ReverbPlugin': ('Reverb',),
    'SimulatorPlugin': ('Simulator',),
    'SpatialPlugin': ('Spatial',),
    'SpectralPlugin': ('Spectral',),
    'UtilityPlugin': ('Utility',),
    'WaveshaperPlugin': ('Distortion', 'Waveshaper'),
}

LV2_UNITS = units = {
    'bar': ("bars", "%f bars", "bars"),
    'beat': ("beats", "%f beats", "beats"),
    'bpm': ("beats per minute", "%f BPM", "BPM"),
    'cent': ("cents", "%f ct", "ct"),
    'cm': ("centimetres", "%f cm", "cm"),
    'coef': ("coefficient", "* %f", "*"),
    'db': ("decibels", "%f dB", "dB"),
    'degree': ("degrees", "%f deg", "deg"),
    'frame': ("audio frames", "%f frames", "frames"),
    'hz': ("hertz", "%f Hz", "Hz"),
    'inch': ("inches", """%f\"""", "in"),
    'khz': ("kilohertz", "%f kHz", "kHz"),
    'km': ("kilometres", "%f km", "km"),
    'mhz': ("megahertz", "%f MHz", "MHz"),
    'midiNote': ("MIDI note", "MIDI note %d", "note"),
    'mile': ("miles", "%f mi", "mi"),
    'min': ("minutes", "%f mins", "min"),
    'm': ("metres", "%f m", "m"),
    'mm': ("millimetres", "%f mm", "mm"),
    'ms': ("milliseconds", "%f ms", "ms"),
    'oct': ("octaves", "%f octaves", "oct"),
    'pc': ("percent", "%f%%", "%"),
    'semitone12TET': ("semitones", "%f semi", "semi"),
    's': ("seconds", "%f s", "s"),
}


def node2str(node, strip=True):
    """Return lilv.Node to string.

    By default, strips whitespace surrounding string value.

    If passed node is None, return None.

    """
    if node is not None:
        node = str(node)

        if strip:
            node = node.strip()

    return node


def getfirst(obj, uri, strip=True):
    """Return string value of first item returned by obj.get_value(uri).

    By default, strips whitespace surrounding string value.

    If collection is empty, return None.

    """
    data = obj.get_value(uri)

    if data:
        data = str(data[0])

        if strip:
            data = data.strip()

        return data
    else:
        return None


def _get_port_info(ctx, port):
    world = ctx.world
    warnings = ctx.warnings
    errors = ctx.errors
    portnames = ctx.portnames
    portsymbols = ctx.portsymbols

    # base data
    portname = port.get_name()

    if portname is None:
        portname = "_%i" % index
        errors.append("port with index %i has no name" % index)
    else:
        portname = str(portname)

    portsymbol = port.get_symbol()

    if portsymbol is None:
        portsymbol = "_%i" % index
        errors.append("port with index %i has no symbol" % index)
    else:
        portsymbol = str(portsymbol)

    # check for duplicate names
    if portname in portsymbols:
        warnings.append("port name '%s' is not unique" % portname)
    else:
        portnames.add(portname)

    # check for duplicate symbols
    if portsymbol in portsymbols:
        errors.append("port symbol '%s' is not unique" % portsymbol)
    else:
        portsymbols.add(portsymbol)

    # short name
    psname = getfirst(port, world.ns.lv2.shortName)

    if psname is None:
        psname = portname[:16]
    elif len(psname) > 16:
        errors.append("port '%s' short name has more than 16 characters" % portname)

    # check for old style shortName
    if port.get_value(world.ns.lv2.shortname):
        errors.append("port '%s' short name is using old style 'shortname' instead of 'shortName'" % portname)

    # port types
    types = [str(t).rsplit("#", 1)[-1][:-4] for t in port.get_value(world.ns.rdf.type)]
    buffer_type = port.get_value(world.ns.atom.bufferType)

    if ("Atom" in types and port.supports_event(world.ns.midi.MidiEvent) and buffer_type
            and str(buffer_type[0]) == world.ns.atom.Sequence):
        types.append("MIDI")

    # port comment
    pcomment = getfirst(port, world.ns.rdfs.comment)

    # port designation
    designation = getfirst(port, world.ns.lv2.designation)

    # port rangeSteps
    rangesteps = getfirst(port, world.ns.mod.rangeSteps) or getfirst(port, world.ns.pprops.rangeSteps)

    # port properties
    properties = sorted([str(t).rsplit("#", 1)[-1] for t in port.get_value(world.ns.lv2.portProperty)])

    # data
    ranges = {}
    scalepoints = []

    # control and cv must contain ranges, might contain scale points
    if "Control" in types or "CV" in types:
        is_int = "integer" in properties

        if is_int and "CV" in types:
            errors.append("port '%s' has integer property and CV type" % portname)

        xdefault, xminimum, xmaximum = port.get_range()

        if xminimum is not None and xmaximum is not None:
            if is_int:
                if xminimum.is_int():
                    ranges['minimum'] = int(xminimum)
                else:
                    ranges['minimum'] = float(xminimum)
                    if fmod(ranges['minimum'], 1.0) == 0.0:
                        warnings.append("port '%s' has integer property but minimum value is float" % portname)
                    else:
                        errors.append("port '%s' has integer property but minimum value has non-zero decimals" % portname)

                    ranges['minimum'] = int(ranges['minimum'])

                if xmaximum.is_int():
                    ranges['maximum'] = int(xmaximum)
                else:
                    ranges['maximum'] = float(xmaximum)
                    if fmod(ranges['maximum'], 1.0) == 0.0:
                        warnings.append("port '%s' has integer property but maximum value is float" % portname)
                    else:
                        errors.append("port '%s' has integer property but maximum value has non-zero decimals" % portname)

                    ranges['maximum'] = int(ranges['maximum'])

            else:
                if xminimum.is_int():
                    warnings.append("port '%s' minimum value is an integer" % portname)
                    ranges['minimum'] = int(xminimum) * 1.0
                else:
                    ranges['minimum'] = float(xminimum)

                if xmaximum.is_int():
                    warnings.append("port '%s' maximum value is an integer" % portname)
                    ranges['maximum'] = int(xmaximum) * 1.0
                else:
                    ranges['maximum'] = float(xmaximum)

            if ranges['minimum'] >= ranges['maximum']:
                ranges['maximum'] = ranges['minimum'] + (1 if is_int else 0.1)
                errors.append("port '%s' minimum value is equal or higher than its maximum" % portname)

            if xdefault is not None:
                if is_int:
                    if xdefault.is_int():
                        ranges['default'] = int(xdefault)
                    else:
                        ranges['default'] = float(xdefault)
                        if fmod(ranges['default'], 1.0) == 0.0:
                            warnings.append("port '%s' has integer property but default value is float" % portname)
                        else:
                            errors.append("port '%s' has integer property but default value has non-zero decimals" % portname)
                        ranges['default'] = int(ranges['default'])
                else:
                    if xdefault.is_int():
                        warnings.append("port '%s' default value is an integer" % portname)
                        ranges['default'] = int(xdefault) * 1.0
                    else:
                        ranges['default'] = float(xdefault)

                testmin = ranges['minimum']
                testmax = ranges['maximum']

                if "sampleRate" in properties:
                    testmin *= 48000
                    testmax *= 48000

                if not (testmin <= ranges['default'] <= testmax):
                    ranges['default'] = ranges['minimum']
                    errors.append("port '%s' default value is out of bounds" % portname)

            else:
                ranges['default'] = ranges['minimum']

                if "Input" in types:
                    errors.append("port '%s' is missing default value" % portname)

        else:
            if is_int:
                ranges['minimum'] = 0
                ranges['maximum'] = 1
                ranges['default'] = 0
            else:
                ranges['minimum'] = -1.0 if "CV" in types else 0.0
                ranges['maximum'] = 1.0
                ranges['default'] = 0.0

            if "CV" not in types and designation != str(world.ns.lv2.latency):
                errors.append("port '%s' is missing value ranges" % portname)

        scalepoints = port.get_scale_points()

        if scalepoints is not None:
            scalepoints_unsorted = []

            for sp in scalepoints:
                label = node2str(sp.get_label())
                value = sp.get_value()

                if label is None:
                    errors.append("a port scalepoint is missing its label")
                    continue

                if value is None:
                    errors.append("port scalepoint '%s' is missing its value" % label)
                    continue

                if is_int:
                    if value.is_int():
                        value = int(value)
                    else:
                        value = float(value)
                        if fmod(value, 1.0) == 0.0:
                            warnings.append("port '%s' has integer property but scalepoint '%s' value is float" % (portname, label))
                        else:
                            errors.append("port '%s' has integer property but scalepoint '%s' value has non-zero decimals" % (portname, label))
                        value = int(value)
                else:
                    if value.is_int():
                        warnings.append("port '%s' scalepoint '%s' value is an integer" % (portname, label))
                        value = int(value) * 1.0
                    else:
                        value = float(value)

                if ranges['minimum'] <= value <= ranges['maximum']:
                    scalepoints_unsorted.append((value, label))
                else:
                    errors.append(("port scalepoint '%s' has an out-of-bounds value:\n" % label) +
                                  ("%d < %d < %d" if is_int else "%f < %f < %f") % (ranges['minimum'], value, ranges['maximum']))

            if scalepoints_unsorted:
                unsorted = dict(s for s in scalepoints_unsorted)
                values = list(s[0] for s in scalepoints_unsorted)
                values.sort()
                scalepoints = list({'value': v, 'label': unsorted[v]} for v in values)

        if "enumeration" in properties and len(scalepoints) <= 1:
            errors.append("port '%s' wants to use enumeration but doesn't have enough values" % portname)
            properties.remove("enumeration")

    # control ports might contain unit
    units = {}
    if "Control" in types:
        # unit
        uunit = port.get_value(world.ns.units.unit)
        ulabel = urender = usymbol = None

        if uunit:
            uuri = str(uunit[0])

            # using pre-existing lv2 unit
            if uuri.startswith(str(world.ns.units)):
                uuri = uuri.rsplit('#', 1)[-1]

                if uuri not in LV2_UNITS:
                    errors.append("port '%s' has invalid lv2 unit '%s'" % (portname, uuri))
                else:
                    ulabel, urender, usymbol = LV2_UNITS[uuri]

            # using custom unit
            else:
                xlabel  = world.find_nodes(uunit[0], world.ns.rdfs.label, None)
                xrender = world.find_nodes(uunit[0], world.ns.units.render, None)
                xsymbol = world.find_nodes(uunit[0], world.ns.units.symbol, None)

                if xlabel:
                    ulabel = str(xlabel[0])
                else:
                    errors.append("port '%s' has custom unit with no label" % portname)

                if xrender:
                    urender = str(xrender[0])
                else:
                    errors.append("port '%s' has custom unit with no render" % portname)

                if xsymbol:
                    usymbol = str(xsymbol[0])
                else:
                    errors.append("port '%s' has custom unit with no symbol" % portname)

        if ulabel and urender and usymbol:
            units = {
                'label': ulabel,
                'render': urender,
                'symbol': usymbol,
            }

    return (types, {
        'name': portname,
        'symbol': portsymbol,
        'ranges': ranges,
        'units': units,
        'comment': pcomment,
        'designation': designation,
        'properties': properties,
        'rangeSteps': rangesteps,
        'scalePoints': scalepoints,
        'shortName': psname,
    })


def _get_plugin_ports(ctx, plugin):
    index = 0
    ports = {
        'audio': {
            'input': [],
            'output': []
        },
        'control': {
            'input': [],
            'output': []
        },
        'midi': {
            'input': [],
            'output': []
        }
    }

    ctx.portsymbols = set()
    ctx.portnames = set()

    for i in range(plugin.get_num_ports()):
        port = plugin.get_port_by_index(i)
        types, info = _get_port_info(ctx, port)
        info['index'] = i

        is_input = "Input" in types
        types.remove("Input" if is_input else "Output")

        for typ in [typl.lower() for typl in types]:
            if typ not in ports.keys():
                ports[typ] = { 'input': [], 'output': [] }
            ports[typ]["input" if is_input else "output"].append(info)

    return ports


def _get_plugin_presets(ctx, plugin):
    world = ctx.world
    presets = plugin.get_related(world.ns.presets.Preset)
    preset_list = []

    for preset in presets:
        world.load_resource(preset)
        labels = world.find_nodes(preset, world.ns.rdfs.label, None)

        if labels:
            label = str(labels[0])
        else:
            label = None
            ctx.errors.append("Preset '%s' has no rdfs:label" % preset)

        preset_list.append({'label': label, 'uri': str(preset)})

    return sorted(preset_list, key=lambda x: x['label'] or '')


def _get_plugin_properties(ctx, plugin_uri):
    world = ctx.world

    properties = {}
    readable = [(node, False)
                for node in world.find_nodes(plugin_uri, world.ns.patch.readable, None)]
    writeable = [(node, True)
                 for node in world.find_nodes(plugin_uri, world.ns.patch.writable, None)]

    for prop_uri, is_writable in readable + writeable:
        prop_node = world.find_nodes(prop_uri, world.ns.rdf.type, world.ns.lv2.Parameter)

        if not prop_node:
            ctx.errors.append(
                "Could not find defintion of property '%s'." % prop_uri)
            continue

        label = world.find_nodes(prop_uri, world.ns.rdfs.label, None)

        if label:
            label = str(label[0])

        range_ = world.find_nodes(prop_uri, world.ns.rdfs.range, None)

        if range_:
            range_ = str(range_[0])

        prop_uri = str(prop_uri)
        properties[prop_uri] = {
            'uri': prop_uri,
            'label': label,
            'type': range_,
            'writable': is_writable,
        }

    return properties


def _get_plugin_info(ctx, plugin):
    world = ctx.world
    world.ns.mod = lilv.Namespace(world, NS_MOD)
    world.ns.patch = lilv.Namespace(world, NS_PATCH)
    world.ns.pprops = lilv.Namespace(world, NS_PORT_PROPERTIES)
    world.ns.presets = lilv.Namespace(world, NS_PRESET)
    world.ns.units = lilv.Namespace(world, NS_UNITS)

    ctx.errors = errors = []
    ctx.warnings = warnings = []

    # uri
    uri = plugin.get_uri()

    if uri is None:
        errors.append("plugin uri is missing or invalid")
    elif str(uri).startswith("file:"):
        errors.append("plugin uri is local, and thus not suitable for redistribution")

    # load all resources in bundle
    world.load_resource(uri)

    # name
    name = plugin.get_name()

    if name is None:
        errors.append("plugin name is missing")

    # label
    label = getfirst(plugin, world.ns.mod.label)

    if label is None:
        warnings.append("plugin label is missing")
        if name is not None:
            label = str(name)[:16]
    elif len(label) > 16:
        warnings.append("plugin label has more than 16 characters")

    # author
    author_name = plugin.get_author_name()
    author_email = plugin.get_author_email()
    author_homepage = plugin.get_author_homepage()

    # binary
    binary = plugin.get_library_uri()

    if binary is None:
        errors.append("plugin binary is missing")
    else:
        binary = binary.get_path()

    # brand
    brand = getfirst(plugin, world.ns.mod.brand)

    if brand is None:
        warnings.append("plugin brand is missing")
    elif len(brand) > 16:
        warnings.append("plugin brand has more than 11 characters")

    # license
    license = getfirst(plugin, world.ns.doap.license)

    if license is None:
        errors.append("plugin license is missing")

    # comment
    comment = getfirst(plugin, world.ns.rdfs.comment)

    if comment is None:
        errors.append("plugin comment is missing")

    # version
    microver = plugin.get_value(world.ns.lv2.microVersion)
    minorver = plugin.get_value(world.ns.lv2.minorVersion)

    if not microver and not minorver:
        errors.append("plugin is missing version information")
        minor_version = 0
        micro_version = 0
    else:
        if not minorver:
            errors.append("plugin is missing minorVersion")
            minor_version = 0
        else:
            minor_version = int(minorver[0])

        if not microver:
            errors.append("plugin is missing microVersion")
            micro_version = 0
        else:
            micro_version = int(microver[0])

    version = "%d.%d" % (minor_version, micro_version)

    if minor_version == 0:
        # 0.x is experimental
        stability = "experimental"
    elif minor_version % 2 != 0 or micro_version % 2 != 0:
        # odd x.2 or 2.x is testing/development
        stability = "testing"
    else:
        # otherwise it's stable
        stability = "stable"

    # category
    categories = plugin.get_value(world.ns.rdf.type)
    category = set()

    if categories:
        for node in categories:
            category.update(LV2_CATEGORIES.get(str(node).split('#', 1)[-1], []))

    # bundles
    bundle = plugin.get_bundle_uri()
    bundlepath = bundle.get_path().rstrip(os.sep)
    bundles = plugin.get_data_uris()

    if bundles:
        bundles = {dirname(node.get_path().rstrip(os.sep)) for node in bundles}
        bundles.add(bundlepath)
        bundles = list(bundles)
    else:
        bundles = [bundlepath]

    # ports
    ports = _get_plugin_ports(ctx, plugin)

    # presets
    presets = _get_plugin_presets(ctx, plugin)

    # properties
    properties = _get_plugin_properties(ctx, uri)

    return {
        'uri': node2str(uri),
        'name': node2str(name),
        'binary': binary,
        'brand': brand,
        'label': label,
        'license': license,
        'comment': comment,
        'category': list(category),
        'microVersion': micro_version,
        'minorVersion': minor_version,
        'version': version,
        'stability': stability,
        'author': {
            'name': node2str(author_name),
            'email': node2str(author_email),
            'homepage': node2str(author_homepage),
        },
        'bundles': sorted(bundles),
        #'ui': ui,
        'ports': ports,
        'presets': presets,
        'properties': properties,
        'errors': sorted(errors),
        'warnings': sorted(warnings),
    }


def get_plugins_info(uri=None):
    class _context():
        pass

    ctx = _context()
    ctx.world = lilv.World()
    ctx.world.load_all()
    plugins = ctx.world.get_all_plugins()

    if uri:
        uri = ctx.world.new_uri(uri)
        return _get_plugin_info(ctx, plugins[uri])
    else:
        return [_get_plugin_info(ctx, p) for p in plugins]


def main(args=None):
    import argparse
    import pprint
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument(
        '-d', '--debug',
        action="store_true",
        help="Print debugging information to standard error")
    ap.add_argument(
        '-p', '--pretty-format',
        action="store_true",
        help="Pretty format JSON output")
    ap.add_argument(
        'plugin_uri',
        nargs='?',
        metavar='URI', help='Plugin URI')

    args = ap.parse_args(args)
    plugin_data = get_plugins_info(args.plugin_uri)

    if args.debug:
        print(pprint.pformat(plugin_data), file=sys.stderr)

    if args.pretty_format:
        kw = {'indent': 4}
    else:
        kw = {}

    print(json.dumps(plugin_data, sort_keys=True, **kw))


if __name__ == '__main__':
    import sys

    sys.exit(main() or 0)
