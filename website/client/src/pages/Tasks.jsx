import React from 'react';
import Alert from 'react-bootstrap/Alert';
import Table from 'react-bootstrap/Table';
import Spinner from 'react-bootstrap/Spinner';

import AddTask from '../components/AddTask';

class Tasks extends React.Component {
	constructor(props) {
		super(props);
		this.state = {};
	}

	validate = (e) => {
		if (e.ok) {
			e.json().then((json) => this.setState({ tasks: json }));
		} else {
			this.setState({ error: e.message });
		}
	}

	componentDidMount() {
		fetch(`${process.env.REACT_APP_SG_SERVER}:${process.env.REACT_APP_SG_PORT}/tasks/get`)
			.then(this.validate).catch(this.validate);
	}

	render() {
		return (
			<div className="m-3">
				<div className="mb-2">
					<h2 className="d-inline-block">Tasks</h2>
					<AddTask className="float-end">+ Add Task</AddTask>
				</div>
				{
					this.state.tasks
					? <Table bordered>
						<thead style={{ backgroundColor: "#EEE" }}>
							<tr>
								<th>Task Name</th>
								<th>Description</th>
								<th>Assets</th>
							</tr>
						</thead>
						<tbody>
							{
								this.state.tasks.map((task, i) => {
									return <tr key={i}>
										<td>{task.name}</td>
										<td>{task.description}</td>
										<td>{task.assets}</td>
									</tr>
								})
							}
						</tbody>
					</Table>
					: (
						this.state.error
						? <Alert variant="danger">{this.state.error}</Alert>
						: <Spinner animation="border" />
					)
				}
			</div>
		);
	}
}

export default Tasks;