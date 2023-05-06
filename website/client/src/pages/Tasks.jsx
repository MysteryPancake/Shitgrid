import React from 'react';
import Table from 'react-bootstrap/Table';
import AddTask from '../components/AddTask'

class Tasks extends React.Component {
	constructor(props) {
		super(props);
		this.state = {
			tasks: []
		};
	}

	componentDidMount() {
		fetch(`${process.env.REACT_APP_SHITGRID_SERVER}:${process.env.REACT_APP_SHITGRID_PORT}/gettasks`)
			.then(res => res.json())
			.then(json => this.setState({ tasks: json }));
	}

	render() {
		return (
			<div className="m-3">
				<div className="mb-2">
					<h2 className="d-inline-block">Tasks</h2>
					<AddTask className="float-end">+ Add Task</AddTask>
				</div>
				<Table bordered>
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
									<td>{task.taskName}</td>
									<td>{task.taskDesc}</td>
									<td>{task.taskAssets}</td>
								</tr>
							})
						}
					</tbody>
				</Table>
			</div>
		);
	}
}

export default Tasks;