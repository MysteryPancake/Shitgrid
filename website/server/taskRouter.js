const fs = require('fs');
const path = require('path');
const express = require('express');
const router = express.Router();
const TASK_DB = 'tasks.json';

router.post('/add', (req, res) => {

	let taskName = req.body.taskName;
	if (!taskName) {
		res.status(400).send("Missing task name!");
		return;
	}
	taskName = taskName.trim();

	// Task description is not essential
	const taskDesc = (req.body.taskDesc || "").trim();

	// Read existing content if possible
	const jsonFile = path.join(req.app.locals.WEB_DB, TASK_DB);
	let jsonData = [];
	if (fs.existsSync(jsonFile)) {
		jsonData = JSON.parse(fs.readFileSync(jsonFile));
	}
	// Add new task to array
	jsonData.push({
		name: taskName,
		description: taskDesc,
		assets: []
	});
	fs.writeFileSync(jsonFile, JSON.stringify(jsonData));

	res.sendStatus(200);
});

router.get('/get', (req, res) => {
	const jsonFile = path.join(req.app.locals.WEB_DB, TASK_DB);
	// Send nothing if we have no tasks yet
	if (!fs.existsSync(jsonFile)) {
		res.send([]);
		return;
	}
	// Top quality security right here
	res.sendFile(jsonFile);
});

module.exports = router;