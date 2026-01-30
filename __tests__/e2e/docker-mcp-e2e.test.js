/**
 * E2E test: MCP server via StdioClientTransport
 *
 * Spawns the built MCP server as a child process and communicates
 * via the MCP SDK Client over stdio. Validates tool listing and
 * optional live tool invocation when credentials are present.
 *
 * Runs inside Docker (npm run test:e2e) or locally (npm run test:e2e:local).
 */

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SERVER_PATH = path.resolve(__dirname, '..', '..', 'dist', 'index.js');

const EXPECTED_TOOL_COUNT = 12;
const CONNECTION_TIMEOUT = 30_000;
const TOOL_CALL_TIMEOUT = 60_000;

describe('MCP Server E2E', () => {
  /** @type {Client} */
  let client;
  /** @type {StdioClientTransport} */
  let transport;

  beforeAll(async () => {
    transport = new StdioClientTransport({
      command: 'node',
      args: [SERVER_PATH],
      env: {
        ...process.env,
        // Ensure Python venv is discoverable
        PATH: process.env.PATH,
      },
    });

    client = new Client({
      name: 'e2e-test-client',
      version: '1.0.0',
    });

    await client.connect(transport);
  }, CONNECTION_TIMEOUT);

  afterAll(async () => {
    try {
      await client?.close();
    } catch {
      // Ignore close errors
    }
    try {
      await transport?.close();
    } catch {
      // Ignore close errors
    }
  });

  test('listTools returns expected tools', async () => {
    const result = await client.listTools();

    expect(result.tools).toBeDefined();
    expect(Array.isArray(result.tools)).toBe(true);
    expect(result.tools.length).toBe(EXPECTED_TOOL_COUNT);

    // Verify key tools exist
    const toolNames = result.tools.map(t => t.name);
    expect(toolNames).toContain('search_books');
    expect(toolNames).toContain('download_book_to_file');
    expect(toolNames).toContain('process_document_for_rag');
    expect(toolNames).toContain('get_download_limits');

    // Each tool should have name, description, and inputSchema
    for (const tool of result.tools) {
      expect(tool.name).toBeTruthy();
      expect(tool.description).toBeTruthy();
      expect(tool.inputSchema).toBeDefined();
    }
  }, TOOL_CALL_TIMEOUT);

  test('callTool with invalid tool returns error', async () => {
    const result = await client.callTool({
      name: 'nonexistent_tool',
      arguments: {},
    });

    // Server should return an error response, not crash
    expect(result).toBeDefined();
    expect(result.isError).toBe(true);
  }, TOOL_CALL_TIMEOUT);

  // Live credential test - only runs when ZLIBRARY_EMAIL is set
  const liveTest = process.env.ZLIBRARY_EMAIL ? test : test.skip;

  liveTest('callTool get_download_limits returns structured response', async () => {
    const result = await client.callTool({
      name: 'get_download_limits',
      arguments: {},
    });

    expect(result).toBeDefined();
    expect(result.content).toBeDefined();
    expect(Array.isArray(result.content)).toBe(true);
    expect(result.content.length).toBeGreaterThan(0);
    expect(result.content[0].type).toBe('text');
  }, TOOL_CALL_TIMEOUT);
});
