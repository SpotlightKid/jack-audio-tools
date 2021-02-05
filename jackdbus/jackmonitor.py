#!/usr/bin/env python
"""Monitor JACK server via D-BUS and run a command on status changes."""

import argparse
import logging
import os
import signal
import subprocess
import sys
from functools import partial

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

__prog__ = 'jackmonitor'
__version__ = '0.1.0'
log = logging.getLogger(__prog__)
INTERVAL_STATS = 0
INTERVAL_RECONNECT = 1000


class DBUSBaseInterface:
    """Base class for D-BUS service interface wrappers.

    This is an abstract base class. Sub-classes ned to define the following
    class or instance attributes:

    * service - the name of the D-BUS service
    * interface - the name of the D-BUS accessed via this class
    * object_path = the path to the service object providing the interface

    """

    def __init__(self, ctl=None, bus=None):
        if not ctl:
            ctl = self.get_controller(bus)

        self._if = dbus.Interface(ctl, self.interface)

    def get_controller(self, bus=None):
        if not bus:
            bus = dbus.SessionBus()
        return bus.get_object(self.service, self.object_path)

    def _async_handler(self, *args, **kw):
        name = kw.get('name')
        callback = kw.get('callback')

        if args and isinstance(args[0], dbus.DBusException):
            log.error("Async call failed name=%s: %s", name, args[0])
            return

        if callback:
            callback(*args, name=name)

    def call_async(self, meth, args=None, name=None, callback=None,
                   error_callback=None):
        if callback:
            handler = partial(self._async_handler, callback=callback,
                              name=name or meth)
            kw = dict(reply_handler=handler, error_handler=error_callback or handler)
        else:
            kw = {}

        return getattr(self._if, meth)(*args or [], **kw)

    def add_signal_handler(self, handler, signal=None):
        return self._if.connect_to_signal(
            signal_name=signal,
            handler_function=handler,
            interface_keyword='interface',
            member_keyword='signal')


class JackCtlInterface(DBUSBaseInterface):
    service = "org.jackaudio.service"
    object_path = "/org/jackaudio/Controller"
    interface = "org.jackaudio.JackControl"

    def exit(self, cb=None, error_cb=None):
        return self.call_async('Exit', name='is_started', callback=cb,
                               error_callback=error_cb)

    def is_started(self, cb=None, error_cb=None):
        return self.call_async('IsStarted', name='is_started', callback=cb,
                               error_callback=error_cb)

    def is_realtime(self, cb=None, error_cb=None):
        return self.call_async('IsRealtime', name='is_realtime', callback=cb,
                               error_callback=error_cb)

    def start_server(self, cb=None, error_cb=None):
        return self.call_async('StartServer', name='start_server', callback=cb,
                               error_callback=error_cb)

    def stop_server(self, cb=None, error_cb=None):
        return self.call_async('StopServer', name='stop_server', callback=cb,
                               error_callback=error_cb)

    def get_latency(self, cb=None, error_cb=None):
        return self.call_async('GetLatency', name='latency', callback=cb,
                               error_callback=error_cb)

    def get_load(self, cb=None, error_cb=None):
        return self.call_async('GetLoad', name='load', callback=cb,
                               error_callback=error_cb)

    def get_period(self, cb=None, error_cb=None):
        return self.call_async('GetBufferSize', name='period', callback=cb,
                               error_callback=error_cb)

    def get_sample_rate(self, cb=None, error_cb=None):
        return self.call_async('GetSampleRate', name='samplerate', callback=cb,
                               error_callback=error_cb)

    def get_xruns(self, cb=None, error_cb=None):
        return self.call_async('GetXruns', name='xruns', callback=cb)

    def add_signal_handler(self, handler, signal=None):
        return self._if.connect_to_signal(
            signal_name=signal,
            handler_function=handler,
            interface_keyword='interface',
            member_keyword='signal')


