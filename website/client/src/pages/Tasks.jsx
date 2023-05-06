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
			<>
				<div>
					<h2 className="d-inline-block m-3">Tasks</h2>
					<AddTask className="float-end m-3">+ Add Task</AddTask>
				</div>
				<Table bordered hover>
					<thead>
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
			</>
		);
	}
}

export default Tasks;