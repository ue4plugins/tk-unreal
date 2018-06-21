import unreal
import sgtk.platform

unreal.log("Loading Shotgun Engine for Unreal from {}".format(__file__))

@unreal.uclass()
class ShotgunEngineWrapper(unreal.ShotgunEngine):

    def _post_init(self):
        """
        Equivalent to __init__ but will also be called from C++
        """
        engine = sgtk.platform.current_engine()
        engine.unreal_sg_engine = self

        unreal.log("ShotgunEngineWrapper._post_init: unreal_sg_engine {} with tk-unreal {}".format(self, engine))
        
    @unreal.ufunction(override=True)
    def get_shotgun_menu_items(self):
        """
        Returns the list of available menu items to populate the Shotgun menu in Unreal
        """
        menu_items = []
        
        engine = sgtk.platform.current_engine()
        menu_items = self.create_menu(engine)

        unreal.log("get_shotgun_menu_items returned: {0}".format(menu_items.__str__()))

        return menu_items

    @unreal.ufunction(override=True)
    def execute_command(self, command_name):
        """
        Callback to execute the menu item selected in the Shotgun menu in Unreal
        """
        engine = sgtk.platform.current_engine()

        unreal.log("execute_command called for {0}".format(command_name))
        if command_name in engine.commands:
            unreal.log("execute_command: Command {0} found.".format(command_name))
            command = engine.commands[command_name]
            command_callback = command["callback"]
            command_callback = self._get_command_override(engine, command_name, command_callback)
            
            self._execute_callback(command_callback)
            # self._execute_deferred(command["callback"])

    def _get_command_override(self, engine, command_name, default_callback):
        """
        Get overriden callback for the given command or the default callback if it's not overriden
        Implement command overrides here as needed
        :param command_name: The command name to override
        :param default_callback: The callback to use when there's no override
        """
        # Override the Shotgun Panel command to use the Shotgun Entity context
        # and also reuse the dialog if one already exists
        if command_name == "Shotgun Panel...":
            def show_shotgunpanel_with_context():
                app = engine.apps["tk-multi-shotgunpanel"]
                entity_type, entity_id = self._get_context(engine)
                if entity_type:
                    return lambda : app.navigate(entity_type, entity_id, app.DIALOG)
                else:
                    return default_callback
            
            return show_shotgunpanel_with_context()
            
        return default_callback
    
    def _get_context_url(self, engine):
        """
        Get the Shotgun entity URL from the metadata of the selected asset, if present
        """
        # By default, use the URL of the project
        url = engine.context.shotgun_url

        # In case of multi-selection, use the first object in the list
        selected_asset = self.selected_assets[0] if self.selected_assets else None
        selected_actor = self.selected_actors[0] if self.selected_actors else None
        
        loaded_asset = None
        if selected_asset:
            # Asset must be loaded to read the metadata from item
            # Note that right-clicking on an asset in the Unreal Content Browser already loads item
            # But a load could be triggered if the context is from a selected actor
            loaded_asset = unreal.EditorAssetLibrary.load_asset(selected_asset.object_path)
        elif selected_actor:
            # Get the asset that is associated with the selected actor
            assets = self.get_referenced_assets(selected_actor)
            loaded_asset = assets[0] if assets else None

        if loaded_asset:
            # Try to get the URL metadata from the asset
            tag = engine.get_metadata_tag("url")
            metadata_value = unreal.EditorAssetLibrary.get_metadata_tag(loaded_asset, tag)
            if metadata_value:
                url = metadata_value
                
        return url

    def _get_context(self, engine):
        """
        Get the Shotgun context (entity type and id) that is associated with the selected menu command
        """
        entity_type = None
        entity_id = None

        # The context is derived from the Shotgun entity URL
        url = self._get_context_url(engine)
        if url:
            # Extract entity type and id from URL, which should follow this pattern:
            # url = shotgun_site + "/detail/" + entity_type + "/" + entity_id
            tokens = url.split("/")
            if len(tokens) > 3:
                if tokens[-3] == "detail":
                    entity_type = tokens[-2]
                    try:
                        # Entity id must be converted to an integer
                        entity_id = int(tokens[-1])
                    except:
                        # Otherwise, the context cannot be derived from the URL
                        entity_type = None
                    
        return entity_type, entity_id
        
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

        engine = sgtk.platform.current_engine()
        if engine is not None:
            unreal.log("Shutting down ShotgunEngineWrapper")
            
            # destroy_engine of tk-unreal will take care of closing all dialogs that are still opened
            engine.destroy()
            QtWidgets.QApplication.instance().quit()
            QtWidgets.QApplication.processEvents()
        
    """
    Menu generation functionality for Unreal (based on the 3ds max Menu Generation implementation)
    
    Actual menu creation is done in Unreal
    The following functions simply generate a list of available commands that will populate the Shotgun menu in Unreal
    """

    def create_menu(self, engine):
        """
        Populate the Shotgun Menu with the available commands
        """
        menu_items = []

        # add contextual commands here so that they get enumerated in the next step
        self._start_contextual_menu(engine, menu_items)

        # enumerate all items and create menu objects for them
        cmd_items = []
        for (cmd_name, cmd_details) in engine.commands.items():
            cmd_items.append(AppCommand(cmd_name, cmd_details))

        # add the other contextual commands in this section
        for cmd in cmd_items:
            if cmd.get_type() == "context_menu":
                self._add_menu_item_from_command(menu_items, cmd)
                
        # end the contextual menu
        self._add_menu_item(menu_items, "context_end")

        # now favourites
        for fav in engine.get_setting("menu_favourites", []):
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
        
    def _start_contextual_menu(self, engine, menu_items):
        """
        Starts a menu section for the current context
        """
        ctx = engine.context
        ctx_name = str(ctx)

        self._add_menu_item(menu_items, "context_begin", ctx_name, ctx_name)
        
        engine.register_command("Jump to Shotgun", self._jump_to_sg, {"type": "context_menu", "short_name": "jump_to_sg"})

        # Add the menu item only when there are some file system locations.
        if ctx.filesystem_locations:
            engine.register_command("Jump to File System", self._jump_to_fs, {"type": "context_menu", "short_name": "jump_to_fs"})

    def _jump_to_sg(self):
        """
        Callback to Jump to Shotgun from context
        """
        from sgtk.platform.qt5 import QtGui, QtCore
        url = self._get_context_url(sgtk.platform.current_engine())
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    def _jump_to_fs(self):
        """
        Callback to Jump to Filesystem from context
        """
        engine = sgtk.platform.current_engine()

        # launch one window for each location on disk
        paths = engine.context.filesystem_locations
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
                engine.log_error("Failed to launch '%s'!" % cmd)

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
