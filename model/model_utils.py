# -*- coding: utf-8 -*-
#
# Project Ginger S390x
#
# Copyright IBM Corp, 2015-2016
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA


import glob
import re

from wok.exception import OperationFailed
from wok.utils import wok_log


def get_directories(path_pattern):
    """
    this is a method to get list of directories in given directory path
    path_pattern: This is pattern for the path for
          which it will get the directories.
          e.g. if path = "/sys/bus/ccw/drivers/dasd-eckd/*/"
          it return list of all the directories under
          "/sys/bus/ccw/drivers/dasd-eckd/"
          And if path = "/sys/bus/ccw/drivers/dasd-eckd/"
          then it will return just ["dasd-eckd"]
    Returns list of all the directories for given path pattern.
    """
    paths = glob.glob(path_pattern)
    return paths


def get_dirname(path):
    """
    This method extracts last directory name in given path
    :param path: example /usr/lib/
    :return: directory name for valid path separated
            by "/" or None if path is None
            for above example it returns "lib"
    """
    if path:
        split_index = -1
        if path.endswith("/"):
            split_index = -2
        dirname = path.split("/")[split_index]
        return dirname
    else:
        return None


def get_row_data(command_output, header_pattern, value_pattern):
    """
    return a dictionary for particular row, in which row is
    mapped as values to the header keys
    dictionary is prepared based on first matched row
    header pattern and value pattern should be unique to
    retrieve header and particular row in command output

    :param command_output: Command output is provided as input to this api
    :param header_pattern:This pattern is needed to parse the header
        of the command output to define the keys
    :param value_pattern: This pattern is needed to search particular row,
                        the values of the row are assigned to
                        corresponding header key
    :return: dictionary

    eg.
    command_output is as below"
    Device   Subchan.  DevType CU Type Use  PIM PAM POM  CHPIDs
    ----------------------------------------------------------------------
    0.0.0200 0.0.0000  3390/0a 3990/e9 yes  e0  e0  ff   b0b10d00 00000000
    0.0.0201 0.0.0001  3390/0a 3990/e9 yes  e0  e0  ff   b0b10d00 00000000
    0.0.0202 0.0.0002  3390/0c 3990/e9      e0  e0  ff   b0b10d00 00000000

    This will return:
    {"Device":"0.0.0200", "Subchan": "0.0.0000",
                "DevType": "3390/0a", "CU Type":"3990/e9",
                "Use": "yes", "PIM": e0, "PAM": "e0",
                "POM": "ff", "CHPIDs": "b0b10d00 00000000"
    }, the first match to the value_pattern
    """
    header = re.search(header_pattern, command_output, re.M | re.I)
    value = re.search(value_pattern, command_output, re.M | re.I)
    row_data = {}
    if header is None or not header.group():
        wok_log.error("header is empty for given pattern")
        raise OperationFailed("GS390XREG0001E",
                              {'reason': "header is empty for given pattern"})
    elif value:
        if (header.group() != value.group()) and \
                (len(header.groups()) == len(value.groups())):
                for cnt in range(1, len(header.groups())+1):
                    row_data[header.group(cnt)] = value.group(cnt)
    return row_data


def get_rows_info(cmd_output, hdr_pattern, val_pattern, unique_col=None,
                  format_data=None, hdr_index=0, val_start_index=2):
    """
    If unique_col is not None, returns a dictionary with key as
    unique_col's value  and value as dictionary of each row
    in cmd_output (in which row is mapped as values to the header keys)
    If unique_col is None, returns list of dictionary of each row in cmd_output

    header pattern is regular expression for command header and
    value pattern is regular expression to get the rows from the command output

    :param cmd_output: Command output is provided as input to this api
    :param hdr_pattern:This pattern is needed to parse the header of the
        command output to define the keys
    :param val_pattern: This pattern is needed to search particular row,
                        the values of the row are assigned to
                        corresponding header key
    :param unique_col: key/col name for which value in each row is unique
    :param format_data: Callback function to format each row dictionary.
    :param hdr_index: index for header in cmd_output
    :param val_start_index: start index of value row in cmd_output

    by default first row is header and values starts from 3rd row

    :return: dictionary or list
    eg.
    command_output is as below"
    Device   Subchan.  DevType CU Type Use  PIM PAM POM  CHPIDs
    ----------------------------------------------------------------------
    0.0.0200 0.0.0000  3390/0a 3990/e9 yes  e0  e0  ff   b0b10d00 00000000
    0.0.0201 0.0.0001  3390/0a 3990/e9 yes  e0  e0  ff   b0b10d00 00000000
    0.0.0202 0.0.0002  3390/0c 3990/e9      e0  e0  ff   b0b10d00 00000000

    This will return:
    {"0.0.0200":{"Device":"0.0.0200", "Subchan": "0.0.0000",
                 "DevType": "3390/0a", "CU Type":"3990/e9",
                "Use": "yes", "PIM": e0, "PAM": "e0",
                "POM": "ff", "CHPIDs": "b0b10d00 00000000"}
     ......
     } depending on format_data and unique_colname
            if unique_colname is not None
    Otherwise
    [{"Device":"0.0.0200", "Subchan": "0.0.0000",
                 "DevType": "3390/0a", "CU Type":"3990/e9",
                "Use": "yes", "PIM": e0, "PAM": "e0",
                "POM": "ff", "CHPIDs": "b0b10d00 00000000"}
     ......
     ]depending on format_data

    """
    command_out = cmd_output.strip().split("\n")
    if unique_col is not None:
        devices = {}
    else:
        devices = []

    if (hdr_index > len(command_out)-1) or \
            (val_start_index > len(command_out)-1):
        return devices

    header = re.search(hdr_pattern, command_out[hdr_index], re.M | re.I)
    if header is None or not header.group():
        wok_log.error("header is empty for given pattern")
        raise OperationFailed("GS390XREG0001E",
                              {'reason': "header is empty for given pattern"})

    value_pattern = re.compile(val_pattern, re.M | re.I)

    for row in command_out[val_start_index:]:
        value = re.search(value_pattern, row)
        row_data = {}
        if value:
            if (header.group() != value.group()) and \
                    (len(header.groups()) == len(value.groups())):
                for cnt in range(1, len(header.groups())+1):
                    row_data[header.group(cnt)] = value.group(cnt)

                # Get the unique_col value if not return None,
                # as format_data might does pop
                if unique_col:
                    key = row_data.get(unique_col)

                # format the row data if callback format function is not None
                if format_data:
                    row_data = format_data(row_data)

                # If unique col then return dictionary of dictionary
                # else return list of dictionary
                if unique_col:
                    if not key:
                        key = row_data[unique_col]
                    devices[key] = row_data
                else:
                    devices.append(row_data)
    return devices
