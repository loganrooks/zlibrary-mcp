# Docker Deployment

Run Z-Library MCP server in a Docker container with HTTP transport via [SuperGateway](https://github.com/supercorp-ai/supergateway).

## Quick Start

```bash
# From project root
cd docker
cp env.example .env
# Edit .env with your Z-Library credentials

# Build and run
docker compose up -d
```

The server will be available at `http://localhost:8000`.

## Manual Build

```bash
# From project root
docker build -t zlibrary-mcp -f docker/Dockerfile .

# Run standalone
docker run -d \
  -p 8000:8000 \
  -e ZLIBRARY_EMAIL=your@email.com \
  -e ZLIBRARY_PASSWORD=your_password \
  -v $(pwd)/downloads:/app/downloads \
  zlibrary-mcp
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ZLIBRARY_EMAIL` | Yes | Z-Library account email |
| `ZLIBRARY_PASSWORD` | Yes | Z-Library account password |
| `ZLIBRARY_MIRROR` | No | Custom Z-Library mirror URL |
| `RETRY_MAX_RETRIES` | No | Max retry attempts (default: 3) |
| `CIRCUIT_BREAKER_THRESHOLD` | No | Failures before circuit opens (default: 5) |

### Volumes

| Container Path | Description |
|----------------|-------------|
| `/app/downloads` | Downloaded books directory |

## Health Check

```bash
curl http://localhost:8000/health
```

## Connecting MCP Clients

The server exposes the MCP protocol over HTTP via SuperGateway. Configure your MCP client to connect to:

```
http://localhost:8000
```

## Architecture

```
[MCP Client] <--HTTP--> [SuperGateway:8000] <--stdio--> [zlibrary-mcp]
```

SuperGateway wraps the stdio-based MCP server to provide HTTP transport, enabling:
- Remote access to the MCP server
- Load balancing and proxying
- Health monitoring

## Offline release-image smoke

Release CI packs once and uses that same tarball for npm publication and the
Docker build. The image is loaded locally, tested, then pushed without rebuilding.
PR CI runs the same packed-image journey. Source builds above remain supported.

To reproduce from a checkout with dependencies already available (Node 22+,
Docker and `openssl` required):

```bash
npm run build
IMAGE_CONTEXT=$(mktemp -d)
npm pack --ignore-scripts --pack-destination "$IMAGE_CONTEXT"
mv "$IMAGE_CONTEXT"/*.tgz "$IMAGE_CONTEXT/release.tgz"
cp package-lock.json "$IMAGE_CONTEXT/"
docker build --build-arg BUILD_INPUT=packed \
  -t zlibrary-mcp:smoke -f docker/Dockerfile "$IMAGE_CONTEXT"
node scripts/image-smoke.mjs zlibrary-mcp:smoke
```

For an existing locally built candidate image, run only
`node scripts/image-smoke.mjs <image>`. Its version must match this checkout's
`package.json`. The runner never pulls an image.

The SDK initializes the container's stdio server, checks the package version and
exact five-tool surface, and searches a fixed synthetic catalogue through the
image's Python bridge. A sidecar, using the same image, hosts the existing
rehearsal HTTPS fake. It has `--network none`; the MCP container shares only that
loopback namespace. Existing Node/Python fences reject unintended networking and
any recorded attempt fails the smoke. Only harness/TLS/state are mounted; server
and bridge files come from the image. All credentials and content are synthetic.
Owned containers and temporary state are removed on success or failure.

The smoke overrides the SuperGateway entrypoint to exercise stdio directly; it
does not test HTTP transport, real providers, or every architecture. Without
Docker, `node --test __tests__/image-smoke.test.mjs` runs the same SDK/bridge/fake
journey against a Docker-command double (requires a built `dist/` and `.venv/`).
That checks the runner's assertions and failure cleanup, not image construction
or actual network namespaces/mounts.
