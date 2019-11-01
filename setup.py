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
        ('jack-timebase-master', "transport.timebase_master"),
        ('jack-transporter', "transport.transporter"),
        ('jack-midi-to-transport', "transport.midi_to_transport"),
        ('jack-rtmidi-to-transport', "transport.rtmidi_to_transport", "rtmidi"),
        #('lv2-list-plugin-presets', "lv2.lv2_list_plugin_presets", "lilv")]:
        ('lv2-list-plugin-presets', "lv2.lv2_list_plugin_presets"),
        ('lv2grep', "lv2.lv2grep"),
    ]:
    spec = "{} = jackaudiotools.{}:main".format(name, mod)

    if extras:
        spec += " [{}]".format(",".join(extras))

    scripts.append(spec)


setup(
    name='jack-audio-tools',
    version="0.1",
    description="A collection of utilities and tools for the JACK audio ecosystem",
    long_description=read('README.md'),
    long_description_content_type="text/markdown",
    url="https://github.com/SpotlightKid/jack-audio-tools",
    license='MIT License',
    author="Christopher Arndt",
    author_email="info@chrisarndt.de",
    packages=[
        'jackaudiotools.transport',
        'jackaudiotools.lv2',
    ],
    package_dir={'jackaudiotools': ''},
    include_package_data=True,
    install_requires=[
        "JACK-Client >= 0.5.0",
    ],
    extras_require={
        # unfortunately, 'lilv' is not registered on PyPI
        #'lilv': ["lilv"],
        'rtmidi': ["python-rtmidi"],
    },
    python_requires='>=3',
    entry_points={
        'console_scripts': scripts
    },
    zip_safe=False,
)
