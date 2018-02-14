# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class UnrealSessionCollector(HookBaseClass):
    """
    Collector that operates on the Unreal session. Should inherit from the basic
    collector hook.

    You can read more about collectors here:
    http://developer.shotgunsoftware.com/tk-multi-publish2/collector.html

    Here's Maya's implementation for reference:
    https://github.com/shotgunsoftware/tk-maya/blob/master/hooks/tk-multi-publish2/basic/collector.py
    """

    @property
    def settings(self):
        """
        Dictionary defining the settings that this collector expects to receive
        through the settings parameter in the process_current_session and
        process_file methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts as
        part of its environment configuration.
        """

        # grab any base class settings
        collector_settings = super(UnrealSessionCollector, self).settings or {}

        # Add setting specific to this collector.

        return collector_settings

    def process_current_session(self, settings, parent_item):
        """
        Analyzes the current session open in Unreal and parents a subtree of
        items under the parent_item passed in.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance

        """
        pass
