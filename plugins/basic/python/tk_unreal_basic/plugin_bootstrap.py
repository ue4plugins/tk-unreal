# This file is based on templates provided and copyrighted by Autodesk, Inc.
# This file has been modified by Epic Games, Inc. and is subject to the license
# file included in this repository.


from __future__ import print_function
import sys
import os
import logging


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

        _initialize_logger(sgtk.LogManager())

        manager = sgtk.bootstrap.ToolkitManager()
        manager.progress_callback = lambda pct, msg: print(
            "%s - %s" % (int(pct * 100), msg)
        )
        manifest.initialize_manager(manager, plugin_root_path)
    else:
        manager = _initialize_manager(plugin_root_path)

    # synchronous
    manager.bootstrap_engine(
        os.environ.get("SHOTGUN_ENGINE", "tk-unreal"),
        manager.get_entity_from_environment()
    )
    _on_engine_initialized()

    # asynchronous doesn't work for now
#     manager.bootstrap_engine_async(
#         os.environ.get("SHOTGUN_ENGINE", "tk-unreal"),
#         manager.get_entity_from_environment(),
#         _on_engine_initialized
#     )


def _on_engine_initialized():
    import sgtk

    sgtk_logger = sgtk.LogManager.get_logger("plugin")
    sgtk_logger.debug("tk-unreal finished initialization.")

    import unreal

    # ShotgunEngine was renamed to ShotgridEngine from UE5
    if hasattr(unreal, "ShotgridEngine"):
        unreal.ShotgridEngine.get_instance().on_engine_initialized()
    else:
        unreal.ShotgunEngine.get_instance().on_engine_initialized()

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
        plugin_info = yaml.load(plugin_info_fh, yaml.SafeLoader)

    base_config = plugin_info["base_configuration"]
    plugin_id = plugin_info["plugin_id"]

    import sgtk

    _initialize_logger(sgtk.LogManager())

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
    toolkit_mgr.base_configuration = base_config
    toolkit_mgr.plugin_id = plugin_id

    return toolkit_mgr


def _initialize_logger(log_manager):
    # start logging to log file
    log_manager.initialize_base_file_handler("tk-unreal")

    # force the StreamHandler to output to stdout instead of stderr
    handler = logging.StreamHandler(sys.stdout)
    # create formatter that follows this pattern: [DEBUG tank.log] message
    formatter = logging.Formatter(
        "[%(levelname)s %(name)s] %(message)s"
    )
    handler.setFormatter(formatter)

    log_manager.initialize_custom_handler(handler)
