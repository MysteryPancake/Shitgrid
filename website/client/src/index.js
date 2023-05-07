import React from 'react';
import ReactDOM from 'react-dom/client';
import reportWebVitals from './reportWebVitals';
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import 'bootstrap/dist/css/bootstrap.min.css';

import TopBar from './components/TopBar';

import Dashboard from './pages/Dashboard';
import Assets from './pages/Assets';
import Tasks from './pages/Tasks';
import Debug from './pages/Debug';
import Builds from './pages/Builds';
import NotFound from './pages/NotFound';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
	<React.StrictMode>
		<BrowserRouter>
			<TopBar />
			<Routes>
				<Route path="/" element={<Dashboard/>} />
				<Route path="/assets" element={<Assets/>} />
				<Route path="/tasks" element={<Tasks/>} />
				<Route path="/debug" element={<Debug/>} />
				<Route path="/builds" element={<Builds/>} />
				<Route path='*' element={<NotFound />}/>
			</Routes>
		</BrowserRouter>
	</React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();