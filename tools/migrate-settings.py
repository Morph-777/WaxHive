#!/usr/bin/env python3
"""Copy development layout preferences once, preserving existing WaxHive settings."""
from pathlib import Path
import configparser
import xml.etree.ElementTree as ET
source = Path.home() / '.var/app/org.gnome.Music/config/glib-2.0/settings/keyfile'
target = Path.home() / '.var/app/io.github.Morph777.WaxHive/config/glib-2.0/settings/keyfile'
if target.exists() or not source.exists():
    print('WaxHive preferences left unchanged.')
else:
    original = configparser.ConfigParser(interpolation=None)
    original.read(source)
    section = 'org/gnome/Music'
    if original.has_section(section):
        schema = Path(__file__).resolve().parents[1] / 'data/org.gnome.Music.gschema.xml'
        keys = {key.attrib['name'] for key in ET.parse(schema).iter('key')}
        migrated = configparser.ConfigParser(interpolation=None)
        migrated['io/github/Morph777/WaxHive'] = {
            key: value for key, value in original[section].items() if key in keys}
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('w') as stream:
            migrated.write(stream, space_around_delimiters=False)
        target.chmod(0o600)
        print('Copied development preferences to WaxHive.')
