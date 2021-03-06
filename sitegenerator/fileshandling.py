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

'''Copying and treating files internal metadata'''

import logging
import os
import re
import shutil

from .tools import replace_file_inline

logger = logging.getLogger(__name__)

import_re = re.compile("##IMPORT (.*)")

required_variable_re = re.compile('\[\[([^\[\]]*)\]\]')
optional_variable_re = re.compile('\<\<([^<>]*)\>\>')

relative_markdown_links = re.compile("\(((?!http|www).[^\)]*\.md)\)")


def import_and_copy_file(source_path, destination_path):
    '''Copy and import file content.

    We handle:
        1. symlinks are replaced with real files
        2. ##IMPORT <file_path> to copy destination file content into current file

    We return an error if we couldn't copy or import all listed filed
    '''
    success = True
    try:
        with open(destination_path, 'w') as dest_f:
            with open(source_path) as source_f:
                success = _copycontent_withimports_tag(source_f, dest_f)
    except UnicodeDecodeError as e:
        # Fall back to direct copy for binary files
        logger.debug("Directly copy as can't read {} as text: {}".format(source_path, e))
        shutil.copy2(source_path, destination_path)
    except FileNotFoundError:
        logger.error("Couldn't open {}".format(source_path))
        success = False
    return success


def _copycontent_withimports_tag(source_f, dest_f):
    '''Copy content from one file to the other, handling import tags

    imports within imports are handled, as well as symlinks chaining'''
    success = True
    for line in source_f:
        result = import_re.findall(line)
        if result:
            rel_path = result[0]
            try:
                with open(os.path.join(os.path.dirname(os.path.realpath(source_f.name)), rel_path)) as import_f:
                    if not _copycontent_withimports_tag(import_f, dest_f):
                        success = False
            except FileNotFoundError:
                logger.error("Couldn't import {} from {}".format(rel_path, source_f.name))
                success = False
        else:
            dest_f.write(line)
    return success


def _replace_from_map(line, regexp, replace_pattern, device_vars):
    '''Abstract replacing the variable from map.

    returning tuple is: (newline, failed_keywords_list)
    '''
    unfound_keywords_list = []
    for keyword in regexp.findall(line):
        try:
            replace_with = device_vars[keyword]
        except KeyError:
            unfound_keywords_list.append(keyword)
            replace_with = ""
        # we always replace, even with something empty (useful for optional content)
        line = line.replace(replace_pattern.format(keyword), replace_with)
    return (line, unfound_keywords_list)


def _replace_line_content(line, filename, device_name, device_vars):
    '''Return current line with replaced variable substitution.

    returning tuple is: (newline, success)
    '''
    success = True

    # handle optional variables first
    replace_pattern = "<<{}>>"
    (line, unfound_keywords) = _replace_from_map(line, optional_variable_re, replace_pattern, device_vars)
    for keyword in unfound_keywords:
        logger.info("{} doesn't have any mapping for {} which is optional in {}".format(
                device_name, keyword, filename))

    # handle required variables
    replace_pattern = "[[{}]]"
    (line, unfound_keywords) = _replace_from_map(line, required_variable_re, replace_pattern, device_vars)
    for keyword in unfound_keywords:
        logger.error("{} doesn't have any mapping for {} which is required in {}".format(
                device_name, keyword, filename))
        success = False

    return (line, success)


def replace_variables(path, device_name=None, device_vars={}):
    '''This variable replacement is done on files being in a per device directory.

    We handle variable substitution (only if device_name is provided)
        [[VARIABLE]] are required variables. It will print an error and return as such (not interrupting though)
        <<VARIABLE>> are optional variables. It will print an info and not return an error
    '''
    success = True
    with replace_file_inline(path) as (source_f, dest_f):
        for line in source_f:
            (line, new_success) = _replace_line_content(line, path, device_name, device_vars)
            success = new_success and success
            dest_f.write(line)

    return success


def reformat_links(path):
    '''Strip down the final .md on any relative path in links as it will be replaced with real file names'''
    with replace_file_inline(path) as (source_f, dest_f):
        for line in source_f:
            for link_to_replace in relative_markdown_links.findall(line):
                line = line.replace(link_to_replace, link_to_replace[:-3])
            dest_f.write(line)


def prepend_external_link(path, message, url):
    '''Prepend to existing page some known template type'''

    with replace_file_inline(path) as (source_f, dest_f):
        line_count = 1
        for line in source_f:
            # add the message as a second line
            if line_count == 2:
                dest_f.write("> [{}]({})\n".format(message, url))
            line_count += 1
            dest_f.write(line)
