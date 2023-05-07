const fs = require('fs');
const path = require('path');
const express = require('express');
const router = express.Router();
const ASSET_DB = 'assets.json';

router.post('/add', (req, res) => {

	let assetName = req.body.assetName;
	if (!assetName) {
		res.status(400).send("Missing asset name!");
		return;
	}

	// Prevent folder name issues
	assetName = assetName.trim();
	if (/[^\w\- ]/g.test(assetName)) {
		res.status(400).send("Asset name contains characters not allowed in filenames!");
		return;
	} else if (assetName.length > 255) {
		res.status(400).send("Asset name is too long! Keep it under 256 characters.");
		return;
	}

	let assetType = req.body.assetType;
	if (!assetType) {
		res.status(400).send("Missing asset type!");
		return;
	}
	assetType = assetType.trim();

	// Asset description is not essential
	const assetDesc = (req.body.assetDesc || "").trim();

	// Read existing content if possible
	const jsonFile = path.join(req.app.locals.WEB_DB, ASSET_DB);
	let jsonData = [];
	if (fs.existsSync(jsonFile)) {
		jsonData = JSON.parse(fs.readFileSync(jsonFile));
	}
	// Don't override existing data
	if (jsonData.find(e => e.name == assetName)) {
		res.status(400).send("Asset name already exists!");
		return;
	}
	// Add new asset to array
	jsonData.push({
		name: assetName,
		type: assetType,
		description: assetDesc,
		thumbnail: "",
		status: "TODO"
	});
	fs.writeFileSync(jsonFile, JSON.stringify(jsonData));

	// Create master/wip/asset subfolder if required
	const wipFolder = path.join(req.app.locals.BLEND_DB, "wip", assetName);
	if (!fs.existsSync(wipFolder)) {
		fs.mkdirSync(wipFolder, { recursive: true });
	}

	res.sendStatus(200);
});

router.get('/get', (req, res) => {
	const jsonFile = path.join(req.app.locals.WEB_DB, ASSET_DB);
	// Send nothing if we have no assets yet
	if (!fs.existsSync(jsonFile)) {
		res.send([]);
		return;
	}
	// Top quality security right here
	res.sendFile(jsonFile);
});

module.exports = router;