import unreal
import sgtk.platform

unreal.log("Loading Shotgun Engine for Unreal")

@unreal.uclass()
class ShotgunEngineWrapper(unreal.ShotgunEngine):

    @unreal.ufunction(override=True)
    def get_shotgun_menu_items(self):
        """
        Returns the list of available menu items to populate the Shotgun menu in Unreal
        """
        menu_items = []
        
        self._engine = sgtk.platform.current_engine()

        if self._engine is not None:
            menu_items = self.create_menu()

        unreal.log("get_shotgun_menu_items returned: {0}".format(menu_items.__str__()))

        return menu_items

    @unreal.ufunction(override=True)
    def execute_command(self, command_name):
        """
        Callback to execute the menu item selected in the Shotgun menu in Unreal
        """
        self._engine = sgtk.platform.current_engine()

        if self._engine is not None:
            unreal.log("execute_command called for {0}".format(command_name))
            if command_name in self._engine.commands:
                unreal.log("execute_command: Command {0} found.".format(command_name))
                command = self._engine.commands[command_name]
                self._execute_callback(command["callback"])
                # self._execute_deferred(command["callback"])

    def _execute_callback(self, callback):
        """
        Execute the callback right away
        """
        unreal.log("_execute_callback called with {0}".format(callback.__str__()))
        self._callback = callback
        self._execute_within_exception_trap()

    def _execute_deferred(self, callback):
        """
        Execute the callback deferred
        The primary purpose of this method is to detach the executing code from the menu invocation
        """
        unreal.log("{0} _execute_deferred called with {1}".format(self, callback.__str__()))
        self._callback = callback
        
        from sgtk.platform.qt5 import QtCore
        QtCore.QTimer.singleShot(0, self._execute_within_exception_trap)

    def _execute_within_exception_trap(self):
        """
        Execute the callback and log any exception that gets raised which may otherwise have been
        swallowed by the deferred execution of the callback.
        """
        if self._callback is not None:
            try:
                unreal.log("_execute_within_exception_trap: trying callback {0}".format(self._callback.__str__()))
                self._callback()
            except Exception, e:
                current_engine = sgtk.platform.current_engine()
                current_engine.logger.exception("An exception was raised from Toolkit")
            self._callback = None
                
    @unreal.ufunction(override=True)
    def shutdown(self):
        from sgtk.platform.qt5 import QtWidgets

        _engine = sgtk.platform.current_engine()
        if _engine is not None:
            unreal.log("Shutting down ShotgunEngineWrapper")
            _engine.destroy()
            QtWidgets.QApplication.instance().quit()
            QtWidgets.QApplication.processEvents()
        
    """
    Menu generation functionality for Unreal (based on the 3ds max Menu Generation implementation)
    
    Actual menu creation is done in Unreal
    The following functions simply generate a list of available commands that will populate the Shotgun menu in Unreal
    """

    def create_menu(self):
        """
        Populate the Shotgun Menu with the available commands
        """
        menu_items = []

        # add contextual commands here so that they get enumerated in the next step
        self._start_contextual_menu(menu_items)

        # enumerate all items and create menu objects for them
        cmd_items = []
        for (cmd_name, cmd_details) in self._engine.commands.items():
            cmd_items.append(AppCommand(cmd_name, cmd_details))

        # add the other contextual commands in this section
        for cmd in cmd_items:
            if cmd.get_type() == "context_menu":
                self._add_menu_item_from_command(menu_items, cmd)
                
        # end the contextual menu
        self._add_menu_item(menu_items, "context_end")

        # now favourites
        for fav in self._engine.get_setting("menu_favourites", []):
            app_instance_name = fav["app_instance"]
            menu_name = fav["name"]
            # scan through all menu items
            for cmd in cmd_items:
                if cmd.get_app_instance_name() == app_instance_name and cmd.name == menu_name:
                    # found our match!
                    self._add_menu_item_from_command(menu_items, cmd)
                    # mark as a favourite item
                    cmd.favourite = True

        self._add_menu_item(menu_items, "separator")
        
        # now go through all of the other menu items.
        # separate them out into various sections
        commands_by_app = {}

        for cmd in cmd_items:
            if cmd.get_type() != "context_menu":
                # normal menu
                app_name = cmd.get_app_name()
                if app_name is None:
                    # un-parented app
                    app_name = "Other Items"
                if not app_name in commands_by_app:
                    commands_by_app[app_name] = []
                commands_by_app[app_name].append(cmd)

        # now add all apps to main menu
        self._add_app_menu(commands_by_app, menu_items)

        return menu_items

    def _add_menu_item_from_command(self, menu_items, command):
        """
        Adds the given command to the list of menu items using the command's properties
        """
        self._add_menu_item(menu_items, 
                            command.properties.get("type", "default"),
                            command.properties.get("short_name", command.name),
                            command.name,
                            command.properties.get("description", ""))

    def _add_menu_item(self, menu_items, type, name = "", title = "", description = ""):
        """
        Adds a new Unreal ShotgunMenuItem to the menu items
        """
        menu_item = unreal.ShotgunMenuItem()
        menu_item.title = title
        menu_item.name = name
        menu_item.type = type
        menu_item.description = description
        menu_items.append(menu_item)
        
    def _start_contextual_menu(self, menu_items):
        """
        Starts a menu section for the current context
        """
        ctx = self._engine.context
        ctx_name = str(ctx)

        self._add_menu_item(menu_items, "context_begin", ctx_name, ctx_name)
        
        self._engine.register_command("Jump to Shotgun", self._jump_to_sg, {"type": "context_menu", "short_name": "jump_to_sg"})

        # Add the menu item only when there are some file system locations.
        if ctx.filesystem_locations:
            self._engine.register_command("Jump to File System", self._jump_to_fs, {"type": "context_menu", "short_name": "jump_to_fs"})

    def _jump_to_sg(self):
        """
        Callback to Jump to Shotgun from context
        """
        from sgtk.platform.qt5 import QtGui, QtCore
        url = self._engine.context.shotgun_url
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    def _jump_to_fs(self):
        """
        Callback to Jump to Filesystem from context
        """
        # launch one window for each location on disk
        paths = self._engine.context.filesystem_locations
        for disk_location in paths:
            # get the setting
            system = sys.platform

            # run the app
            if system == "linux2":
                cmd = 'xdg-open "%s"' % disk_location
            elif system == "darwin":
                cmd = 'open "%s"' % disk_location
            elif system == "win32":
                cmd = 'cmd.exe /C start "Folder" "%s"' % disk_location
            else:
                raise Exception("Platform '%s' is not supported." % system)

            exit_code = os.system(cmd)
            if exit_code != 0:
                self._engine.log_error("Failed to launch '%s'!" % cmd)

    def _add_app_menu(self, commands_by_app, menu_items):
        """
        Add all apps to the main menu section, process them one by one.
        :param commands_by_app: Dictionary of app name and commands related to the app, which
                                will be added to the menu_items
        """
        for app_name in sorted(commands_by_app.keys()):
            if len(commands_by_app[app_name]) > 1:
                # more than one menu entry fort his app
                # make a menu section and put all items in that menu section
                self._add_menu_item(menu_items, "context_begin", app_name, app_name)

                for cmd in commands_by_app[app_name]:
                    self._add_menu_item_from_command(menu_items, cmd)

                self._add_menu_item(menu_items, "context_end", app_name, app_name)
            else:
                # this app only has a single entry.
                # display that on the menu
                cmd_obj = commands_by_app[app_name][0]
                if not cmd_obj.favourite:
                    # skip favourites since they are alreay on the menu
                    self._add_menu_item_from_command(menu_items, cmd_obj)

