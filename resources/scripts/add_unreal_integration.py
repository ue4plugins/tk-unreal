# This file is provided by Epic Games, Inc. and is subject to the license
# file included in this repository.

import argparse
import logging
import os
import re
import shutil

"""
Add the Unreal integration to a SG TK default2 config.

python add_unreal_integration.py -p <path to your TK config>

The scripts:
- copies an unreal folder in env/includes
- adds `include: ../env/includes/unreal/templates.yml` to the core/templates.yml file.
- adds `- ./includes/unreal/settings/tk-unreal.yml` to the env/project.yml file includes.
- adds `tk-unreal: "@settings.tk-unreal.project"` to the env/project.yml file engines
- adds `- ./includes/unreal/settings/tk-unreal.yml` to the env/asset_step.yml file includes.
- adds `tk-unreal: "@settings.tk-unreal.asset_step"` to the env/asset_step.yml file engines
- adds `- ../unreal/settings/tk-multi-publish2.yml` include to the env/includes/settings/tk-maya.yml
- adds `tk-multi-publish2: "@settings.tk-multi-publish2.maya.asset_step.unreal"` to the env/includes/settings/tk-maya.yml
- adds `include: unreal/frameworks.yml` to the env/includes/frameworks file.
- adds "*Unreal*" to Creative Tools group in env/includes/settings/tk-desktop.yml.
- copies ../config/unreal folder to env/includes
- copies files and folders from ../config/schema to core/schema
"""

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("UEconfig")


def add_include_to_includes(lines, include):
    """
    Add the given include line to the 'includes' block from the given lines.

    :returns: A tuple where the first entry is the last line treated and the second
              a boolean indicating if changed were made.
    :raises ValueError: If no includes block can be found.
    """
    changed = False
    # Look for the "includes:" block
    logger.debug("Looking for an includes block...")
    for lineno, line in enumerate(lines):
        if re.match(r"includes\s*:\n", line):
            break
    else:
        raise ValueError("Couldn't find an includes block")
    # Keep reading the include block contents, check if we can find tk-unreal.yml include
    lineno += 1  # Next line after "includes:"
    logger.debug("Treating includes block from line %d" % lineno)
    for lineno2, line in enumerate(lines[lineno:]):
        if not re.match(r"-\s+", line):
            logger.debug("Detected end of includes block from %s" % line)
            lines.insert(lineno2 + lineno, "%s\n" % include)
            changed = True
            break
        if re.match(include, line):
            logger.debug("Spotted existing Unreal include from '%s'" % line)
            break
    return lineno + lineno2, changed


def add_unreal_include_and_engine(env_file_path, context_name):
    """
    Add if needed the Unreal engine to the given SG TK env file.

    :param str env_file_path: Full path to a SG TK env file.
    :param str context_name: The context name for this env file, e.g. 'project'.
    :raises ValueError: If the Unreal engine can't be added.
    """
    changed = False
    logger.info("Checking %s..." % env_file_path)
    with open(env_file_path, "r") as f:
        lines = f.readlines()
        offset, changed = add_include_to_includes(
            lines,
            "- ./includes/unreal/settings/tk-unreal.yml"
        )
        # Keep reading and look for the "engines:" block
        logger.debug("Looking for an engines block from line %d..." % offset)
        for lineno, line in enumerate(lines[offset:]):
            if re.match(r"engines\s*:\n", line):
                logger.debug("Engines block starts at line %d" % (lineno + offset))
                break
        else:
            raise ValueError("Couldn't find an engines block in %s" % env_file_path)
        # Keep reading the engines block contents, check if we can find tk-unreal definition
        logger.debug("Checking if tk-unreal needs to be added to engines block...")
        lineno = offset + lineno + 1  # Next line after "engiens:"
        padding = "  "  # Two spaces padding
        for lineno2, line in enumerate(lines[lineno:]):
            m = re.match(r"(\s+)\w", line)
            if not m:
                lines.insert(
                    lineno2 + lineno,
                    "%stk-unreal: \"@settings.tk-unreal.%s\"\n" % (padding, context_name)
                )
                changed = True
                break
            # Capture padding
            padding = m.group(1)
            if re.match(r"\s+tk-unreal: \"@settings.tk-unreal.%s\"" % context_name, line):
                logger.debug("Spotted existing Unreal include from '%s'" % line)
                break

    if changed:
        logger.info("Adding Unreal engine to %s." % env_file_path)
        with open(env_file_path, "w") as f:
            f.writelines(lines)


