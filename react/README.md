## About

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

## Deploy

See [../README.md](../README.md)

## Local chat

The plant chat requires the separate `agent` service, not just the Flask backend.
From the repository root, use `./deploy --env=local react flask agent` to start
all three with matching local URLs. See [../README.md](../README.md) for initial
environment setup; the agent also requires Docker.

If chat reports "Unable to reach the plant agent", check that the agent is
running at `REACT_APP_BACKEND_URL_AGENT` (normally `http://localhost:8093` locally).
Start the missing service and retry the message. The browser cannot distinguish
a stopped service from other connectivity or CORS failures; the original fetch
error is retained as the cause in Sentry for diagnosis.
