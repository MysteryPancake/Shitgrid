import React from 'react';
import Alert from 'react-bootstrap/Alert';
import Button from 'react-bootstrap/Button';
import Modal from 'react-bootstrap/Modal';
import Form from 'react-bootstrap/Form';

class AddAsset extends React.Component {
	constructor(props) {
		super(props);
		this.state = {
			show: false,
			assetName: "",
			assetType: "setpiece",
			assetDesc: ""
		};
	}

	showModal = () => {
		this.setState({ show: true });
	}

	hideModal = () => {
		this.setState({ show: false });
	}

	validate = async(e) => {
		if (e.ok) {
			window.location.reload();
		} else {
			const msg = e.message || await e.text();
			this.setState({ error: msg });
		}
	}

	submit = (e) => {
		e.preventDefault();
		fetch(`${process.env.REACT_APP_SHITGRID_SERVER}:${process.env.REACT_APP_SHITGRID_PORT}/assets/add`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				assetName: this.state.assetName,
				assetType: this.state.assetType,
				assetDesc: this.state.assetDesc
			})
		}).then(this.validate).catch(this.validate);
	}

	render() {
		return (
			<>
				<Button {...this.props} onClick={this.showModal}>{this.props.children}</Button>
				<Modal show={this.state.show} onHide={this.hideModal} backdrop="static" keyboard={false} centered>
					<Form onSubmit={this.submit}>
						<Modal.Header closeButton>
							<Modal.Title>Add Asset</Modal.Title>
						</Modal.Header>
						<Modal.Body>
							<Form.Label htmlFor="assetName">Asset Name</Form.Label>
							<Form.Control
								id="assetName"
								name="assetName"
								type="text"
								autoFocus
								maxLength={255}
								value={this.state.assetName}
								onChange={e => this.setState({ assetName: e.target.value })}
								required
							/>
							<Form.Label htmlFor="assetType" className="mt-3">Asset Type</Form.Label>
							<Form.Select
								id="assetType"
								value={this.state.assetType}
								onChange={e => this.setState({ assetType: e.target.value })}
							>
								<option value="setpiece" default>Set Piece</option>
								<option value="character">Character</option>
								<option value="prop">Prop</option>
								<option value="fx">FX</option>
								<option value="set">Set</option>
								<option value="camera">Camera</option>
							</Form.Select>
							<Form.Label htmlFor="assetDesc" className="mt-3">Asset Description</Form.Label>
							<Form.Control
								id="assetDesc"
								name="assetDesc"
								type="text"
								as="textarea"
								rows={6}
								value={this.state.assetDesc}
								onChange={e => this.setState({ assetDesc: e.target.value })}
							/>
						</Modal.Body>
						<Modal.Footer>
							<Alert variant="danger" show={!!this.state.error}>{this.state.error}</Alert>
							<Button variant="secondary" onClick={this.hideModal}>Cancel</Button>
							<Button type="submit" variant="primary">Add Asset</Button>
						</Modal.Footer>
					</Form>
				</Modal>
			</>
		);
	}
}

export default AddAsset;