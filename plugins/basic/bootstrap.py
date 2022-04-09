# This file is based on templates provided and copyrighted by Autodesk, Inc.
# This file has been modified by Epic Games, Inc. and is subject to the license 
# file included in this repository.

import sys
import os

# Setup sys.path so that we can import our bootstrapper.
plugin_root_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(plugin_root_dir, "python"))

# Add sgtk path to sys.path
import pathlib
sgtk_core_path = pathlib.Path(plugin_root_dir.split("app_store")[0])
sgtk_core_path = sgtk_core_path / "core" / "python"
sys.path.insert(0, str(sgtk_core_path))

from tk_unreal_basic import plugin_bootstrap
plugin_bootstrap.bootstrap_plugin(plugin_root_dir)