class AppCommand(object):
    """
    Wraps around a single command that you get from engine.commands
    """
    def __init__(self, name, command_dict):
        """
        Initialize AppCommand object.
        :param name: Command name
        :param command_dict: Dictionary containing a 'callback' property to use as callback.
        """
        self.name = name
        self.properties = command_dict["properties"]
        self.callback = command_dict["callback"]
        self.favourite = False

    def get_app_name(self):
        """
        Returns the name of the app that this command belongs to
        """
        if "app" in self.properties:
            return self.properties["app"].display_name
        return None

    def get_app_instance_name(self):
        """
        Returns the name of the app instance, as defined in the environment.
        Returns None if not found.
        """
        engine = self.get_engine()
        if engine is None:
            return None

        if "app" not in self.properties:
            return None

        app_instance = self.properties["app"]

        for (app_instance_name, app_instance_obj) in engine.apps.items():
            if app_instance_obj == app_instance:
                # found our app!
                return app_instance_name

        return None

    def get_engine(self):
        """
        Returns the engine from the App Instance
        Returns None if not found
        """
        if "app" not in self.properties:
            return None

        app_instance = self.properties["app"]
        engine = app_instance.engine

        return engine

    def get_type(self):
        """
        returns the command type. Returns node, custom_pane or default.
        """
        return self.properties.get("type", "default")
