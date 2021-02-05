#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# setup.py - Setup file for the jack-audio-tools package
#

from os.path import dirname, join

from setuptools import setup


def read(*args):
    return open(join(dirname(__file__), *args)).read()

scripts = []
for name, mod, *extras in [
        ('carxp2lv2presets', "carla.carxp2lv2presets", "rdflib"),
        ('jack-timebase-master', "transport.timebase_master"),
        ('jack-transporter', "transport.transporter"),
        ('jack-midi-to-transport', "transport.midi_to_transport"),
        ('jack-rtmidi-to-transport', "transport.rtmidi_to_transport", "rtmidi"),
        ('jack-dbus-monitor', "jackdbus.jackmonitor", "dbus"),
        #('lv2-grep', "lv2.lv2_grep", "lilv"),
        ('lv2-grep', "lv2.grep"),
        #('lv2-list-plugin-presets', "lv2.lv2_list_plugin_presets", "lilv")]:
        ('lv2-list-plugin-presets', "lv2.list_plugin_presets"),
        #('lv2-plugin-info', "lv2.lv2_plugin_info", "lilv"),
        ('lv2-plugin-info', "lv2.plugin_info"),
        #('lv2-plugin-uris', "lv2.lv2_plugin_uris", "lilv"),
        ('lv2-plugin-uris', "lv2.plugin_uris"),
    ]:
    spec = "{} = jackaudiotools.{}:main".format(name, mod)

    if extras:
        spec += " [{}]".format(",".join(extras))

    scripts.append(spec)

classifiers = """\
Development Status :: 4 - Beta
Environment :: Console
Operating System :: POSIX
License :: OSI Approved :: MIT License
Programming Language :: Python
Programming Language :: Python :: 3 :: Only
Programming Language :: Python :: 3.7
Programming Language :: Python :: 3.8
Topic :: Multimedia :: Sound/Audio
"""

setup(
    name='jack-audio-tools',
    version="0.4.0",
    description="A collection of utilities and tools for the JACK audio ecosystem",
    long_description=read('README.md'),
    long_description_content_type="text/markdown",
    url="https://github.com/SpotlightKid/jack-audio-tools",
    license='MIT License',
    author="Christopher Arndt",
    author_email="info@chrisarndt.de",
    keywords="jack,jackaudio,LV2,carla,MIDI",
    classifiers=[c.strip() for c in classifiers.splitlines() if not c.startswith('#')],
    packages=[
        'jackaudiotools.carla',
        'jackaudiotools.lv2',
        'jackaudiotools.jackdbus',
        'jackaudiotools.transport',
    ],
    package_dir={'jackaudiotools': ''},
    include_package_data=True,
    install_requires=[
        "JACK-Client >= 0.5.0",
    ],
    extras_require={
        # unfortunately, 'lilv' is not registered on PyPI
        #'lilv': ["lilv"],
        'rtmidi': ['python-rtmidi'],
        'rdflib': ['rdflib'],
        'dbus': ['PyGObject', "dbus-python"],
    },
    python_requires='>=3',
    entry_points={
        'console_scripts': scripts
    },
    zip_safe=False,
)
