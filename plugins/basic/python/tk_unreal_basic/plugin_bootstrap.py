# Copyright (c) 2018 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.


from __future__ import print_function
import sys
import os


def bootstrap_plugin(plugin_root_path):

    # Add the python subfolder to the PYTHONPATH.
    plugin_python_path = os.path.join(plugin_root_path, "python")
    sys.path.insert(0, plugin_python_path)

    try:
        # When a Toolkit plugin is compiled into a baked plugin for distribution
        # with a DCC, a special module and manifest is created in the build.
        from sgtk_plugin_basic_unreal import manifest
        running_stand_alone = True
    except ImportError:
        manifest = None
        running_stand_alone = False

    if running_stand_alone:
        # running stand alone. import core from the manifest's core path and
        # extract the plugin info from the manifest

        # Retrieve the Shotgun toolkit core included with the plug-in and
        # prepend its python package path to the python module search path.
        # this will allow us to import sgtk
        tk_core_python_path = manifest.get_sgtk_pythonpath(plugin_root_path)
        sys.path.insert(0, tk_core_python_path)

        import sgtk

        sgtk.LogManager().initialize_base_file_handler("tk-unreal")
        sgtk.LogManager().initialize_custom_handler()

        manager = sgtk.bootstrap.ToolkitManager()
        manager.progress_callback = lambda pct, msg: print(
            "%s - %s" % (int(pct * 100), msg)
        )
        manifest.initialize_manager(manager, plugin_root_path)
    else:
        manager = _initialize_manager(plugin_root_path)

    manager.bootstrap_engine(
        os.environ.get("SHOTGUN_ENGINE", "tk-unreal"),
        manager.get_entity_from_environment()
    )


def _initialize_manager(plugin_root_path):
    """
    Initializes a ToolkitManager for use in zero-config mode.
    """
    # running in situ as part of zero config. sgtk has already added sgtk
    # to the python path. need to extract the plugin info from info.yml

    # import the yaml parser
    from tank_vendor import yaml

    # build the path to the info.yml file
    plugin_info_yml = os.path.join(plugin_root_path, "info.yml")

    # open the yaml file and read the data
    with open(plugin_info_yml, "r") as plugin_info_fh:
        plugin_info = yaml.load(plugin_info_fh)

    base_config = plugin_info["base_configuration"]
    plugin_id = plugin_info["plugin_id"]

    import sgtk

    # start logging to log file
    sgtk.LogManager().initialize_base_file_handler("tk-unreal")
    sgtk.LogManager().initialize_custom_handler()

    # get a logger for the plugin
    sgtk_logger = sgtk.LogManager.get_logger("plugin")
    sgtk_logger.debug("Booting up toolkit plugin.")

    sgtk_logger.debug("Executable: %s", sys.executable)

    try:
        # Authenticates with Toolkit. If already logged in, this will
        # return the current user.
        user = sgtk.authentication.ShotgunAuthenticator().get_user()
    except sgtk.authentication.AuthenticationCancelled:
        # Show a "Shotgun > Login" menu.
        sgtk_logger.info("Shotgun login was cancelled by the user.")
        return

    # Create a boostrap manager for the logged in user with the plug-in
    # configuration data.
    toolkit_mgr = sgtk.bootstrap.ToolkitManager(user)

    toolkit_mgr.progress_callback = lambda pct, msg: print("{0} - {1}".format(int(pct * 100), msg))

    # Pulls the latest Unreal configuration from the master branch.
    # toolkit_mgr.base_configuration = "sgtk:descriptor:git_branch?path={0}&branch={1}".format(
    #     "git@github.com:shotgunsoftware/tk-config-unreal.git",
    #     "master"
    # )
    toolkit_mgr.do_shotgun_config_lookup = False
    toolkit_mgr.base_configuration = base_config
    toolkit_mgr.plugin_id = plugin_id

    return toolkit_mgr
