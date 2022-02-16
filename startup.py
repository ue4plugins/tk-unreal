# This file is based on templates provided and copyrighted by Autodesk, Inc.
# This file has been modified by Epic Games, Inc. and is subject to the license
# file included in this repository.

import os
import sys
import pprint
import json
import re

import sgtk
from sgtk.platform import SoftwareLauncher, SoftwareVersion, LaunchInformation


class EngineLauncher(SoftwareLauncher):
    """
    Handles launching an executable. Automatically starts up your engine with
    the current context in the new session of the DCC.
    """

    # Named regex strings to insert into the executable template paths when
    # matching against supplied versions and products. Similar to the glob
    # strings, these allow us to alter the regex matching for any of the
    # variable components of the path in one place
    # We match 4.27, 5.0EA
    COMPONENT_REGEX_LOOKUP = {"version": r"\d+\.\d+\w*", "major": r"\d+"}

    # This dictionary defines a list of executable template strings for each
    # of the supported operating systems. The templates are used for both
    # globbing and regex matches by replacing the named format placeholders
    # with an appropriate glob or regex string.
    # Note: Software entities need to be manually added by users in SG for Linux
    # since there is no standard installation path.
    EXECUTABLE_TEMPLATES = {
        "darwin": [
            "/Users/Shared/Epic Games/UE_{version}/Engine/Binaries/Mac/UE{major}Editor.app",
            "/Users/Shared/Epic Games/UE_{version}/Engine/Binaries/Mac/UnrealEditor.app"
        ],
        "win32": [
            "C:/Program Files/Epic Games/UE_{version}/Engine/Binaries/Win64/UE{major}Editor.exe",
            "C:/Program Files/Epic Games/UE_{version}/Engine/Binaries/Win64/UnrealEditor.exe"
        ],
    }

    @property
    def minimum_supported_version(self):
        """
        The minimum software version that is supported by the launcher.

        :returns: A string.
        """
        return "4.20"

    def prepare_launch(self, exec_path, args, file_to_open=None):
        """
        Prepares an environment to launch the DCC that will automatically
        load Toolkit and the engine when the DCC starts.

        :param str exec_path: Path to executable to launch.
        :param str args: Command line arguments as strings.
        :param str file_to_open: (optional) Full path name of a file to open on launch.

        :returns: A :class:`LaunchInformation` instance.
        """
        # TODO: Get the startup project from settings somewhere, for now hardcoded
        # Otherwise, leave it empty and the project selection window will appear
        # (the command-line arguments are forwarded to the new instance of Unreal Editor)
        unreal_project = ""
        args = args + unreal_project
        required_env = {}
        # Creating a QApplication in Unreal on Mac crashes it, so disable the
        # SG TK integration for now, just run the executable with its args. This
        # allows to launch Unreal from tk-desktop or submit turntable renders
        # from Maya to Unreal, without the integration crashing Unreal.
        if sys.platform == "darwin":
            self.logger.warning("SG TK Unreal integration is not available on Mac.")
            return LaunchInformation(exec_path, args, required_env)

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
        matching the passed env_key.

        Returns the complete joined path string without setting the environment variable.

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
        Scan the filesystem for UE executables.

        :returns: A list of :class:`SoftwareVersion` objects.
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
        Find installed UE executable.

        :returns: List of :class:`SoftwareVersion` instances.
        :raises RuntimeError: For unsupported OSes.
        """
        self.logger.info("Finding Unreal Engine executables")
        sw_versions = []

        # Get the executable templates for the current OS
        executable_templates = None
        if sgtk.util.is_macos():
            executable_templates = self.EXECUTABLE_TEMPLATES.get("darwin")
        elif sgtk.util.is_windows():
            executable_templates = self.EXECUTABLE_TEMPLATES.get("win32")
        elif sgtk.util.is_linux():
            executable_templates = self.EXECUTABLE_TEMPLATES.get("linux")

        if not executable_templates:
            raise RuntimeError("Unsupported platform %s" % sys.platform)

        for executable_template in executable_templates:
            self.logger.debug("Processing template %s.", executable_template)
            executable_matches = self._glob_and_match(
                executable_template, self.COMPONENT_REGEX_LOOKUP
            )
            # Extract all products from that executable.
            for (executable_path, key_dict) in executable_matches:
                # extract the matched keys form the key_dict (default to None if
                # not included)
                executable_version = key_dict.get("version")
                details = self._get_unreal_version_details(executable_path)
                if details and all(x in details for x in ["MajorVersion", "MinorVersion", "PatchVersion"]):
                    executable_version = "%s.%s.%s" % (
                        details["MajorVersion"],
                        details["MinorVersion"],
                        details["PatchVersion"],
                    )
                sw_versions.append(
                    SoftwareVersion(
                        executable_version,
                        "Unreal Engine",
                        executable_path,
                        os.path.join(self.disk_location, "icon_256.png"),
                    )
                )
        if sgtk.util.is_windows():
            # On Windows we also explore registry, but make sure to not add
            # things twice.
            found_paths = [sw.path for sw in sw_versions]
            for sw in self._find_software_from_registry():
                if sw.path not in found_paths:
                    sw_versions.append(sw)
                    found_paths.append(sw.path)

        return sw_versions

    def _get_unreal_version_details(self, executable_path):
        """
        Return version details for the given Unreal executable, if any.

        :param str executable_path: Full path to an Unreal Editor executable.
        :returns: A dictionary with version details retrieved from the side car file for the
                  given Unreal Editor executable, or ``None``.
        """
        version_details = None
        path, exe = os.path.split(executable_path)
        version_file = "%s.version" % os.path.splitext(exe)[0]
        full_path = os.path.join(path, version_file)
        if os.path.exists(full_path):
            with open(full_path) as pf:
                version_details = json.load(pf)
        return version_details

    def _get_unreal_version(self, executable_path):
        """
        Return the Unreal Editor version for the given executable.

        :returns: A potentially empty version string.
        """
        details = self._get_unreal_version_details(executable_path)
        if details and all(x in details for x in ["MajorVersion", "MinorVersion", "PatchVersion"]):
            return "%s.%s.%s" % (
                details["MajorVersion"],
                details["MinorVersion"],
                details["PatchVersion"],
            )
        # Fall back on parsing the executable path
        # Look for ue_4.7, ue_4.7.2, etc..
        for part in executable_path.lower().split(os.path.sep):
            m = re.match(r"ue_([0-9]+(?:\.[0-9]+)*)$", part)
            if m:
                return m.group(1)
        return ""

    def _get_win_executable_path(self, install_path):
        """
        Return the Unreal Editor exe path for the given install path, if one
        exists.

        Check if the executable exists on the filesystem.
        :returns: A string, full path to the Unreal editor executable or ``None``.
        """
        binary_path = os.path.normpath(
            os.path.join(install_path, "Engine", "Binaries", "Win64")
        )
        exec_path = os.path.join(binary_path, "UE4Editor.exe")
        if os.path.exists(exec_path):
            self.logger.info("Found %s" % exec_path)
            return exec_path
        # From UE5, the exe name changed
        exec_path = os.path.join(binary_path, "UnrealEditor.exe")
        if os.path.exists(exec_path):
            self.logger.info("Found %s" % exec_path)
            return exec_path

        self.logger.info(
            "Couldn't find executable in installation path %s" % install_path
        )
        return None

    def _find_software_from_registry(self):
        """
        Find executables in the Windows Registry.

        :returns: List of :class:`SoftwareVersion` instances.
        """
        self.logger.info("Detecting Unreal Engine from registry...")
        try:
            # Note: keeping this as is, without knowing why it was implemented
            # like that, instead of just doing import winreg
            import _winreg
        except ImportError:
            import winreg as _winreg

        self.logger.debug(
            "Querying windows registry for key HKEY_LOCAL_MACHINE\\SOFTWARE\\EpicGames\\Unreal Engine"
        )
        base_key_name = "SOFTWARE\\EpicGames\\Unreal Engine"
        # find all subkeys in key HKEY_LOCAL_MACHINE\SOFTWARE\EpicGames\Unreal Engine
        sw_versions = []
        try:
            key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, base_key_name)
            sub_key_count = _winreg.QueryInfoKey(key)[0]
            for i in range(sub_key_count):
                sub_key_name = _winreg.EnumKey(key, i)
                sub_key = _winreg.OpenKey(key, sub_key_name)
                values_count = _winreg.QueryInfoKey(sub_key)[1]
                if sub_key_name == "Builds":
                    for j in range(values_count):
                        value = _winreg.EnumValue(sub_key, j)[1]
                        self.logger.info("Checking %s" % value)
                        if value and os.path.exists(value):
                            executable_path = self._get_win_executable_path(value)
                            if executable_path:
                                sw = SoftwareVersion(
                                    self._get_unreal_version(executable_path),
                                    "Unreal Engine (Dev Build)",
                                    executable_path,
                                    os.path.join(self.disk_location, "icon_256.png")
                                )
                                sw_versions.append(sw)
                else:
                    for j in range(values_count):
                        value_name, value, _ = _winreg.EnumValue(sub_key, j)
                        if value_name == "InstalledDirectory":
                            if value and os.path.exists(value):
                                executable_path = self._get_win_executable_path(value)
                                if executable_path:
                                    sw = SoftwareVersion(
                                        self._get_unreal_version(executable_path),
                                        "Unreal Engine",
                                        executable_path,
                                        os.path.join(self.disk_location, "icon_256.png")
                                    )
                                    sw_versions.append(sw)

                            break
            _winreg.CloseKey(key)
        except WindowsError as e:
            self.logger.error("Error handling key %s: %s" % (base_key_name, e))
            # Log the traceback in debug
            self.logger.debug(
                "Error opening key %s: %s" % (base_key_name, e),
                exc_info=True
            )

        return sw_versions
