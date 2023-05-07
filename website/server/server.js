const fs = require('fs');
const path = require('path');
const express = require('express');
const cors = require('cors');
const app = express();

const PORT = process.env.REACT_APP_SHITGRID_PORT;
if (!PORT) {
	console.error("Missing environment variable REACT_APP_SHITGRID_PORT!");
	return;
}

// Main folder for website database files, using JSON for the moment
const WEB_DB = process.env.SHITGRID_WEB_DB;
if (WEB_DB) {
	console.log(`Website database set to ${WEB_DB}`);
} else {
	console.error("Missing environment variable SHITGRID_WEB_DB!");
	return;
}

// Contains subfolders for each department, "modelling", "surfacing", etc
const BLEND_DB = process.env.SHITGRID_BLEND_DB;
if (BLEND_DB) {
	console.log(`Blender database set to ${BLEND_DB}`);
} else {
	console.error("Missing environment variable SHITGRID_BLEND_DB!");
	return;
}

// Allow frontend and backend to communicate on the same device
app.use(cors());
app.use(express.json());

const TASK_DB = "tasks.json";
const ASSET_DB = "assets.json";

const router = express.Router();

router.get('/', (req, res) => {
	res.send('Backend is working!');
});

router.post('/addtask', (req, res) => {
	const taskName = req.body.taskName.trim();
	const taskDesc = req.body.taskDesc.trim();

	if (!taskName || !taskDesc) {
		res.sendStatus(400);
		return;
	}

	// Who needs a real database
	const jsonFile = path.join(WEB_DB, TASK_DB);
	// Read existing "tasks.json" if possible
	let jsonData = [];
	if (fs.existsSync(jsonFile)) {
		const content = fs.readFileSync(jsonFile);
		jsonData = JSON.parse(content);
	}
	// Add new task to array
	jsonData.push({
		name: taskName,
		description: taskDesc,
		assets: []
	});
	// Write "tasks.json" again
	fs.writeFileSync(jsonFile, JSON.stringify(jsonData));

	res.sendStatus(200);
});

router.get('/gettasks', (req, res) => {
	const jsonFile = path.join(WEB_DB, TASK_DB);
	// Send nothing if we have no tasks yet
	if (!fs.existsSync(jsonFile)) {
		res.send([]);
		return;
	}
	// Top quality security right here
	res.sendFile(jsonFile);
});

router.post('/addasset', (req, res) => {
	const assetName = req.body.assetName.trim();
	const assetType = req.body.assetType.trim();
	const assetDesc = req.body.assetDesc.trim();

	if (!assetName || !assetDesc) {
		res.sendStatus(400);
		return;
	}

	// Who needs a real database
	const jsonFile = path.join(WEB_DB, ASSET_DB);
	// Read existing "assets.json" if possible
	let jsonData = [];
	if (fs.existsSync(jsonFile)) {
		const content = fs.readFileSync(jsonFile);
		jsonData = JSON.parse(content);
	}
	// Don't override existing data
	if (jsonData.find(e => e.name == assetName)) {
		res.status(400);
		return;
	}
	// Add new asset to object
	jsonData.push({
		name: assetName,
		type: assetType,
		description: assetDesc,
		thumbnail: "",
		status: "TODO"
	});
	// Write "assets.json" again
	fs.writeFileSync(jsonFile, JSON.stringify(jsonData));

	// Create subfolder in Blender folder if required
	const wipFolder = path.join(BLEND_DB, assetName);
	if (!fs.existsSync(wipFolder)) {
		fs.mkdirSync(wipFolder);
	}

	res.sendStatus(200);
});

router.get('/getassets', (req, res) => {
	const jsonFile = path.join(WEB_DB, ASSET_DB);
	// Send nothing if we have no assets yet
	if (!fs.existsSync(jsonFile)) {
		res.send([]);
		return;
	}
	// Top quality security right here
	res.sendFile(jsonFile);
});

app.use(router);

app.listen(PORT, () => console.log(`Listening on port ${PORT}`));