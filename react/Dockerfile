FROM node:22-bookworm-slim

RUN npm install -g serve

WORKDIR /src
COPY package.json package-lock.json .npmrc ./
RUN npm ci

COPY . .
# A local .env points the storefront at localhost. Railway supplies the public URL.
RUN rm -f .env .env.local

# Create React App inlines REACT_APP_* at build time. The DSN is passed
# base64-encoded because its "@" is dropped when Railway forwards build args.
ARG REACT_APP_DSN_B64
ARG REACT_APP_RELEASE=empower.react@railway
ARG REACT_APP_ENVIRONMENT=demo
ARG REACT_APP_BACKEND_URL_FLASK
ARG REACT_APP_STATSIG_CLIENT_KEY=client-local

RUN set -eu; \
    dsn="$(printf '%s' "$REACT_APP_DSN_B64" | base64 -d)"; \
    case "$dsn" in *sentry.io/*) ;; *) echo "REACT_APP_DSN_B64 did not decode to a Sentry DSN"; exit 1 ;; esac; \
    echo "Baking Sentry project ${dsn##*/}"; \
    REACT_APP_DSN="$dsn" \
    REACT_APP_RELEASE="$REACT_APP_RELEASE" \
    REACT_APP_ENVIRONMENT="$REACT_APP_ENVIRONMENT" \
    REACT_APP_BACKEND_URL_FLASK="$REACT_APP_BACKEND_URL_FLASK" \
    REACT_APP_STATSIG_CLIENT_KEY="$REACT_APP_STATSIG_CLIENT_KEY" \
    INLINE_RUNTIME_CHUNK=false npx react-scripts build && cp serve.json build/

CMD ["sh", "-c", "serve -s build -l tcp://0.0.0.0:${PORT:-3000}"]
