## Documentation

This repository is a part of the ShotGrid Pipeline Toolkit/Unreal integration and contains the source code for SG TK Unreal engine.

The simplest way to add the ShotGrid Toolkit integration to Unreal is to start from the available standard Shotgrid Toolkit configurations:
- Default2 SG TK configuration: https://github.com/ue4plugins/tk-config-unreal
- Basic SG TK configuration: https://github.com/ue4plugins/tk-config-unrealbasic

However, it is possible to manually add the integration to an existing SG TK configuration from the files provided by the [default2 based Unreal config](https://github.com/ue4plugins/tk-config-unreal) or the [basic based Unreal config](https://github.com/ue4plugins/tk-config-unrealbasic).

### Configuring the file system schema for a default2 base configuration
If your SG TK configuration needs a file system schema, copy the following files and directories from `core/schema` of [this config](https://github.com/ue4plugins/tk-config-unreal) under the `core/schema` folder of your existing configuration.
```
schema/
└── project
    ├── assets
    │   └── asset_type
    │       └── asset
    │           └── step
    │               ├── publish
    │               │   └── fbx
    │               │       └── placeholder
    │               └── work
    │                   └── fbx
    │                       └── placeholder
    └── sequences
        └── sequence
            └── editorial
                └── placeholder
```

### Adding the SG TK Unreal components
Both configs have a self contained `env/includes` folder which contains all definitions needed by the integration
```
unreal/
├── frameworks.yml
├── settings
│   ├── tk-multi-loader2.yml
│   ├── tk-multi-publish2.yml
│   ├── tk-multi-shotgunpanel.yml
│   └── tk-unreal.yml
├── templates.yml
└── tk-unreal-location.yml
```

This folder should be copied to the `env/includes` folder of your existing configuration.

Then the following files (or similar) need to be modified to add the Unreal integration:

- *core/templates.yml*:
  - add `include: ../env/includes/unreal/templates.yml`
- *env/project.yml*: 
  - add `- ./includes/unreal/settings/tk-unreal.yml` to *includes*
  - add `tk-unreal: "@settings.tk-unreal.project"` to *engines*
- *env/asset_step.yml*: 
  - add `- ./includes/unreal/settings/tk-unreal.yml` to *includes*
  - add `tk-unreal: "@settings.tk-unreal.asset_step"` to *engines*
- *env/includes/settings/tk-maya.yml* or *env/includes/maya/asset_step.yml*:
  - add `- ../unreal/settings/tk-multi-publish2.yml` to *includes*
  - replace *tk-multi-publish2* asset step setting with: `tk-multi-publish2: "@settings.tk-multi-publish2.maya.asset_step.unreal"`
- *env/includes/frameworks* or *env/includes/common/frameworks.yml*:
  - add `include: unreal/frameworks.yml` 
- *env/includes/settings/tk-desktop.yml* or *env/includes/desktop/project.yml*: 
  - add "*Unreal*" to Creative Tools group.



## See also:
For more information on how to run the ShotGrid/Unreal integration, please see the [support documentation](https://docs.unrealengine.com/4.27/en-US/ProductionPipelines/UsingUnrealEnginewithAutodeskShotGrid).

