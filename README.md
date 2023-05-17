# Shitgrid

Definitely not Kitsu...

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

- Set `SG_BLEND_DB` to the folder you want Blender files to be saved, for example `C:/blender_db`

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
