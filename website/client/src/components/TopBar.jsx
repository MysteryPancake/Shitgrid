import Nav from 'react-bootstrap/Nav';
import Navbar from 'react-bootstrap/Navbar';
import { Link } from 'react-router-dom'

function TopBar() {
	return (
		<Navbar bg="dark" variant="dark">
			<Navbar.Brand className="ms-3">
				<img
					src="/shitgrid.svg"
					className="d-inline-block"
					width="32"
					height="32"
					alt="SH"
				/>
				{' '}
				Shitgrid
			</Navbar.Brand>
			<Nav className="me-auto">
				<Nav.Link as={Link} to="/">Dashboard</Nav.Link>
				<Nav.Link as={Link} to="/assets">Assets</Nav.Link>
				<Nav.Link as={Link} to="/tasks">Tasks</Nav.Link>
				<Nav.Link as={Link} to="/builds">Builds</Nav.Link>
			</Nav>
		</Navbar>
	);
}

export default TopBar;