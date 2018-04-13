# Copyright (c) 2018 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Hook that loads defines all the available actions, broken down by publish type.
"""

import pprint
import os
import sgtk
import unreal

HookBaseClass = sgtk.get_hook_baseclass()


class UnrealActions(HookBaseClass):

    ##############################################################################################################
    # public interface - to be overridden by deriving classes

    def generate_actions(self, sg_publish_data, actions, ui_area):
        """
        Returns a list of action instances for a particular publish.
        This method is called each time a user clicks a publish somewhere in the UI.
        The data returned from this hook will be used to populate the actions menu for a publish.

        The mapping between Publish types and actions are kept in a different place
        (in the configuration) so at the point when this hook is called, the loader app
        has already established *which* actions are appropriate for this object.

        The hook should return at least one action for each item passed in via the
        actions parameter.

        This method needs to return detailed data for those actions, in the form of a list
        of dictionaries, each with name, params, caption and description keys.

        Because you are operating on a particular publish, you may tailor the output
        (caption, tooltip etc) to contain custom information suitable for this publish.

        The ui_area parameter is a string and indicates where the publish is to be shown.
        - If it will be shown in the main browsing area, "main" is passed.
        - If it will be shown in the details area, "details" is passed.
        - If it will be shown in the history area, "history" is passed.

        Please note that it is perfectly possible to create more than one action "instance" for
        an action! You can for example do scene introspection - if the action passed in
        is "character_attachment" you may for example scan the scene, figure out all the nodes
        where this object can be attached and return a list of action instances:
        "attach to left hand", "attach to right hand" etc. In this case, when more than
        one object is returned for an action, use the params key to pass additional
        data into the run_action hook.

        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        :param actions: List of action strings which have been defined in the app configuration.
        :param ui_area: String denoting the UI Area (see above).
        :returns List of dictionaries, each with keys name, params, caption and description
        """
        app = self.parent
        app.log_debug("Generate actions called for UI element %s. "
                      "Actions: %s. Publish Data: %s" % (ui_area, actions, sg_publish_data))

        action_instances = []

        if "import_content" in actions:
            action_instances.append({"name": "import_content",
                                     "params": None,
                                     "caption": "Import into Content Browser",
                                     "description": "This will import the asset into the Unreal Editor Content Browser."})
        
        return action_instances

    def execute_multiple_actions(self, actions):
        """
        Executes the specified action on a list of items.

        The default implementation dispatches each item from ``actions`` to
        the ``execute_action`` method.

        The ``actions`` is a list of dictionaries holding all the actions to execute.
        Each entry will have the following values:

            name: Name of the action to execute
            sg_publish_data: Publish information coming from Shotgun
            params: Parameters passed down from the generate_actions hook.

        .. note::
            This is the default entry point for the hook. It reuses the ``execute_action``
            method for backward compatibility with hooks written for the previous
            version of the loader.

        .. note::
            The hook will stop applying the actions on the selection if an error
            is raised midway through.

        :param list actions: Action dictionaries.
        """
        for single_action in actions:
            name = single_action["name"]
            sg_publish_data = single_action["sg_publish_data"]
            params = single_action["params"]
            self.execute_action(name, params, sg_publish_data)

    def execute_action(self, name, params, sg_publish_data):
        """
        Execute a given action. The data sent to this be method will
        represent one of the actions enumerated by the generate_actions method.

        :param name: Action name string representing one of the items returned by generate_actions.
        :param params: Params data, as specified by generate_actions.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        :returns: No return value expected.
        """
        app = self.parent
        app.log_debug("Execute action called for action %s. "
                      "Parameters: %s. Publish Data: %s" % (name, params, sg_publish_data))

        # resolve path
        path = self.get_publish_path(sg_publish_data)

        if name == "import_content":
            self._import_to_content_browser(path, sg_publish_data)
        else:
            try:
                HookBaseClass.execute_action(self, name, params, sg_publish_data)
            except AttributeError:
                # base class doesn't have the method, so ignore and continue
                pass

    def _import_to_content_browser(self, path, sg_publish_data):
        """
        Import the asset into the Unreal Content Browser.

        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """
        
        unreal.log("File to import: {}".format(path))

        if not os.path.exists(path):
            raise Exception("File not found on disk - '%s'" % path)

        destination_path, destination_name = self._get_destination_path_and_name(sg_publish_data)
        
        _unreal_import_fbx_asset(path, destination_path, destination_name)

    ##############################################################################################################
    # helper methods which can be subclassed in custom hooks to fine tune the behaviour of things
        
    def _get_destination_path_and_name(self, sg_publish_data):
        """
        Get the destination path and name from the publish data and the templates

        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        :return destination_path that matches a template and destination_name from asset or published file
        """
        # Enable if needed while in development
        # self.sgtk.reload_templates()

        # Get the publish context which should be for an asset, task or project
        context = self.sgtk.context_from_entity_dictionary(sg_publish_data)
        # unreal.log("Publish data Context: {}".format(context))

        # Query the fields that will be applied to templates
        # We will select a template that matches the fields available
        query_template = self.sgtk.templates["unreal_fields_query"]
        fields = context.as_template_fields(query_template)
        unreal.log("Template fields: {}".format(fields))

        # By default, use the most basic template based on asset type and name
        destination_template = self.sgtk.templates["unreal_asset_template"]
        
        if fields:
            # Check for project-specific templates that use specific fields
            if fields["sg_category_3"] is not None:
                destination_template = self.sgtk.templates["unreal_asset_3_categories"]
            elif fields["sg_category_2"] is not None:
                destination_template = self.sgtk.templates["unreal_asset_2_categories"]
            elif fields["sg_category_1"] is not None:
                destination_template = self.sgtk.templates["unreal_asset_1_category"]
            elif fields["sg_asset_type"] is None:
            # Case of asset with no type
                destination_template = self.sgtk.templates["unreal_asset_notype"]
        else:
            # fields is empty in the case of the project context, which indicates
            # that we are trying to load a published file not linked to any task or asset
            # In that case, use the published file template
            destination_template = self.sgtk.templates["unreal_published_file"]
            
            # Derive the destination name from the published file name without the extension
            name = sg_publish_data["code"]
            name = os.path.splitext(name)[0]
            unreal.log("Published file name: {}".format(name))
            
            # Add it as sg_asset_name in fields to apply it to the template
            fields["sg_asset_name"] = name
        
        unreal.log("Selected destination template: {}".format(destination_template))
        destination_path = destination_template.apply_fields(fields)
        unreal.log("Destination path after applying fields: {}".format(destination_path))
        
        destination_name = None
        if "sg_asset_name" in fields:
            destination_name = fields["sg_asset_name"]
            
        return destination_path, destination_name
        
"""
Functions to import FBX into Unreal
"""

def _unreal_import_fbx_asset(input_path, destination_path, destination_name):
    """
    Import an FBX into Unreal Content Browser

    :param input_path: The fbx file to import
    :param destination_path: The Content Browser path where the asset will be placed
    :param destination_name: The asset name to use; if None, will use the filename without extension
    """
    tasks = []
    tasks.append(_generate_fbx_import_task(input_path, destination_path, destination_name))
    
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(False, True)
    
    for task in tasks:
        unreal.log("Import Task for: {}".format(task.filename))
        for object_path in task.imported_object_paths:
            unreal.log("Imported object: {}".format(object_path))
        
def _generate_fbx_import_task(filename, destination_path, destination_name=None, replace_existing=True,
                             automated=True, save=True, materials=True,
                             textures=True, as_skeletal=False):
    """
    Create and configure an Unreal AssetImportTask

    :param filename: The fbx file to import
    :param destination_path: The Content Browser path where the asset will be placed
    :return the configured AssetImportTask
    """
    task = unreal.AssetImportTask()
    task.filename = filename
    task.destination_path = destination_path
    
    # By default, destination_name is the filename without the extension
    if destination_name is not None:
        task.destination_name = destination_name
        
    task.replace_existing = replace_existing
    task.automated = automated
    task.save = save

    task.options = unreal.FbxImportUI()
    task.options.import_materials = materials
    task.options.import_textures = textures
    task.options.import_as_skeletal = as_skeletal
    # task.options.static_mesh_import_data.combine_meshes = True

    task.options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    if as_skeletal:
        task.options.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH

    return task
