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
Docker build. Both npm and GHCR wait for the image smoke: prepare/test/pack,
build/load, bind the image digest, smoke, npm publish, then GHCR push. A failed
smoke leaves both registries untouched. GHCR still waits for npm publication.
PR CI runs the same packed-image journey. Source builds above remain supported.

To reproduce from a checkout with dependencies already available (Node 22+,
Docker and `openssl` required):

```bash
npm run build
IMAGE_CONTEXT=$(mktemp -d)
bash scripts/prepare-image-context.sh "$IMAGE_CONTEXT"
docker build --build-arg BUILD_INPUT=packed \
  -t zlibrary-mcp:smoke -f docker/Dockerfile "$IMAGE_CONTEXT"
node scripts/image-smoke.mjs zlibrary-mcp:smoke
```

CI, publishing and these instructions use the same context helper. It requires
an empty destination and creates only `release.tgz` and `package-lock.json`.
Supply an existing tarball as a second argument to reuse it without packing:
`bash scripts/prepare-image-context.sh "$IMAGE_CONTEXT" /path/to/candidate.tgz`.

Publication enables Docker's containerd image store before the BuildKit build
and explicitly requests `provenance: mode=min`. The classic image store cannot
retain an attestation index. `image-identity.mjs` requires the loaded index digest
to equal BuildKit's output before the smoke; `push-tested-image.mjs` checks every
metadata tag against that digest before pushing the same local image without
rebuilding or selecting a platform. It then checks each registry digest and the
retained attestation manifest. See [Docker's image-store requirements for
attestations](https://docs.docker.com/build/metadata/attestations/#driver-and-image-store-support).
The tag patterns, npm channel and `latest` behavior are unchanged. A registry
error can still leave a partial release after the smoke passes; there is no
transaction across npm and GHCR.

For an existing locally built candidate image, run only
`node scripts/image-smoke.mjs <image>`. Its version must match this checkout's
`package.json`. The runner never pulls an image.

The SDK initializes the container's stdio server, checks the package version and
exact five-tool surface, compares full input/output schemas against the committed
`__tests__/rehearsal/tools-schemas.json` fixture, and searches a fixed synthetic
catalogue through the image's Python bridge. A sidecar, using the same image, hosts the existing
rehearsal HTTPS fake. It has `--network none`; the MCP container shares only that
loopback namespace. Existing Node/Python fences reject unintended networking and
any recorded attempt fails the smoke. Only harness/TLS/state are mounted; server
and bridge files come from the image. All credentials and content are synthetic.
Owned containers and temporary state are removed on success or failure.

Before the search, a canary runs inside the MCP container with its environment
and image interpreter. It must receive the Python fence's rejection and record
exactly one blocked attempt; a kernel denial alone fails. Only that expected
marker is cleared before the journey, so `egress=0` describes the journey after
the successful positive control.

The smoke overrides the SuperGateway entrypoint to exercise stdio directly; it
does not test HTTP transport, real providers, or every architecture. Without
Docker, `node --test __tests__/image-smoke.test.mjs __tests__/image-smoke-contract.test.mjs` runs the same SDK/bridge/fake
journey against a Docker-command double (requires a built `dist/` and `.venv/`).
That checks the runner's assertions and failure cleanup, not image construction
or actual network namespaces/mounts.

For socket-free helper/schema/publication controls alone, run
`node --test __tests__/image-smoke-contract.test.mjs`. The YAML gate is covered by
`node --experimental-vm-modules node_modules/jest/bin/jest.js __tests__/publish-workflow.test.js --runInBand --coverage=false`.