class JackMonitor:
    """Monitor JACK status via D-BUS."""

    def __init__(self, args, bus=None):
        self.args = args
        self.jack_status = {}

        # create and register main loop
        self.mainloop = GLib.MainLoop()
        DBusGMainLoop(set_as_default=True)

        # Create Jack control and config D-BUS interfaces
        self.bus = bus or dbus.SessionBus()
        self.dbus_connect()

        # Check for current JACK status
        self.jackctl.is_started(cb=self.update_jack_status)

    def run(self):
        self.mainloop.run()

    def dbus_connect(self):
        """Create Jack control and config D-BUS interfaces."""
        try:
            log.debug("Connecting to JACK D-BUS interface...")
            self.jackctl = JackCtlInterface(bus=self.bus)
        except dbus.exceptions.DBusException as exc:
            log.warning("Could not connect to JACK D-BUS interface: %s", exc)
            return True
        else:
            log.debug("JACK D-BUS connection established.")
            self.jackctl.add_signal_handler(self.handle_jackctl_signal)
            if self.args.interval_stats > 0:
                GLib.timeout_add(self.args.interval_stats, self.get_jack_stats)
                if self.args.command:
                    GLib.timeout_add(self.args.interval_stats, self.run_stats_command)

    def handle_dbus_error(self, *args):
        """Handle errors from async JackCtlInterface calls.

        If the error indicates that the JackCtl D-BUS service vanished,
        invalidate the existing D-BUS interface instances and schedule a
        reconnection attempt.

        """
        log.warning("JackCtl D-BUS call error handler called.")
        if args and isinstance(args[0], dbus.DBusException):
            if 'org.freedesktop.DBus.Error.ServiceUnknown' in str(args[0]) and self.jackctl:
                log.warning("JackCtl D-BUS service vanished. Assuming JACK is stopped.")
                self.update_jack_status(0, name='is_started')
                self.jackctl = None
                if self.args.interval_reconnect > 0:
                    GLib.timeout_add(self.args.interval_reconnect, self.dbus_connect)
                else:
                    log.debug("Exiting main loop.")
                    self.mainloop.quit()

    def handle_jackctl_signal(self, *args, signal=None, **kw):
        log.debug("JackCtl signal received: %r", signal)
        if signal == 'ServerStarted':
            self.update_jack_status(1, name='is_started')
        elif signal == 'ServerStopped':
            self.update_jack_status(0, name='is_started')

    def update_jack_status(self, value, name=None):
        old_status = self.jack_status.get(name)
        self.jack_status[name] = value
        log.debug("JACK status: %r", self.jack_status)

        if name == 'is_started' and self.args.command:
            if old_status is None and self.args.skip_initial:
                log.debug("Skipping initial JACK status update.")
                return
            run_command([self.args.command, "start" if value else "stop"])

    def run_stats_command(self):
        if self.args.command and self.args.interval_stats > 0:
            env = {key.upper(): str(val) for key, val in self.jack_status.items()}
            run_command([self.args.command, "status"], env=env)

        return True

    def get_jack_stats(self):
        if self.jackctl and self.jack_status.get('is_started'):
            try:
                log.debug("Requesting JACK stats...")
                cb = self.update_jack_status
                ecb = self.handle_dbus_error
                self.jackctl.is_realtime(cb, ecb)
                self.jackctl.get_sample_rate(cb, ecb)
                self.jackctl.get_period(cb, ecb)
                self.jackctl.get_load(cb, ecb)
                self.jackctl.get_xruns(cb, ecb)
                self.jackctl.get_latency(cb, ecb)
            except dbus.exceptions.DBusException:
                log.warning("JackCtl D-BUS service failure. Assuming JACK is stopped.")
                self.update_jack_status(0, name='is_started')

        return True


def run_command(cmd, env=None):
    env_ = os.environ.copy()
    if env:
        env_.update(env)

    return subprocess.Popen(cmd, close_fds=True, env=env_)


def main(args=None):
    """Main function to be used when called as a script."""
    from dbus.mainloop.glib import DBusGMainLoop

    ap = argparse.ArgumentParser(prog=__prog__, description=__doc__.splitlines()[0])
    ap.add_argument(
        '-i', '--interval-stats',
        type=int,
        metavar="MS",
        default=INTERVAL_STATS,
        help="Also run command at given interval and pass JACK stats in environment "
             "(default: %(default)s, 0 = off).")
    ap.add_argument(
        '-r', '--interval-reconnect',
        type=int,
        metavar="MS",
        default=INTERVAL_RECONNECT,
        help="Interval for re-connecting to D-BUS (default: %(default)s, 0 = off).")
    ap.add_argument(
        '-s', '--skip-initial',
        action="store_true",
        help="Skip initial JACK status event on program startup.")
    ap.add_argument(
        '--version',
        action="version",
        version="%%(prog)s %s" % __version__,
        help="Show program version and exit.")
    ap.add_argument(
        '-v', '--verbose',
        action="store_true",
        help="Be verbose about what the script does.")
    ap.add_argument(
        'command',
        help="Run given command on JACK status changes.")

    args = ap.parse_args(args if args is not None else sys.argv[1:])

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="[%(name)s] %(levelname)s: %(message)s")

    monitor = JackMonitor(args)
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)

    try:
        monitor.run()
    except KeyboardInterrupt:
        log.debug("Bye-bye.")


if __name__ == '__main__':
    import sys
    sys.exit(main() or 0)
