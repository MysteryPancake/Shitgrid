import React from 'react'
import Card from 'react-bootstrap/Card';

class Timer extends React.Component {
	constructor(props) {
		super(props);
		this.state = {
			timeRef: new Date(props.time).getTime()
		};
	}

	timer() {
		const diffMillis = this.state.timeRef - Date.now();
		const diffSec = diffMillis / 1000;
		const days = Math.floor(diffSec / 86400);
		const hours = Math.floor((diffSec % 86400) / 3600).toString().padStart(2, "0");
		const mins = Math.floor((diffSec % 3600) / 60).toString().padStart(2, "0");
		const secs = Math.floor(diffSec % 60).toString().padStart(2, "0");
		const millis = Math.floor(diffMillis % 1000).toString().padStart(3, "0")
		this.setState({ timeLeft: `${days}:${hours}:${mins}:${secs}.${millis}` });
	}

	componentDidMount() {
		this.interval = setInterval(this.timer.bind(this), 30);
	}

	componentWillUnmount() {
		clearInterval(this.interval);
	}

	render() {
		return (
			<Card bg="light">
				<Card.Body className="text-center mb-3 mt-3">
					<h1 className="mb-3 font-monospace fw-bold">{this.state.timeLeft}</h1>
					<p className="mb-1">Time until</p>
					<p className="fw-bold mb-0 fs-5">{this.props.event}</p>
				</Card.Body>
			</Card>
		);
	}
}

export default Timer;