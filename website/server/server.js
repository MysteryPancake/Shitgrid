const fs = require('fs');
const path = require('path');
const express = require('express');
const cors = require('cors');
const app = express();
const port = process.env.REACT_APP_SHITGRID_PORT || 5000;

// Use JSON requests for now
app.use(express.json());

// Allow frontend and backend to communicate on the same device
app.use(cors());

const router = express.Router();

// Main folder for website database files, using JSON for the moment
const WEB_DB = process.env.SHITGRID_WEB_DB;

// Contains subfolders for each department, "modelling", "surfacing", etc
const BLEND_DB = process.env.SHITGRID_BLEND_DB;

const TASK_DB = "tasks.json";
const ASSET_DB = "assets.json";

console.log(`Website database set to ${WEB_DB}`);
console.log(`Blender database set to ${BLEND_DB}`);

router.get('/', (req, res) => {
	res.send('Backend is working!');
});

router.post('/addtask', (req, res) => {
	const taskName = req.body.taskName.trim();
	const taskDesc = req.body.taskDesc.trim();

	if (!taskName || !taskDesc) {
		res.sendStatus(400); // Bad request
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
		taskName: taskName,
		taskDesc: taskDesc
	});
	// Write "tasks.json" again
	fs.writeFileSync(jsonFile, JSON.stringify(jsonData));

	res.sendStatus(200); // Success
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
		res.sendStatus(400); // Bad request
		return;
	}

	// Create subfolder in Blender folder if required
	const wipFolder = path.join(BLEND_DB, assetName);
	if (!fs.existsSync(wipFolder)) {
		fs.mkdirSync(wipFolder);
	}

	// Who needs a real database
	const jsonFile = path.join(WEB_DB, ASSET_DB);
	// Read existing "assets.json" if possible
	let jsonData = [];
	if (fs.existsSync(jsonFile)) {
		const content = fs.readFileSync(jsonFile);
		jsonData = JSON.parse(content);
	}
	// Add new asset to array
	jsonData.push({
		assetName: assetName,
		assetType: assetType,
		assetDesc: assetDesc
	});
	// Write "assets.json" again
	fs.writeFileSync(jsonFile, JSON.stringify(jsonData));

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

app.listen(port, () => console.log(`Listening on port ${port}`));