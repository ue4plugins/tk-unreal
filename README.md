## Documentation

This is the scaffold necessary to write a Toolkit engine.

`startup.py`: This is where you will implement the Unreal install folder detection logic.

`engine.py`: This is the heart of the integration between Toolkit and Unreal. It is responsible for adding menu entries, implementing panel support, routing messages to the console, etc.

`plugins`: This is the Toolkit plugin folder. A Toolkit plugin is a piece of code that can be run inside a DCC to initialize Toolkit and launch the engine.

If desired, a Toolkit plugin can be built into a self-contained package that
doesnt't require Internet access to download code and could be part of the installation folder of Unreal.

The other way to invoke this plugin is to leverage the something akin to MAYA_PATH, where Maya walks the paths specified in that variable and load any file named `userSetup.py`.

So, assuming Unreal has something like UNREAL_PATH that picks up files named unreal_plugin.py, the `startup.py` logic would update UNREAL_PATH to point to
a folder inside the repo that contains `unreal_plugin.py` and that file would invoke the bootstrap.py file and let it do its thing.

`hooks`: This is the folder with all the requisite scaffold to run our hooks and implement custom Unreal logic.