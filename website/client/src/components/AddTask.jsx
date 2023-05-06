import React from 'react';
import Button from 'react-bootstrap/Button';
import Modal from 'react-bootstrap/Modal';
import Form from 'react-bootstrap/Form';

class AddTask extends React.Component {
	constructor(props) {
		super(props);
		this.state = {
			show: false,
			taskName: "",
			taskDesc: ""
		};
	}

	showModal = () => {
		this.setState({ show: true });
	}

	hideModal = () => {
		this.setState({ show: false });
	}

	submit = (e) => {
		e.preventDefault();
		fetch(`${process.env.REACT_APP_SHITGRID_SERVER}:${process.env.REACT_APP_SHITGRID_PORT}/addtask`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				taskName: this.state.taskName,
				taskDesc: this.state.taskDesc
			})
		}).then(() => window.location.reload());
	}

	render() {
		return (
			<>
				<Button {...this.props} onClick={this.showModal}>{this.props.children}</Button>
				<Modal show={this.state.show} onHide={this.hideModal} backdrop="static" keyboard={false} centered>
					<Form onSubmit={this.submit}>
						<Modal.Header closeButton>
							<Modal.Title>Add Task</Modal.Title>
						</Modal.Header>
						<Modal.Body>
							<Form.Label htmlFor="taskName">Task Name</Form.Label>
							<Form.Control
								id="taskName"
								name="taskName"
								type="text"
								autoFocus
								value={this.state.taskName}
								onChange={e => this.setState({ taskName: e.target.value })}
								required
							/>
							<Form.Label htmlFor="taskDesc" className="mt-3">Task Description</Form.Label>
							<Form.Control
								id="taskDesc"
								name="taskDesc"
								type="text"
								as="textarea"
								rows={6}
								value={this.state.taskDesc}
								onChange={e => this.setState({ taskDesc: e.target.value })}
								required
							/>
						</Modal.Body>
						<Modal.Footer>
							<Button variant="secondary" onClick={this.hideModal}>Cancel</Button>
							<Button type="submit" variant="primary">Add Task</Button>
						</Modal.Footer>
					</Form>
				</Modal>
			</>
		);
	}
}

export default AddTask;