# This file is based on templates provided and copyrighted by Autodesk, Inc.
# This file has been modified by Epic Games, Inc. and is subject to the license 
# file included in this repository.

import os
import re
import sys
import pprint
import json

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
        return "4.20"

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

        # TODO: Get the startup project from settings somewhere, for now hardcoded
        # Otherwise, leave it empty and the project selection window will appear
        # (the command-line arguments are forwarded to the new instance of Unreal Editor)
        unreal_project = ""
        args = args + unreal_project
        
        # Set the bootstrap location in the environment variable that will be used by the Unreal Shotgun startup script
        bootstrap_script = os.path.join(self.disk_location, "plugins", "basic", "bootstrap.py")
        required_env["UE_SHOTGUN_BOOTSTRAP"] = bootstrap_script
        
        self.logger.debug("Executable path: %s", exec_path)
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
        # get any existing path for the given env_key
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
        Find executables in the Windows Registry.

        :returns: List of :class:`SoftwareVersion` instances
        """
        print("Finding Unreal Engine executables")
        
        # Determine a list of paths to search for Unreal Editor executables based on the windows registry
        search_paths = _get_installation_paths_from_registry(self.logger)
        sw_versions = self._get_software_from_search_paths(search_paths, "Unreal Engine")

        # Also look for custom developer builds
        search_paths = _get_development_builds_paths_from_registry(self.logger)
        sw_versions = sw_versions + self._get_software_from_search_paths(search_paths, "Unreal Engine (Dev Build)")

        return sw_versions
        
    def _get_software_from_search_paths(self, search_paths, display_name):
        sw_versions = []
        for search_path in search_paths:
            # Construct the expected executable name for this path.
            # If it exists, add it to the list of exec_paths to check.
            exec_path, executable_version = self._find_exec_and_version(search_path)

            if exec_path:
                # Create a SoftwareVersion using the information from executable
                # path(s) found in default locations.
                self.logger.debug("Creating SoftwareVersion for executable '%s'." % exec_path)
                sw_versions.append(SoftwareVersion(
                    executable_version,
                    display_name,
                    exec_path,
                    os.path.join(self.disk_location, "icon_256.png")
                ))
        
        return sw_versions
        
    def _find_exec_and_version(self, root_path):
        # With the given root path, check if there's an Unreal executable in it and its version
        binary_folder = "Engine\\Binaries\\Win64"
        executable_filename = "UE4Editor.exe"
        version_filename = "UE4Editor.version"

        # Construct the expected executable name for this root path.
        exec_path = os.path.join(root_path, binary_folder, executable_filename)
        exec_path = os.path.normpath(exec_path)
        versionfile_path = os.path.join(root_path, binary_folder, version_filename)
        self.logger.debug("Checking installation path %s" % exec_path)

        if os.path.exists(exec_path):
            self.logger.debug("Found executable in installation path %s" % exec_path)
            
            if os.path.exists(versionfile_path):
                self.logger.debug("Version file found in installation path %s" % versionfile_path)
            else:
                self.logger.debug("Version file not found in installation path %s" % versionfile_path)
                versionfile_path = None
        else:
            return None, None

        sw_versions = []
        executable_version = "0"
        # First, try to find the executable version from the version file
        if versionfile_path is not None:
            self.logger.debug("Parsing version from file '%s'." % versionfile_path)
            version_data = json.load(open(versionfile_path))
            executable_version = str(version_data["MajorVersion"]) + "." + str(version_data["MinorVersion"]) + "." + str(version_data["PatchVersion"])
        else:
            # As a fallback method:
            # Check to see if the version number can be parsed from the path name.
            # It's expected to find a subdir named "ue_x.yy", where x is the major, and yy the minor version
            self.logger.debug("Parsing version from path '%s'." % exec_path)
            path_sw_versions = [p.lower() for p in exec_path.split(os.path.sep)
                                if re.match("ue_[0-9]+[.0-9]*$", p.lower()) is not None
                                ]
            if path_sw_versions:
                # Use this sub dir to determine the version of the executable
                executable_version = path_sw_versions[0].replace("ue_", "")
                self.logger.debug(
                    "Resolved version '%s' from executable '%s'." %
                    (executable_version, exec_path)
            )
            
        return exec_path, executable_version

def _get_installation_paths_from_registry(logger):
    """
    Query Windows registry for Unreal installations.

    :returns: List of paths where Unreal is installed
    """
    import _winreg
    logger.debug("Querying windows registry for key HKEY_LOCAL_MACHINE\\SOFTWARE\\EpicGames\\Unreal Engine")

    base_key_name = "SOFTWARE\\EpicGames\\Unreal Engine"
    sub_key_names = []

    # find all subkeys in key HKEY_LOCAL_MACHINE\SOFTWARE\EpicGames\Unreal Engine
    try:
        key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, base_key_name)
        sub_key_count = _winreg.QueryInfoKey(key)[0]
        i = 0
        while i < sub_key_count:
            sub_key_names.append(_winreg.EnumKey(key, i))
            i += 1
        _winreg.CloseKey(key)
    except WindowsError:
        logger.error("error opening key %s" % base_key_name)

    install_paths = []
    # Query the value "InstalledDirectory" on all subkeys.
    try:
        for name in sub_key_names:
            key_name = base_key_name + "\\" + name
            key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, key_name)
            try:
                install_paths.append(_winreg.QueryValueEx(key, "InstalledDirectory")[0])
                logger.debug("Found InstalledDirectory value for key %s" % key_name)
            except WindowsError:
                logger.debug("value InstalledDirectory not found for key %s, skipping key" % key_name)
            _winreg.CloseKey(key)
    except WindowsError:
        logger.error("error opening key %s" % key_name)

    return install_paths

def _get_development_builds_paths_from_registry(logger):
    """
    Query Windows registry for Unreal custom developer builds.

    :returns: List of paths where Unreal executable is found
    """
    import _winreg
    logger.debug("Querying windows registry for key HKEY_CURRENT_USER\\SOFTWARE\\Epic Games\\Unreal Engine\\Builds")

    base_key_name = "SOFTWARE\\Epic Games\\Unreal Engine\\Builds"
    install_paths = []

    # find all values in key HKEY_CURRENT_USER\SOFTWARE\Epic Games\Unreal Engine\Builds
    try:
        key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, base_key_name)
        values_count = _winreg.QueryInfoKey(key)[1]
        logger.debug("Found %d values." % values_count)
        i = 0
        while i < values_count:
            value = _winreg.EnumValue(key, i)
            install_paths.append(value[1])
            logger.debug("Found Unreal executable path '%s'." % value[1])
            i += 1
        _winreg.CloseKey(key)
    except WindowsError:
        logger.error("error opening key %s" % base_key_name)

    return install_paths
    