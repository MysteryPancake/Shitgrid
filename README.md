# Shitgrid

Like Kitsu but worse!

## Components

### Website

The website is designed to imitate Shotgrid, with basic abilities to create and view tasks and assets.
It uses a React frontend and an Express backend, both which have to be run separately.
When an asset is added via the frontend, the backend creates a folder on disk.
These folders are used by the Blender addon as described below.

### Blender Addon

The Blender addon is responsible for managing asset versions.
Assets get published into the folders created by the website.

## Environment Variables:

### Website

- Set `SHITGRID_WEB_DB` to a folder where you want the backend database to be stored, for example `C:/web_db`.
- Set `REACT_APP_SHITGRID_SERVER` to the URL of the web server backend, for example `http://localhost`.
- Set `REACT_APP_SHITGRID_PORT` to the web server backend port, for example `5000`.

### Blender Addon

- Set `SHITGRID_BLEND_DB` to a folder where you want Blender files to be stored, for example `C:/blender_db`.

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

1. Open Blender Preferences
2. Install the file `blender_addon/__init__.py`
3. Press `N` to open the menu
