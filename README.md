# Shitgrid

This pipeline was an experiment to see how much of a pipeline I could get done in 2 weeks.

I wanted this pipeline to be fully original, so I tried to avoid ideas from existing pipelines.

Eventually I realised I was reinventing the wheel after looking at Kitsu's codebase, which uses the same idea of transferring data between objects.

## Features

### Publishing

When publishing an asset, it works like a namespace. All data blocks relevant to the chosen publish layer get tagged with custom data.

Custom data is used to create an imaginary link, associating data blocks to an asset name, ID, layer and version.

Conceptually this means any data can be published, even if it can't be represented as an object (such as text, brushes, palettes, etc)

Any data blocks which are already tagged won't get retagged. This is because a single Blender can contain multiple assets (for example when scene building), and publishing should only affect the relevant asset name.

If a data block is already tagged and belongs to the publish name and layer, its version in the custom data will be incremented.

### Updating

When updating, it searches through all data blocks and checks the version in their custom data. Any outdated data blocks will be rebuilt according to their layer.

### Fetching

Fetching is meant to append a prebuilt asset created by `build.bat`.

For the public release it checks whether build exist, and otherwise manually builds all layers for an asset.

### Building

Building is a developer feature intended to manually build specific layers with specific versions. It turned out to be the most useful feature in practice.

## Components

### Website

The website is designed to imitate Shotgrid, with basic abilities to create and view tasks and assets.

When an asset is added via the frontend, the backend creates a folder on disk within the `wip` folder.

The folders are used by the Blender addon as described below.

### Blender Addon

The Blender addon is responsible for publishing, version control and building.

Once a `wip` asset folder is added via the website, the addon can publish Blender files into that folder.

The build scripts take `wip` files and consolidate them into single assets, located in the `build` folder.

## Architecture

### Website Backend

The backend is written in JavaScript using Express.

It doesn't use a database for now, just basic file storage in `assets.json` and `tasks.json`.

<img src="images/web_backend_uml.png">

### Website Frontend

The frontend is written in JavaScript and JSX using React.

### Blender Addon

The Blender addon is written in Python.

## Environment Variables

### Website

- Set `SG_WEB_DB` to the folder you want the JSON files to be stored, for example `C:/web_db`
- Set `REACT_APP_SG_SERVER` to whatever URL the backend is hosted on, for example `http://localhost`
- Set `REACT_APP_SG_PORT` to whatever port the backend is hosted on, for example `5000`

### Blender Addon

- The Blender database must be set in the addon preferences.
- Set it to the folder you want Blender files to be saved, for example `C:/blender_db`

## Installation

### Website Frontend

1. Install NPM and Node.js
2. Go to `website/client`
3. Run `npm install`
4. Run `npm start`

### Website Backend

1. Install NPM and Node.js
2. Go to `website/server`
3. Run `npm install`
4. Run `npm start`

### Blender Addon

1. Zip the contents of the `blender` folder
2. Open Blender preferences
3. Install the zipped folder as an addon
4. Press `N` to open the menu
