const express = require('express');
const cors = require('cors');
const app = express();

const taskRouter = require('./taskRouter.js');
const assetRouter = require('./assetRouter.js');

const PORT = process.env.REACT_APP_SG_PORT;
if (!PORT) {
	console.error("Missing environment variable REACT_APP_SG_PORT!");
	return;
}

// Main folder for website database files, using JSON for the moment
app.locals.WEB_DB = process.env.SG_WEB_DB;
if (app.locals.WEB_DB) {
	console.log(`Website database set to ${app.locals.WEB_DB}`);
} else {
	console.error("Missing environment variable SG_WEB_DB!");
	return;
}

// Hardcoded for now
app.locals.BLEND_DB = "C:\\Users\\MysteryPancake\\Desktop\\Blender_Pipeline\\db_blend";
console.log(`Blender database set to ${app.locals.BLEND_DB}`);

// Allow frontend and backend to communicate on the same device
app.use(cors());
app.use(express.json());

app.use('/tasks', taskRouter);
app.use('/assets', assetRouter);

app.get('/', (req, res) => {
	res.send('Backend is working!');
});

app.listen(PORT, () => console.log(`Listening on port ${PORT}`));