# This file is based on templates provided and copyrighted by Autodesk, Inc.
# This file has been modified by Epic Games, Inc. and is subject to the license
# file included in this repository.

"""
An Unreal Editor engine for Tank.
"""

# Note that the VFX Plaform states that in 2019 all DCCs need to support Python 3,
# since Python 2.7 will be EOL in 2020. So it's a good idea to start writing your
# engine with a Python 3 compatible syntax. Note that at the moment Toolkit
# is not Python 3 compatible.
from __future__ import print_function

import pprint
from sgtk.platform import Engine
import sgtk.platform

import unreal
import os
import sys

###############################################################################################
# The Shotgun Unreal engine


class UnrealEditorEngine(Engine):
    """
    Toolkit engine for Unreal.
    """

    metadata_tag_prefix = "SG."

    def __init__(self, *args, **kwargs):
        """
        Engine Constructor
        """
        self._qt_app = None

        Engine.__init__(self, *args, **kwargs)

    @property
    def context_change_allowed(self):
        """
        Whether the engine allows a context change without the need for a restart.
        """
        return True

    @property
    def host_info(self):
        """
        :returns: A dictionary with information about the application hosting this engine.

        The returned dictionary is of the following form on success:

            {
                "name": "Unreal Engine",
                "version": "4.9",
            }

        The returned dictionary is of following form on an error preventing
        the version identification.

            {
                "name": "Unreal Engine",
                "version: "unknown"
            }
        """
        host_info = {"name": "Unreal Engine", "version": "unknown"}
        return host_info

    ##########################################################################################
    # init and destroy

    def pre_app_init(self):
        """
        Runs after the engine is set up but before any apps have been initialized.
        """
        # unicode characters returned by the shotgun api need to be converted
        # to display correctly in all of the app windows

        # This is often necessary to get Qt to play nice with Python and utf-8.
        # from tank.platform.qt import QtCore
        # # tell QT to interpret C strings as utf-8
        # utf8 = QtCore.QTextCodec.codecForName("utf-8")
        # QtCore.QTextCodec.setCodecForCStrings(utf8)
        # self.logger.debug("set utf-8 codec for widget text")

        self.init_qt_app()

        # Load the tk_unreal module (the SG engine wrapper for Unreal)
        self.tk_unreal = self.import_module("tk_unreal")
        self.unreal_sg_engine = self.tk_unreal.config.wrapper_instance

        unreal.log("UnrealEditorEngine.pre_app_init: unreal_sg_engine {}".format(self.unreal_sg_engine))

    def init_engine(self):
        """
        Initializes the engine.
        """
        self.logger.debug("%s: Initializing UnrealEditorEngine from %s...", self, __file__)

        # If your launcher allows to launch any version of Unreal, this is where you would usually
        # show a Qt dialog warning that this version of the tk-unreal engine might not be compatible
        # with the current version of the Unreal engine.

    def init_qt_app(self):
        self.logger.debug("%s: Initializing QtApp for Unreal", self)
        from sgtk.platform.qt5 import QtWidgets

        if not QtWidgets.QApplication.instance():
            self._qt_app = QtWidgets.QApplication(sys.argv)
            self._qt_app.setQuitOnLastWindowClosed(False)
        else:
            self._qt_app = QtWidgets.QApplication.instance()

        # On other platforms than Windows, we need to process the Qt events otherwise
        # UIs are "frozen". We use a slate tick callback to do that on a regular basis.
        # It is not clear why this is not needed on Windows, possibly because a
        # dedicated Windows event dispatcher is used instead of a regular
        # QAbstractEventDispatcher
        if sys.platform != "win32":
            unreal.register_slate_post_tick_callback(self._process_qt_events_cb)
        # Make the QApplication use the dark theme. Must be called after the QApplication is instantiated
        self._initialize_dark_look_and_feel()

    @staticmethod
    def _process_qt_events_cb(delta_time):
        """
        An Unreal tick callback to process QT events.

        :param float delta_time: delta time since the last run.
        """
        from sgtk.platform.qt5 import QtWidgets
        qapp = QtWidgets.QApplication.instance()
        if qapp:
            qapp.processEvents()

    def post_app_init(self):
        """
        Called when all apps have initialized
        """

        # This is usually where the Shotgun menu is created based on the actions available
        # as well as any dockable views in the UI. If your app can't dock a widget in the
        # UI, it is perfectly reasonable to not implement show_panel method. The base class will
        # forward the call to show_dialog.

        # Not all commands are part of an app. For example, the Restart Engine and
        # Toggle Debug commands.
        #
        # The first entry of the Shotgun menu should be a sub-menu named after
        # the current context (calling str on self.context will generate a human readable string),
        # and should contain all commands that don't have an app or whose properties
        # key have the type set to context_menu.
        #
        # Then each app should have it's folder with all it's commands inserted inside it, unless
        # there is a single command for that app. In that case it is good practice to put the menu
        # entry at the root level of the menu.
        #
        # Note that maps in Python are unsorted, so if you want to display the menu entries in a
        # predictable manner, like alphabetically, you'll have to sort it yourself.
        #
        # Ideally this shouldn't be the responsability of the engine, but sadly it is. We're looking
        # into refactoring that logic in the future.

        self.logger.info("Here are the available Toolkit commands:")

        for (cmd_name, cmd_details) in self.commands.items():
            # Prints out the name of the Toolkit commands that can be invoked
            # and the method to invoke to launch them. The callback
            # do not take any parameters.
            # This prints the application's name, the command name and the callback method.

            print("-" * len(cmd_name))
            print("Command name: " + cmd_name)
            print("Command properties:")
            pprint.pprint(cmd_details["properties"])

        # Many engines implement the notion of favorites, which allow the menu
        # to bubble certain actions up to the main Shotgun menu. This shows
        # up in the environment file as.
        #
        # menu_favourites:
        # - {app_instance: tk-multi-workfiles2, name: File Open...}
        # - {app_instance: tk-multi-workfiles2, name: File Save...}
        #
        # Here's a reference implementation:
        #
        for fav in self.get_setting("menu_favourites"):
            app_instance_name = fav["app_instance"]
            menu_name = fav["name"]

            if menu_name not in self.commands:
                self.logger.warning("Unknown command: %s/%s", app_instance_name, menu_name)
                continue

            command = self.commands[menu_name]

            if command["properties"]["app"].instance_name != app_instance_name:
                # The same action can be registered for different app instance
                # so skip it.
                continue

            print("Favorite found: ", menu_name)

    def post_context_change(self, old_context, new_context):
        """
        Runs after a context change.

        :param old_context: The context being changed away from.
        :param new_context: The new context being changed to.
        """
        # When the context changes, you'll want to recreate the Shotgun menu
        # as the actions might have changed.

    def destroy_engine(self):
        """
        Stops watching scene events and tears down menu.
        """
        self.logger.debug("%s: Destroying tk-unreal engine...", self)

        # Close all Shotgun app dialogs that are still opened since
        # some apps do threads cleanup in their onClose event handler
        # Note that this function is called when the engine is restarted (through "Reload Engine and Apps")

        # Important: Copy the list of dialogs still opened since the call to close() will modify created_qt_dialogs
        dialogs_still_opened = self.created_qt_dialogs[:]

        for dialog in dialogs_still_opened:
            dialog.close()

    def get_metadata_tag(self, tag):
        """
        Returns the given tag with the metadata tag prefix defined for this engine
        """
        return UnrealEditorEngine.metadata_tag_prefix + tag

    def _get_dialog_parent(self):
        """
        Get the QWidget parent for all dialogs created through
        show_dialog & show_modal.
        """
        # I'm leaving the piece of logic for Maya here. If the Unreal editor
        # doesn't derive from a QMainWindow, this can simply return None, which
        # means Qt dialog won't be parent-able on top of the editor/engine. This
        # is a Qt limitation.
        #

        # from tank.platform.qt import QtGui
        # import maya.OpenMayaUI as OpenMayaUI
        # try:
        #     import shiboken2 as shiboken
        # except ImportError:
        #     import shiboken
        # ptr = OpenMayaUI.MQtUtil.mainWindow()
        # parent = shiboken.wrapInstance(long(ptr), QtGui.QMainWindow)

        # return parent

        return None

    def _create_dialog(self, title, bundle, widget, parent):
        """
        Function override to set the window icon
        """
        dialog = sgtk.platform.Engine._create_dialog(self, title, bundle, widget, parent)

        from sgtk.platform.qt import QtGui

        unreal_icon = os.path.realpath(
            os.path.join(
                os.path.dirname(__file__),
                "icon_256.png"
            )
        )
        dialog.setWindowIcon(QtGui.QIcon(unreal_icon))
        return dialog

    def _define_qt_base(self):
        """
        This will be called at initialisation time and will allow
        a user to control various aspects of how QT is being used
        by Tank. The method should return a dictionary with a number
        of specific keys, outlined below.

        * qt_core - the QtCore module to use
        * qt_gui - the QtGui module to use
        * wrapper - the Qt wrapper root module, e.g. PySide
        * dialog_base - base class for to use for Tank's dialog factory

        :returns: dict
        """
        # This method generally is not overriden by an engine. However,
        # if your Qt environment has special quirks that need to be taken
        # into account when creating dialogs, the dialog_base key should
        # be set to a custom class that encapsulates those quirks so that
        # Toolkit applications behave as expected. This can take the form for
        # example of code that ensures that dialogs show initially on top
        # in environments where the main app dialog isn't Qt-based.
        return super(UnrealEditorEngine, self)._define_qt_base()

    @property
    def has_ui(self):
        """
        Detect and return if Unreal is running in batch mode
        """
        # Unless the Unreal Editor can run in batch-mode (no-ui), this should
        # return True.
        return True

    ##########################################################################################
    # logging

    def _emit_log_message(self, handler, record):
        """
        Called by the engine to log messages in Unreal script editor.
        All log messages from the toolkit logging namespace will be passed to this method.

        :param handler: Log handler that this message was dispatched from.
                        Its default format is "[levelname basename] message".
        :type handler: :class:`~python.logging.LogHandler`
        :param record: Standard python logging record.
        :type record: :class:`~python.logging.LogRecord`
        """
        msg = handler.format(record)

        # Assuming the Unreal Editor has a message dialog, you would call
        # here a method that allows to send text to that console. Note that
        # this method can be called from any thread that uses Toolkit logging.
        unreal.log("{0}".format(msg))

    ##########################################################################################
    # panel support

    def show_panel(self, panel_id, title, bundle, widget_class, *args, **kwargs):
        """
        Docks an app widget in a panel.

        :param panel_id: Unique identifier for the panel, as obtained by register_panel().
        :param title: The title of the panel
        :param bundle: The app, engine or framework object that is associated with this window
        :param widget_class: The class of the UI to be constructed. This must derive from QWidget.

        Additional parameters specified will be passed through to the widget_class constructor.

        :returns: the created widget_class instance
        """
        # This is the default implementation from the base class. If you can't dock Qt widgets
        # inside the editor, then simply take out this method and panels will show up as floating
        # dialogs.
        self.log_warning("Panel functionality not implemented. Falling back to showing "
                         "panel '%s' in a modeless dialog" % panel_id)
        return self.show_dialog(title, bundle, widget_class, *args, **kwargs)
