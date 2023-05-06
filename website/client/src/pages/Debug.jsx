import Container from  'react-bootstrap/Container';

function Debug() {
	return (
		<Container>
			<h1 className="mt-5">What's up?</h1>
			<p className="mt-4">Website backend is set to {' '}
				<a href={`${process.env.REACT_APP_SHITGRID_SERVER}:${process.env.REACT_APP_SHITGRID_PORT}`}>
					{process.env.REACT_APP_SHITGRID_SERVER}:{process.env.REACT_APP_SHITGRID_PORT}
				</a>
			</p>
		</Container>
	);
}

export default Debug;