// Driver-facing stdio MCP adapter. It exposes exactly the measured server tools.
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { ListToolsRequestSchema, CallToolRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { connect } from 'node:net';
import { createInterface } from 'node:readline';
const socketPath = process.argv[2];
function request(value) {
  return new Promise((resolve, reject) => {
    const socket = connect(socketPath),
      lines = createInterface({ input: socket });
    socket.once('error', reject);
    socket.once('connect', () => socket.write(JSON.stringify(value) + '\n'));
    lines.once('line', (line) => {
      const r = JSON.parse(line);
      if (r.error) reject(new Error(r.error));
      else resolve(r.result);
      socket.end();
    });
  });
}
const server = new Server(
  { name: 'book-acquisition-eval', version: '1.0.0' },
  { capabilities: { tools: {} } },
);
server.setRequestHandler(ListToolsRequestSchema, () => request({ method: 'list' }));
server.setRequestHandler(CallToolRequestSchema, (req) =>
  request({ method: 'call', name: req.params.name, args: req.params.arguments ?? {} }),
);
await server.connect(new StdioServerTransport());
