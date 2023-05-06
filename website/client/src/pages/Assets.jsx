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
			<>
				<div>
					<h2 className="d-inline-block m-3">Assets</h2>
					<AddAsset className="float-end m-3">+ Add Asset</AddAsset>
				</div>
				<Table bordered hover>
					<thead>
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
									<td>{asset.assetDesc}</td>
									<td>{asset.assetType}</td>
									<td>{asset.status}</td>
								</tr>
							})
						}
					</tbody>
				</Table>
			</>
		);
	}
}

export default Assets;