def add_unreal_to_config(path):
    """
    Add Unreal integration an existing default2 based SG TK configuration.

    :param str path: Full path the config folder.
    :raises ValueError: For invalid config path
    """
    logger.info("Adding Unreal integration to %s" % path)
    logger.info("Checking the config structure...")
    if not os.path.isdir(path):
        raise ValueError("%s is not a valid directory" % path)
    env_include_path = os.path.join(path, "env", "includes")
    if not os.path.isdir(env_include_path):
        raise ValueError("%s is not a valid directory" % env_include_path)
    schema_path = os.path.join(path, "core", "schema")
    if not os.path.isdir(schema_path):
        raise ValueError("%s is not a valid directory" % schema_path)

    # Let's be safe for the time being
    unreal_config_folder = os.path.join(path, "env", "includes", "unreal")
    if os.path.exists(unreal_config_folder):
        raise ValueError("Conflict found with %s, please remove or rename it" % unreal_config_folder)

    # Check now all the files we can possibly tweak
    templates_file = os.path.join(path, "core", "templates.yml")
    if not os.path.isfile(templates_file):
        raise ValueError("%s is not a valid file" % templates_file)
    project_file = os.path.join(path, "env", "project.yml")
    if not os.path.isfile(project_file):
        raise ValueError("%s is not a valid file" % project_file)
    asset_step_file = os.path.join(path, "env", "asset_step.yml")
    if not os.path.isfile(asset_step_file):
        raise ValueError("%s is not a valid file" % asset_step_file)
    frameworks_file = os.path.join(path, "env", "includes", "frameworks.yml")
    if not os.path.isfile(frameworks_file):
        raise ValueError("%s is not a valid file" % frameworks_file)
    mayasettings_file = os.path.join(path, "env", "includes", "settings", "tk-maya.yml")
    if not os.path.isfile(mayasettings_file):
        raise ValueError("%s is not a valid file" % mayasettings_file)
    tkdesktop_file = os.path.join(path, "env", "includes", "settings", "tk-desktop.yml")
    if not os.path.isfile(tkdesktop_file):
        raise ValueError("%s is not a valid file" % tkdesktop_file)

    logger.info("Needed files and folders are presents. Processing files...")

    # Tweak core/templates.yml
    changed = False
    logger.info("Checking %s..." % templates_file)
    with open(templates_file, "r") as f:
        lines = f.readlines()
        # Look for an existing include to our unreal templates
        for line in lines:
            if re.match(r"include\s*:\s*../env/includes/unreal/templates.yml", line):
                logger.debug("Spotted existing Unreal include from '%s'" % line)
                break
        else:
            # Not found
            changed = True
            lines.append(
                "include: ../env/includes/unreal/templates.yml\n"
            )
    if changed:
        logger.info("Adding Unreal templates to core templates.")
        with open(templates_file, "w") as f:
            f.writelines(lines)

    # Tweak env/project.yml
    add_unreal_include_and_engine(project_file, "project")
    # Tweak env/asset_step.yml
    add_unreal_include_and_engine(asset_step_file, "asset_step")

    # Tweak env/includes/frameworks.yml
    changed = False
    logger.info("Checking %s..." % frameworks_file)
    with open(frameworks_file, "r") as f:
        lines = f.readlines()
        # Look for an existing include to our unreal frameworks
        for line in lines:
            if re.match(r"include\s*:\s*unreal/frameworks.yml", line):
                logger.debug("Spotted existing Unreal include from '%s'" % line)
                break
        else:
            # Not found
            changed = True
            lines.append(
                "include: unreal/frameworks.yml\n"
            )
    if changed:
        logger.info("Adding Unreal frameworks to frameworks.")
        with open(frameworks_file, "w") as f:
            f.writelines(lines)

    # Tweak env/includes/settings/tk-maya.yml
    changed = False
    logger.info("Checking %s..." % mayasettings_file)
    with open(mayasettings_file, "r") as f:
        lines = f.readlines()
        # Add our include
        offset, changed = add_include_to_includes(
            lines,
            "- ../unreal/settings/tk-multi-publish2.yml"
        )
        # Tweak publish2 asset_step setting
        for lineno, line in enumerate(lines[offset:]):
            m = re.match(
                r"(\s+)tk-multi-publish2:\s+\"@settings.tk-multi-publish2.maya.asset_step(\.unreal)?\"",
                line,
            )
            if m:
                logger.debug("Found publish2 asset_step line %s" % line)
                if not m.group(2):  # missing unreal
                    lines[offset + lineno] = "%s%s" % (
                        m.group(1),
                        "tk-multi-publish2: \"@settings.tk-multi-publish2.maya.asset_step.unreal\"\n",
                    )
                    changed = True
                else:
                    logger.debug("Publish2 asset_step was already set to Unreal integration")
                break
    if changed:
        logger.info("Adding Unreal settings to %s." % mayasettings_file)
        with open(mayasettings_file, "w") as f:
            f.writelines(lines)

    # Tweak env/includes/settings/tk-desktop.yml
    changed = False
    logger.info("Checking %s..." % tkdesktop_file)
    with open(tkdesktop_file, "r") as f:
        lines = f.readlines()
        in_match_group = False
        in_dcc_group = False
        missing = True
        padding = "  "
        # Look for an existing "matches" group with Maya in it, add Unreal to it
        for lineno, line in enumerate(lines):
            if in_match_group:
                m = re.match(r"(\s+)-(.+)", line)
                if m:
                    padding = m.group(1)
                    if "Unreal" in m.group(2):
                        logger.debug("Unreal is already there: %s" % line)
                        missing = False
                    elif "Maya" in m.group(2):
                        logger.debug("Found dcc group from %s" % line)
                        in_dcc_group = True
                elif in_dcc_group and missing:
                    # We insert before the end of the "matches" block
                    lines.insert(
                        lineno,
                        "%s- \"*Unreal*\"\n" % padding
                    )
                    changed = True
                    break
            elif re.match(r"\s+-\s+matches:", line):
                logger.debug("Entering match group with %s" % line)
                in_match_group = True
                in_dcc_group = False
                missing = True

    if changed:
        logger.info("Adding Unreal wildcard to TK Desktop groups.")
        with open(tkdesktop_file, "w") as f:
            f.writelines(lines)

    # Copy ../config/unreal folder to env/includes
    copy_from_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        "..",
        "config",
    )

    logger.info("Copying config/unreal folder to %s" % unreal_config_folder)
    shutil.copytree(
        os.path.join(
            copy_from_path,
            "unreal"
        ),
        unreal_config_folder,
    )
    logger.info("Copying schema placeholders to %s" % schema_path)
    copy_schema_path = os.path.normpath(os.path.join(copy_from_path, "schema"))
    for dirpath, dirnames, filenames in os.walk(copy_schema_path):
        relative = os.path.relpath(dirpath, copy_schema_path)
        target_folder = os.path.join(schema_path, relative)
        logger.debug("Comparing %s to %s, folders %s, files %s" % (dirpath, target_folder, dirnames, filenames))
        for dirname in dirnames:
            target = os.path.join(target_folder, dirname)
            if not os.path.exists(target):
                logger.info("Creating folder %s" % target)
                os.mkdir(target)
            elif not os.path.isdir(target):
                raise ValueError("%s already exists but is not a directory" % target)
            else:
                logger.debug("%s already exists" % target)
        for filename in filenames:
            source = os.path.join(dirpath, filename)
            target = os.path.join(target_folder, filename)
            if not os.path.exists(target):
                logger.info("Copying %s to %s" % (source, target))
                shutil.copy(source, target)
            elif not os.path.isfile(target):
                raise ValueError("%s already exists but is not a file" % target)
            else:
                # Since our files are only placeholders for now, not doing
                # anything is ok.
                logger.debug("%s already exists" % target)
    logger.info("Unreal integration was successfully added")


def main():
    """
    Parse command line arguments and call the add_unreal_to_config method
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v",
        "--verbose",
        help="Verbose output",
        action="store_true"
    )

    parser.add_argument(
        "-p",
        "--path",
        help="Full path to the SG TK configuration directory",
        required=True,
    )
    args = parser.parse_args()
    logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    try:
        add_unreal_to_config(args.path)
    except Exception:
        logging.error(
            "Unable to add Unreal integration to %s" % args.path,
            exc_info=True,
        )


if __name__ == "__main__":
    main()
