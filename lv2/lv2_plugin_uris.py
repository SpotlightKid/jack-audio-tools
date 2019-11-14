#!/usr/bin/env python
"""List URIs associated with an LV2 plugin."""

import sys
import lilv


if len(sys.argv) < 2:
    sys.exit("Usage: %s <plugin URI>" % sys.argv[0])

w = lilv.World()
w.load_all()
plugins = w.get_all_plugins()
plugin = plugins[w.new_uri(sys.argv[1])]

print("Name: %s" % plugin.get_name())
print("Plugin URI: %s" % plugin.get_uri())
print("Bundle URI: %s" % plugin.get_bundle_uri())
print("Shared library URI: %s" % plugin.get_library_uri())

nodelist = plugin.get_data_uris()
uris = [str(n) for n in nodelist]
print("Data URIs:")
for uri in uris:
    print("-", uri)

nodelist = plugin.get_uis()
uris = [str(n) for n in nodelist]
print("UI URIs:")
for uri in uris:
    print("-", uri)

nodelist = plugin.get_related(None)
uris = [str(n) for n in nodelist]
print("Resource URIs:")
for uri in uris:
    print("-", uri)
