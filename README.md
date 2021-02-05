# jack-audio-tools

A collection of utilities and tools for the [JACK] audio ecosystem


## JACK Transport

The scripts in the `jackaudiotools.transport` package query or manipulate the
JACK transport state.

They require the [JACK-Client] package to be installed, which will be installed
automatically, when you install the `jack-audio-tools` distribution via `pip`:

    pip install jack-audio-tools


### `jack-midi-to-transport`

JACK client which allows to control transport state via MIDI.

The client provides a MIDI input and converts received MIDI system real-time
and MIDI machine control (MMC) messages into JACK transport commands.

The following MIDI messages, when received, start the JACK transport:

* `START` (System Real-time)
* `CONTINUE` (System Real-time)
* `PLAY` (MMC)
* `DEFERRED PLAY` (MMC)

These messages stop the transport:

* `STOP` (System Real-time)
* `STOP` (MMC)
* `PAUSE` (MMC)
* `RESET` (MMC)

And these rewind the transport to frame zero:

* `REWIND` (MMC)
* `RESET` (MMC)

MMC messages are ignored, if the device number in the MMC System Exclusive
message does not match the client's device number (set with the -d command
line option).

If the client's device number is set to 127 (the default), it matches all
MMC message device numbers.


### `jack-rtmidi-to-transport`

JACK client which allows to control transport state via MIDI.

A variant of `midi_to_transport`, which uses the [python-rtmidi] package
as a MIDI backend instead of JACK-Client, which is slightly more efficient,
because MIDI input processing is happening in a C++ thread instead of a
Python callback.

To use it, specify the `rtmidi` extra dependency when installing the
`jack-audio-tools` distribution via `pip`:

    pip install "jack-audio-tools[rtmidi]"


### `jack-timebase-master`

A simple JACK timebase master, which provides  musical timing related
information (i.e. currents bar, beats per bar, beat denominator, BPM etc.)
to other JACK clients.


### `jack-transporter`

Query or change the JACK transport state.


## JACK D-BUS

The scripts in the `jackaudiotools.jackdbus` package interface with the JACK
D-BUS service to query information about the status of the JACK server and/or
control its operation.

These scripts require the [PyGobject]  and [dbus-python] packages to be
installed. To install these, specify the `dbus` extra dependency when
installing the `jack-audio-tools` distribution via `pip`:

    pip install "jack-audio-tools[dbus]"


### `jack-dbus-monitor`

This script monitors the JACK server via D-BUS and runs a command on status
changes and optionally at a given interval passing some JACK stats in the
environment.

Here is an example shell script to use as a command:

```bash
#!/bin/bash

event="$1"  # 'start', 'stop' or 'status'
echo "JACK event: $event"

if [[ "$event" = "status" ]]; then
    echo "IS_STARTED: $IS_STARTED"
    echo "IS_REALTIME: $IS_REALTIME"
    echo "PERIOD: $PERIOD"
    echo "LATENCY: $LATENCY"
    echo "LOAD: $LOAD"
    echo "XRUNS: $XRUNS"
    echo "SAMPLERATE: $SAMPLERATE"
fi
```

Save this as `jack_status.sh` and use it like so:

```console
jack-dbus-monitor --interval-stats 1000 ./jack_status.sh
```


## LV2

The scripts in the `jackaudiotools.lv2` package help with querying information
from the [LV2] plugins installed on the system.

They require the [lilv] Python bindings to be installed. Unfortunately, these
can not be installed from the Python Package Index. Instead, install a recent
version of the `lilv` library, either from your distribution's package
repository or from source.


### `lv2-grep`

Print URIs of all installed LV2 plugins matching the given regular expression.

Can optionally output the list of matching plugins in JSON format, where each
list item is an object with the plugin name and uri and optionally the list of
categories the plugin belongs to, as properties.


### `lv2-plugin-uris`

Print a list of all URIs associated with an LV2 plugin.


### `lv2-list-plugin-presets`

List all presets of an LV2 plugin with the given URI.


### `lv2-plugin-info`

Generate a JSON document with information about a single or all installed LV2
plugins. This allows plugin meta data to be loaded quickly in other programs.

Depending on the number of plugins installed on your system, this script may
run for several seconds or even minutes and produce an output file of several
megabytes in size.


## Carla

The scripts in the `jackaudiotools.carla` package manipulate or query [Carla]
project files.


### `carxp2lv2presets`

Export plugin settings from a Carla project file (.carxp) as LV2 preset bundles.

This script requires the [rdflib] package to be installed. To install it,
specify the `rdflib` extra dependency when installing the `jack-audio-tools`
distribution via `pip`:

    pip install "jack-audio-tools[rdflib]"


## License

This software is distributed under the MIT License.

See the file [LICENSE](./LICENSE) for more information.


## Author

This software is written by *Christopher Arndt*.


[carla]: https://kx.studio/Applications:Carla
[dbus-python]: https://pypi.org/project/dbus-python
[jack-client]: https://pypi.org/project/JACK-Client
[jack]: https://jackaudio.org/
[lilv]: http://drobilla.net/software/lilv
[lv2]: http://lv2plug.in/
[PyGObject]: https://pypi.org/project/PyGobject
[python-rtmidi]: https://pypi.org/project/python-rtmidi
[rdflib]: https://pypi.org/project/rdflib
