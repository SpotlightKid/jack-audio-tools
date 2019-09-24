#!/usr/bin/env python3
#
# midi_to_transport.py
#
"""JACK client which allows to control transport state via MIDI.

The following MIDI messages, when received, start the JACK transport:

* START (System Real-time)
* CONTINUE (System Real-time)
* PLAY (MMC)
* DEFERRED PLAY (MMC)

These messages stop the transport:

* STOP (System Real-time)
* STOP (MMC)
* PAUSE (MMC)
* RESET (MMC)

And these rewind the transport to frame zero:

* REWIND (MMC)
* RESET (MMC)

MMC messages are ignored, if the device number in the MMC System Exclusive
message does not match the client's device number (set with the -d command
line option).

If the client's device number is set to 127 (the default), it matches all
MMC message device numbers.

"""

import argparse
import sys
from threading import Event

import jack


MIDI_SYSEX = 0xF0
MIDI_START = 0xFA
MIDI_CONTINUE = 0xFB
MIDI_STOP = 0xFC
MMC_STOP = 1
MMC_PLAY = 2
MMC_DEFERRED_PLAY = 3
MMC_FAST_FORWARD = 4
MMC_REWIND = 5
MMC_RECORD_STROBE = 6
MMC_RECORD_EXIT = 7
MMC_RECORD_PAUSE = 8
MMC_PAUSE = 9
MMC_EJECT = 10
MMC_CHASE = 11
MMC_ERROR = 12
MMC_RESET = 13


class JackMidiToTransport(jack.Client):
    def __init__(self, name, device=0x7F):
        super().__init__(name)
        self.device = device
        self.stop_event = Event()
        self.port = self.midi_inports.register('input')
        self.set_shutdown_callback(self.shutdown)
        self.set_process_callback(self.process)

    def shutdown(self, status, reason):
        print('JACK shutdown:', reason, status)
        self.stop_event.set()

    def process(self, frames):
        for offset, data in self.port.incoming_midi_events():
            status = ord(data[0])
            t_state = self.transport_state

            if status in (MIDI_START, MIDI_CONTINUE) and t_state == jack.STOPPED:
                self.transport_start()
            elif status == MIDI_STOP and t_state != jack.STOPPED:
                self.transport_stop()
            elif status == MIDI_SYSEX:
                data = bytes(data)

                if (len(data) == 6 and data[1] == 0x7F and data[3] == 6 and
                        (self.device == 0x7F or data[2] == self.device)):
                    cmd = data[4]

                    if cmd in (MMC_PLAY, MMC_DEFERRED_PLAY) and t_state == jack.STOPPED:
                        self.transport_start()
                    elif cmd in (MMC_STOP, MMC_PAUSE, MMC_RESET) and t_state != jack.STOPPED:
                        self.transport_stop()

                    if cmd in (MMC_REWIND, MMC_RESET):
                        self.transport_frame = 0


def main(args=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        '-c', '--client-name',
        metavar='NAME',
        default='midi-to-transport',
        help="JACK client name (default: %(default)s)")
    ap.add_argument(
        '-d', '--device',
        type=int,
        default=0x7F,
        help="MIDI SysEx device number (0-127, default: %(default)s)")

    args = ap.parse_args(args)

    try:
        client = JackMidiToTransport(args.client_name, max(0, min(args.device, 127)))
    except jack.JackError as exc:
        return "Could not create JACK client: {}".format(exc)

    with client:
        try:
            print('Press Ctrl-C to quit... ')
            client.stop_event.wait()
        except KeyboardInterrupt:
            print('')


if __name__ == '__main__':
    sys.exit(main() or 0)
