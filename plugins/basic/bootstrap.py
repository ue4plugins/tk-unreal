# Copyright (c) 2018 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sys
import os

# Setup sys.path so that we can import our bootstrapper.
plugin_root_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(plugin_root_dir, "python"))

from tk_unreal_basic import plugin_bootstrap
plugin_bootstrap.bootstrap_plugin(plugin_root_dir)
