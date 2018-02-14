# Copyright (c) 2018 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import pprint

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class UnrealActions(HookBaseClass):
    """
    Shotgun Panel Actions for Unreal
    """

    def generate_actions(self, sg_data, actions, ui_area):
        """
        Returns a list of action instances for a particular object.
        The data returned from this hook will be used to populate the
        actions menu.

        The mapping between Shotgun objects and actions are kept in a different place
        (in the configuration) so at the point when this hook is called, the app
        has already established *which* actions are appropriate for this object.

        This method needs to return detailed data for those actions, in the form of a list
        of dictionaries, each with name, params, caption and description keys.

        The ui_area parameter is a string and indicates where the item is to be shown.

        - If it will be shown in the main browsing area, "main" is passed.
        - If it will be shown in the details area, "details" is passed.

        :param sg_data: Shotgun data dictionary with all the standard shotgun fields.
        :param actions: List of action strings which have been defined in the app configuration.
        :param ui_area: String denoting the UI Area (see above).
        :returns List of dictionaries, each with keys name, params, caption and description
        """
        app = self.parent
        app.log_debug("Generate actions called for UI element %s. "
                      "Actions: %s. Shotgun Data: %s" % (ui_area, actions, sg_data))

        action_instances = []

        try:
            # call base class first
            action_instances += HookBaseClass.generate_actions(self, sg_data, actions, ui_area)
        except AttributeError:
            # base class doesn't have the method, so ignore and continue
            pass

        if "reference" in actions:
            action_instances.append({"name": "reference",
                                     "params": None,
                                     "caption": "Create Reference",
                                     "description": "This will add the item to the scene as a standard reference."})

        return action_instances

    def execute_action(self, name, params, sg_data):
        """
        Execute a given action. The data sent to this be method will
        represent one of the actions enumerated by the generate_actions method.

        :param name: Action name string representing one of the items returned by generate_actions.
        :param params: Params data, as specified by generate_actions.
        :param sg_data: Shotgun data dictionary
        :returns: No return value expected.
        """
        app = self.parent
        app.log_debug("Execute action called for action %s. "
                      "Parameters: %s. Shotgun Data: %s" % (name, params, sg_data))

        if name == "reference":
            path = self.get_publish_path(sg_data)
            self._create_reference(path, sg_data)
        else:
            try:
                HookBaseClass.execute_action(self, name, params, sg_data)
            except AttributeError:
                # base class doesn't have the method, so ignore and continue
                pass

    ##############################################################################################################
    # helper methods which can be subclassed in custom hooks to fine tune the behaviour of things

    def _create_reference(self, path, sg_publish_data):
        """
        Create a reference.

        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """
        if not os.path.exists(path):
            raise Exception("File not found on disk - '%s'" % path)

        print("Path %s: " % path)
        print("Publish data:")
        pprint.pprint(sg_publish_data)
