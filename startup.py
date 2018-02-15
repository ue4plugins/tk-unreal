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
import sys
import pprint

from sgtk.platform import SoftwareLauncher, SoftwareVersion, LaunchInformation


class EngineLauncher(SoftwareLauncher):
    """
    Handles launching an executable. Automatically starts up your engine with
    the current context in the new session of the DCC.
    """

    @property
    def minimum_supported_version(self):
        """
        The minimum software version that is supported by the launcher.
        """
        return "4.19"

    def prepare_launch(self, exec_path, args, file_to_open=None):
        """
        Prepares an environment to launch the DCC that will automatically
        load Toolkit and the engine when the DCC starts.

        :param str exec_path: Path to executable to launch.
        :param str args: Command line arguments as strings.
        :param str file_to_open: (optional) Full path name of a file to open on launch.

        :returns: :class:`LaunchInformation` instance
        """
        required_env = {}
        # Usually DCCs have an environment variable for plugins that need to be loaded.
        # Here we're adding ourselves to that list. We add ourselves to the existing one
        # in fact so we play nice with the current environment.
        required_env["UNREAL_PATH"] = self._join_paths_with_existing_env_paths(
            "UNREAL_PATH", os.path.join(self.disk_location, "startup")
        )

        # Add std context and site info to the env. This will add stuff like which site to
        # connect to, what context to load, etc.
        required_env.update(self.get_standard_plugin_environment())

        # Signals which engine instance from the environment is going to be used.
        required_env["SHOTGUN_ENGINE"] = self.engine_name

        self.logger.debug("Launch environment: %s", pprint.pformat(required_env))
        self.logger.debug("Launch arguments: %s", args)

        return LaunchInformation(exec_path, args, required_env)

    def _join_paths_with_existing_env_paths(self, env_key, startup_path):
        """
        Takes a list of paths  and joins them with existing paths found on the environment variable
        matching the passed env_key. Returns the complete joined path string
        without setting the environment variable.
        :param env_key: the environment variable name who's path values we need to join with our startup paths
        :return: str of the joined environment paths
        """
        # get any existing nuke path to custom gizmos, scripts etc.
        existing_path_str = os.environ.get(env_key, "")
        existing_path_list = existing_path_str.split(os.pathsep)

        # append the toolkit extensions in order to ensure the right integrations execute
        new_path_list = existing_path_list + [startup_path]

        # now filter out any empty strings/paths and join the remainder back together with separators
        return os.pathsep.join(filter(None, new_path_list))

    def scan_software(self):
        """
        Scan the filesystem for DCC executables.

        :return: A list of :class:`SoftwareVersion` objects.
        """

        self.logger.debug("Scanning for Unreal executables...")

        # This piece of boiler-plate code scans for software based and for every version
        # returned checks if the engine actually supports it.
        supported_sw_versions = []
        for sw_version in self._find_software():
            (supported, reason) = self._is_supported(sw_version)
            if supported:
                supported_sw_versions.append(sw_version)
            else:
                self.logger.debug(
                    "SoftwareVersion %s is not supported: %s" %
                    (sw_version, reason)
                )

        return supported_sw_versions

    def _find_software(self):
        """
        Find executables in the default install locations.
        """
        if sys.platform == "darwin":
            location = "/Users/Shared/Epic Games/UE_4.19/Engine/Binaries/Mac/UE4Editor.app/Contents/MacOS/UE4Editor"
        else:
            location = "C:\Program Files\Epic Games\UE_4.19\Engine\Binaries\Win64\UE4Editor.exe"

        yield SoftwareVersion(
            # Version of the DCC.
            "4.19",
            # Name of the project. Certain DCCs like Nuke on Windows have a single executable
            # (Nuke.exe) that can run different products (Nuke, Nuke X, Nuke Studio). This allows
            # to have an name specific for this mix of executable path and command line arguments.
            "Unreal Engine 4",
            # Path to the executable to launch.
            location,
            # Path to the icon of disk representing the engine.
            os.path.join(self.disk_location, "icon_256.png"),
        )
