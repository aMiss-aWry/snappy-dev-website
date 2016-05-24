#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2016 Canonical
#
# Authors:
#  Didier Roche
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

'''Release-related misc utilities'''

import logging
import os
import sys
import subprocess
import yaml

from .settings import ROOT_DIR, RELEASES_BRANCH_MAPPING, DEVICES_MAPPING
from .tools import next_relevant_line

logger = logging.getLogger(__name__)


def _get_supported_releases_map():
    '''Load supported release and master branch map'''
    release_map = {}
    with open(os.path.join(ROOT_DIR, RELEASES_BRANCH_MAPPING)) as f:
        try:
            for line in next_relevant_line(f):
                (release, branch_name) = line.split(" ")
                release_map[release] = branch_name
        except ValueError:
            logger.error("Release file is not of valid format: <release_name> <branch>")
            sys.exit(1)
    return release_map


def get_releases_in_context():
    '''Prepare for one release, switching context and return release name'''
    for release, branch in _get_supported_releases_map().items():
        subprocess.check_call(["git", "checkout", "-q", branch])
        yield release


def load_device_metadata(release):
    """Return maps of variables substitution token for each device.

    Adding RELEASE_VERSION and DEVICE_ID automatically to each device for convenience.
    IMAGE_FILENAME and IMAGE_UNCOMPRESSED_FILENAME are also aded if IMAGE_URL is present.

    Format is:
        { 'device-key':
            { 'VARIABLE_NAME': 'VALUE' },
              …
            },
          …
        }

        Example:
        { 'rpi2': {'IMAGE_URL': 'https://download.ubuntu.com/blablabnla/rpi2-16.04.iso',
                   'IMAGE_FILENAME': 'rpi2-16.04.iso',
                   'RELEASE_VERSION': '16.04' },
          'dragonboard': {'FOO': 'BAR',
                          'RELEAS_VERSION': '16.04' },
        }"""
    devices_metadata = {}
    with open(os.path.join(ROOT_DIR, DEVICES_MAPPING), encoding='utf-8') as f:
        devices_metadata = yaml.load(f.read())
    for device_key in devices_metadata:
        devices_metadata[device_key]['RELEASE_VERSION'] = release
        devices_metadata[device_key]['DEVICE_ID'] = device_key
        image_url = devices_metadata[device_key].get('IMAGE_URL')
        if image_url:
            devices_metadata[device_key]['IMAGE_FILENAME'] = os.path.basename(image_url)
            devices_metadata[device_key]['IMAGE_UNCOMPRESSED_FILENAME'] = \
                os.path.basename(os.path.splitext(image_url)[0])
    return devices_metadata
