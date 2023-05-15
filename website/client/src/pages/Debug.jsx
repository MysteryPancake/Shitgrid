function Debug() {
	return (
		<div className="m-3">
			<h1>Welcome to Hell</h1>
			<p className="mt-3">Website backend is set to {' '}
				<a href={`${process.env.REACT_APP_SG_SERVER}:${process.env.REACT_APP_SG_PORT}`}>
					{process.env.REACT_APP_SG_SERVER}:{process.env.REACT_APP_SG_PORT}
				</a>
			</p>
		</div>
	);
}

export default Debug;