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
