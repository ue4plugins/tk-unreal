# This file is based on templates provided and copyrighted by Autodesk, Inc.
# This file has been modified by Epic Games, Inc. and is subject to the license
# file included in this repository.

import sgtk
import os


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
        work_template_setting = {
            "Work Template": {
                "type": "template",
                "default": None,
                "description": "Template path for artist work files. Should "
                               "correspond to a template defined in "
                               "templates.yml. If configured, is made available"
                               "to publish plugins via the collected item's "
                               "properties. ",
            },
        }

        collector_settings.update(work_template_setting)

        return collector_settings

    def process_current_session(self, settings, parent_item):
        """
        Analyzes the current session in Unreal and parents a subtree of
        items under the parent_item passed in.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance
        """
        # Create an item representing the current Unreal session
        parent_item = self.collect_current_session(settings, parent_item)

        # Collect assets selected in Unreal
        self.collect_selected_assets(parent_item)

    def collect_current_session(self, settings, parent_item):
        """
        Creates an item that represents the current Unreal session.

        :param dict settings: Configured settings for this collector
        :param parent_item: Parent Item instance

        :returns: Item of type unreal.session
        """
        # Create the session item for the publish hierarchy
        # In Unreal, the current session can be defined as the current level/map (.umap)
        # Don't create a session item for now since the .umap does not need to be published
        session_item = parent_item

        # Get the icon path to display for this item
        icon_path = os.path.join(
            self.disk_location,
            os.pardir,
            "icons",
            "unreal.png"
        )

        # Set the icon for the session item
        # Will also be used for the children items parented to the session item
        session_item.set_icon_from_path(icon_path)

        # Set the project root
        unreal_sg = sgtk.platform.current_engine().unreal_sg_engine
        project_root = unreal_sg.get_shotgun_work_dir()

        # Important to convert "/" in path returned by Unreal to "\" for templates to work
        project_root = project_root.replace("/", "\\")
        session_item.properties["project_root"] = project_root

        self.logger.info("Current Unreal project folder is: %s." % (project_root))

        # If a work template is defined, add it to the item properties so
        # that it can be used by publish plugins
        work_template_setting = settings.get("Work Template")
        if work_template_setting:
            publisher = self.parent
            work_template = publisher.get_template_by_name(work_template_setting.value)

            if work_template:
                # Override the work template to use the project root from Unreal and not the default root for templates
                work_template = sgtk.TemplatePath(work_template.definition, work_template.keys, project_root)

                session_item.properties["work_template"] = work_template
                self.logger.debug("Work template defined for Unreal collection.")

        self.logger.info("Collected current Unreal session")

        return session_item

    def collect_selected_assets(self, parent_item):
        """
        Creates items for assets selected in Unreal.

        :param parent_item: Parent Item instance
        """
        unreal_sg = sgtk.platform.current_engine().unreal_sg_engine

        # Iterate through the selected assets and get their info and add them as items to be published
        for asset in unreal_sg.selected_assets:
            asset_name = str(asset.asset_name)
            asset_type = str(asset.asset_class)

            item_type = "unreal.asset." + asset_type
            asset_item = parent_item.create_item(
                item_type,     # Include the asset type for the publish plugin to use
                asset_type,    # display type
                asset_name     # display name of item instance
            )

            # Asset properties that can be used by publish plugins
            asset_item.properties["asset_path"] = asset.object_path
            asset_item.properties["asset_name"] = asset_name
            asset_item.properties["asset_type"] = asset_type
