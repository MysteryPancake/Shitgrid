import Container from  'react-bootstrap/Container';
import Row from  'react-bootstrap/Row';
import Col from  'react-bootstrap/Col';
import Timer from '../components/Timer';

function Dashboard() {
	return (
		<div className="m-3">
			<h2 className="mb-3">Dashboard</h2>
			<Container fluid>
				<Row>
					<Col>
						<Timer time="30 July, 2023" event="Studio 2 Ends"/>
					</Col>
					<Col>
						<Timer time="December 1, 2023" event="Studio 3 Ends"/>
					</Col>
					<Col>
						<Timer time="Jan 1, 2030" event="2030"/>
					</Col>
					<Col>
						<Timer time="Jan 1, 2040" event="2040"/>
					</Col>
					<Col>
						<Timer time="July 15, 2025 09:10:30.592" event="Dynamo Dream Episode 4"/>
					</Col>
					<Col>
						<Timer time="May 6, 2035 13:03:50.439" event="Grand Theft Auto 6"/>
					</Col>
					<Col>
						<Timer time="May 3, 3062 04:02:34.237" event="World War 3"/>
					</Col>
					<Col>
						<Timer time="Jan 5, 9054 06:30:39.597" event="Heat Death of the Sun"/>
					</Col>
					<Col>
						<Timer time="December 1, 13456 07:04:20.703" event="Return of Christ"/>
					</Col>
					<Col>
						<Timer time="November 2, 25236 02:50:03.405" event="Dad Comes Back with the Milk"/>
					</Col>
					<Col>
						<Timer time="June 23, 35236 08:23:34.123" event="Half-Life 3"/>
					</Col>
				</Row>
			</Container>
		</div>
	);
}

export default Dashboard;