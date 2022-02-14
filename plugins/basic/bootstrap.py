# This file is based on templates provided and copyrighted by Autodesk, Inc.
# This file has been modified by Epic Games, Inc. and is subject to the license
# file included in this repository.

import sys
import os
import unreal

# Setup sys.path so that we can import our bootstrapper.
plugin_root_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(plugin_root_dir, "python"))

# Temp workaround for UE5 dev: for some reasons the core/python path is missing
# in sys.path but is present in the PYTHONPATH.
# Make sure sys.path is up to date with what is in the PYTHON PATH
python_path = os.environ.get("PYTHONPATH") or ""
for path in python_path.split(os.pathsep):
    # We can have empty entries for consecutives separators
    if path and path not in sys.path:
        unreal.log_warning(
            "Adding missing %s Python path to sys paths" % path,
        )
        sys.path.append(path)

from tk_unreal_basic import plugin_bootstrap
plugin_bootstrap.bootstrap_plugin(plugin_root_dir)
