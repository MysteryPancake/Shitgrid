import React from 'react';
import Table from 'react-bootstrap/Table';
import AddAsset from '../components/AddAsset'

class Assets extends React.Component {
	constructor(props) {
		super(props);
		this.state = {
			assets: []
		};
	}

	componentDidMount() {
		fetch(`${process.env.REACT_APP_SHITGRID_SERVER}:${process.env.REACT_APP_SHITGRID_PORT}/getassets`)
			.then(res => res.json())
			.then(json => this.setState({ assets: json }));
	}

	render() {
		return (
			<div className="m-3">
				<div className="mb-2">
					<h2 className="d-inline-block">Assets</h2>
					<AddAsset className="float-end">+ Add Asset</AddAsset>
				</div>
				<Table bordered>
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
									<td>{asset.assetName}</td>
									<td>{asset.assetType}</td>
									<td>{asset.assetDesc}</td>
									<td>{asset.status}</td>
								</tr>
							})
						}
					</tbody>
				</Table>
			</div>
		);
	}
}

export default Assets;