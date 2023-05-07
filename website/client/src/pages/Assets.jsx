import React from 'react';
import Alert from 'react-bootstrap/Alert';
import Table from 'react-bootstrap/Table';
import Spinner from 'react-bootstrap/Spinner';

import AddAsset from '../components/AddAsset';

class Assets extends React.Component {
	constructor(props) {
		super(props);
		this.state = {};
	}

	validate = (e) => {
		if (e.ok) {
			e.json().then((json) => this.setState({ assets: json }));
		} else {
			this.setState({ error: e.message });
		}
	}

	componentDidMount() {
		fetch(`${process.env.REACT_APP_SHITGRID_SERVER}:${process.env.REACT_APP_SHITGRID_PORT}/assets/get`)
			.then(this.validate).catch(this.validate);
	}

	render() {
		return (
			<div className="m-3">
				<div className="mb-2">
					<h2 className="d-inline-block">Assets</h2>
					<AddAsset className="float-end">+ Add Asset</AddAsset>
				</div>
				{
					this.state.assets
					? <Table bordered>
						<thead style={{ backgroundColor: "#EEE" }}>
							<tr>
								<th>Thumbnail</th>
								<th>Asset Name</th>
								<th>Type</th>
								<th>Description</th>
								<th>Status</th>
							</tr>
						</thead>
						<tbody>
							{
								this.state.assets.map((asset, i) => {
									return <tr key={i}>
										<td>{asset.thumbnail}</td>
										<td>{asset.name}</td>
										<td>{asset.type}</td>
										<td>{asset.description}</td>
										<td>{asset.status}</td>
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

export default Assets;