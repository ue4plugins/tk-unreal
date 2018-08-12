# This file is based on templates provided and copyrighted by Autodesk, Inc.
# This file has been modified by Epic Games, Inc. and is subject to the license 
# file included in this repository.

import sgtk
import os
import unreal
import datetime

HookBaseClass = sgtk.get_hook_baseclass()


class UnrealAssetPublishPlugin(HookBaseClass):
    """
    Plugin for publishing an Unreal asset.

    This hook relies on functionality found in the base file publisher hook in
    the publish2 app and should inherit from it in the configuration. The hook
    setting for this plugin should look something like this::

        hook: "{self}/publish_file.py:{engine}/tk-multi-publish2/basic/publish_session.py"

    To learn more about writing a publisher plugin, visit
    http://developer.shotgunsoftware.com/tk-multi-publish2/plugin.html
    """

    # NOTE: The plugin icon and name are defined by the base file plugin.

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """

        return """Publishes the asset to Shotgun. A <b>Publish</b> entry will be
        created in Shotgun which will include a reference to the exported asset's current
        path on disk. Other users will be able to access the published file via
        the <b>Loader</b> app so long as they have access to
        the file's location on disk."""

    @property
    def settings(self):
        """
        Dictionary defining the settings that this plugin expects to receive
        through the settings parameter in the accept, validate, publish and
        finalize methods.

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

        # inherit the settings from the base publish plugin
        base_settings = super(UnrealAssetPublishPlugin, self).settings or {}

        # Here you can add any additional settings specific to this plugin
        publish_template_setting = {
            "Publish Template": {
                "type": "template",
                "default": None,
                "description": "Template path for published work files. Should"
                               "correspond to a template defined in "
                               "templates.yml.",
            }
        }

        # update the base settings
        base_settings.update(publish_template_setting)

        return base_settings

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """
        return ["unreal.asset.StaticMesh"]

    def accept(self, settings, item):
        """
        Method called by the publisher to determine if an item is of any
        interest to this plugin. Only items matching the filters defined via the
        item_filters property will be presented to this method.

        A publish task will be generated for each item accepted here. Returns a
        dictionary with the following booleans:

            - accepted: Indicates if the plugin is interested in this value at
                all. Required.
            - enabled: If True, the plugin will be enabled in the UI, otherwise
                it will be disabled. Optional, True by default.
            - visible: If True, the plugin will be visible in the UI, otherwise
                it will be hidden. Optional, True by default.
            - checked: If True, the plugin will be checked in the UI, otherwise
                it will be unchecked. Optional, True by default.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: dictionary with boolean keys accepted, required and enabled
        """
        
        accepted = True
        publisher = self.parent

        # ensure the publish template is defined
        publish_template_setting = settings.get("Publish Template")
        publish_template = publisher.get_template_by_name(publish_template_setting.value)
        if not publish_template:
            self.logger.debug(
                "A publish template could not be determined for the "
                "asset item. Not accepting the item."
            )
            accepted = False

        # we've validated the work and publish templates. add them to the item properties
        # for use in subsequent methods
        item.properties["publish_template"] = publish_template

        return {
            "accepted": accepted,
            "checked": True
        }

    def validate(self, settings, item):
        """
        Validates the given item to check that it is ok to publish. Returns a
        boolean to indicate validity.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        :returns: True if item is valid, False otherwise.
        """
        # raise an exception here if something is not valid.
        # If you use the logger, warnings will appear in the validation tree.
        # You can attach callbacks that allow users to fix these warnings
        # at the press of a button.
        #
        # For example:
        #
        # self.logger.info(
        #         "Your session is not part of a maya project.",
        #         extra={
        #             "action_button": {
        #                 "label": "Set Project",
        #                 "tooltip": "Set the maya project",
        #                 "callback": lambda: mel.eval('setProject ""')
        #             }
        #         }
        #     )

        asset_path = item.properties.get("asset_path")
        asset_name = item.properties.get("asset_name")
        if not asset_path or not asset_name:
            self.logger.debug("Asset path or name not configured.")
            return False

        publish_template = item.properties.get("publish_template")
        if not publish_template:
            self.logger.debug("No publish template configured.")
            return False

        # Add the Unreal asset name to the fields
        fields = {"name" : asset_name}

        # Add today's date to the fields
        date = datetime.date.today()
        fields["YYYY"] = date.year
        fields["MM"] = date.month
        fields["DD"] = date.day

        # Stash the Unrea asset path and name in properties
        item.properties["asset_path"] = asset_path
        item.properties["asset_name"] = asset_name

        # Get destination path for exported FBX from publish template
        # which should be project root + publish template
        publish_path = publish_template.apply_fields(fields)
        publish_path = os.path.normpath(publish_path)
        item.properties["path"] = publish_path

        # Remove the filename from the work path
        destination_path = os.path.split(publish_path)[0]

        # Stash the destination path in properties
        item.properties["destination_path"] = destination_path

        # Set the Published File Type
        item.properties["publish_type"] = "Unreal FBX"

        # run the base class validation
        # return super(UnrealAssetPublishPlugin, self).validate(settings, item)

        return True

    def publish(self, settings, item):
        """
        Executes the publish logic for the given item and settings.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        # This is where you insert custom information into `item`, like the
        # path of the file being published or any dependency this publish
        # has on other publishes.

        # get the path in a normalized state. no trailing separator, separators
        # are appropriate for current os, no double separators, etc.

        # Ensure that the destination path exists before exporting since the
        # Unreal FBX exporter doesn't check that
        destination_path = item.properties["destination_path"]
        self.parent.ensure_folder_exists(destination_path)

        # Export the asset from Unreal
        asset_path = item.properties["asset_path"]
        asset_name = item.properties["asset_name"]
        try:
            _unreal_export_asset_to_fbx(destination_path, asset_path, asset_name)
        except Exception:
            self.logger.debug("Asset %s cannot be exported to FBX." % (asset_path))
        
        # let the base class register the publish
        # the publish_file will copy the file from the work path to the publish path
        # if the item is provided with the worK_template and publish_template properties
        super(UnrealAssetPublishPlugin, self).publish(settings, item)

    def finalize(self, settings, item):
        """
        Execute the finalization pass. This pass executes once all the publish
        tasks have completed, and can for example be used to version up files.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """
        # do the base class finalization
        super(UnrealAssetPublishPlugin, self).finalize(settings, item)

def _unreal_export_asset_to_fbx(destination_path, asset_path, asset_name):
    """
    Export an asset to FBX from Unreal

    :param destination_path: The path where the exported FBX will be placed
    :param asset_path: The Unreal asset to export to FBX
    :param asset_name: The asset name to use for the FBX filename
    """
    # Get an export task
    task = _generate_fbx_export_task(destination_path, asset_path, asset_name)
    if not task:
        return False, None

    # Do the FBX export
    result = unreal.Exporter.run_asset_export_task(task)

    if not result:
        unreal.log_error("Failed to export {}".format(task.filename))
        for error_msg in task.errors:
            unreal.log_error("{}".format(error_msg))

        return result, None

    return result, task.filename
    
def _generate_fbx_export_task(destination_path, asset_path, asset_name):
    """
    Create and configure an Unreal AssetExportTask

    :param destination_path: The path where the exported FBX will be placed
    :param asset_path: The Unreal asset to export to FBX
    :param asset_name: The FBX filename to export to
    :return the configured AssetExportTask
    """
    loaded_asset = unreal.EditorAssetLibrary.load_asset(asset_path)

    if not loaded_asset:
        unreal.log_error("Failed to create FBX export task for {}: Could not load asset {}".format(asset_name, asset_path))
        return None
        
    filename = os.path.join(destination_path, asset_name + ".fbx")
    
    # Setup AssetExportTask for non-interactive mode
    task = unreal.AssetExportTask()
    task.object = loaded_asset      # the asset to export
    task.filename = filename        # the filename to export as
    task.automated = True           # don't display the export options dialog
    task.replace_identical = True   # always overwrite the output
    
    # Setup export options for the export task
    task.options = unreal.FbxExportOption()
    # These are the default options for the FBX export
    # task.options.fbx_export_compatibility = fbx_2013
    # task.options.ascii = False
    # task.options.force_front_x_axis = False
    # task.options.vertex_color = True
    # task.options.level_of_detail = True
    # task.options.collision = True
    # task.options.welded_vertices = True
    # task.options.map_skeletal_motion_to_root = False
    
    return task
