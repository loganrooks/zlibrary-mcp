# Project-Level MCP Server Configuration

## Essential MCP Servers for Z-Library MCP Development

### 1. 🎭 Playwright MCP (CRITICAL)
**Purpose**: Browser automation for testing Z-Library web scraping

**Installation**:
```bash
npm install @modelcontextprotocol/server-playwright
```

**Configuration** (`.mcp/config.json`):
```json
{
  "playwright": {
    "command": "npx",
    "args": ["@modelcontextprotocol/server-playwright"],
    "env": {
      "HEADLESS": "false",
      "TIMEOUT": "30000"
    }
  }
}
```

**Use Cases**:
- Test Z-Library login flows
- Validate DOM scraping logic
- Capture screenshots of failures
- Test CAPTCHA scenarios
- Validate domain rotation
- E2E testing of download workflows

**Example Workflow**:
```typescript
// Testing Z-Library login with Playwright MCP
const playwright = await mcp.connect('playwright');

await playwright.navigate('https://singlelogin.me');
await playwright.fill('#email', process.env.ZLIBRARY_EMAIL);
await playwright.fill('#password', process.env.ZLIBRARY_PASSWORD);
await playwright.click('#login-button');

// Validate successful login
const profileElement = await playwright.waitForSelector('.user-profile');
const screenshot = await playwright.screenshot({ path: 'login-success.png' });
```

### 2. 🧠 Sequential MCP
**Purpose**: Complex reasoning and analysis for debugging

**Use Cases**:
- Analyze error patterns across logs
- Design retry strategies
- Optimize domain rotation algorithms
- Debug complex async flows
- Architecture decision making

**Integration Example**:
```typescript
// Use Sequential for complex debugging
const sequential = await mcp.connect('sequential');

const analysis = await sequential.analyze({
  problem: "Downloads failing intermittently",
  context: {
    logs: recentErrors,
    patterns: failurePatterns,
    domains: testedDomains
  },
  question: "What's the optimal retry strategy?"
});
```

### 3. 📁 Filesystem MCP
**Purpose**: Advanced file operations for downloads and RAG

**Configuration**:
```json
{
  "filesystem": {
    "command": "npx",
    "args": ["@modelcontextprotocol/server-filesystem"],
    "env": {
      "ROOT_DIR": "./",
      "ALLOWED_PATHS": "./downloads,./processed_rag_output,./cache"
    }
  }
}
```

**Use Cases**:
- Monitor download directory
- Auto-process new files
- Clean up old downloads
- Organize processed documents
- Generate file manifests

### 4. 🗄️ SQLite MCP
**Purpose**: Local database for metadata and caching

**Schema Design**:
```sql
-- books table
CREATE TABLE books (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  author TEXT,
  year INTEGER,
  language TEXT,
  extension TEXT,
  size INTEGER,
  hash TEXT UNIQUE,
  book_details JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- searches table
CREATE TABLE searches (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  query TEXT NOT NULL,
  params JSON,
  results JSON,
  result_count INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- downloads table
CREATE TABLE downloads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  book_id TEXT NOT NULL,
  file_path TEXT,
  status TEXT CHECK(status IN ('pending','downloading','completed','failed')),
  error_message TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  completed_at TIMESTAMP,
  FOREIGN KEY (book_id) REFERENCES books(id)
);

-- domains table
CREATE TABLE domains (
  domain TEXT PRIMARY KEY,
  last_success TIMESTAMP,
  failure_count INTEGER DEFAULT 0,
  response_time_ms INTEGER,
  is_active BOOLEAN DEFAULT 1
);
```

**Use Cases**:
- Cache search results
- Track download history
- Store book metadata
- Monitor domain health
- Generate statistics

### 5. 📊 Prometheus MCP (Monitoring)
**Purpose**: Metrics collection and monitoring

**Metrics to Track**:
```typescript
// Custom metrics for Z-Library MCP
const metrics = {
  // Counters
  'zlibrary_searches_total': new Counter({
    name: 'zlibrary_searches_total',
    help: 'Total number of searches performed',
    labelNames: ['status', 'language']
  }),

  'zlibrary_downloads_total': new Counter({
    name: 'zlibrary_downloads_total',
    help: 'Total number of downloads',
    labelNames: ['status', 'format', 'size_category']
  }),

  // Gauges
  'zlibrary_active_domains': new Gauge({
    name: 'zlibrary_active_domains',
    help: 'Number of active domains'
  }),

  'zlibrary_queue_depth': new Gauge({
    name: 'zlibrary_queue_depth',
    help: 'Current download queue depth'
  }),

  // Histograms
  'zlibrary_search_duration_seconds': new Histogram({
    name: 'zlibrary_search_duration_seconds',
    help: 'Search request duration',
    buckets: [0.1, 0.5, 1, 2, 5, 10]
  }),

  'zlibrary_download_duration_seconds': new Histogram({
    name: 'zlibrary_download_duration_seconds',
    help: 'Download duration',
    buckets: [1, 5, 10, 30, 60, 120, 300]
  })
};
```

### 6. 🔄 GitHub MCP
**Purpose**: Project management and CI/CD integration

**Use Cases**:
- Create issues for failed downloads
- Track domain changes
- Automate release notes
- Monitor upstream zlibrary changes
- Link errors to issues

**Automation Example**:
```typescript
// Auto-create issue for persistent failures
const github = await mcp.connect('github');

if (failureCount > 5) {
  await github.createIssue({
    title: `Domain ${domain} failing repeatedly`,
    body: `
      ## Issue
      Domain ${domain} has failed ${failureCount} times

      ## Last Error
      \`\`\`
      ${lastError.stack}
      \`\`\`

      ## Attempted Mitigations
      - Retry with backoff: ${retryAttempts} attempts
      - Domain rotation: Tried ${testedDomains.join(', ')}
    `,
    labels: ['bug', 'infrastructure', 'auto-generated']
  });
}
```

## Development Environment Setup

### Complete MCP Configuration

Create `.mcp/config.json`:
```json
{
  "servers": {
    "playwright": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-playwright"],
      "env": {
        "HEADLESS": "false",
        "TIMEOUT": "30000",
        "SCREENSHOT_DIR": "./screenshots"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem"],
      "env": {
        "ROOT_DIR": "./",
        "WATCH_PATHS": "./downloads,./processed_rag_output"
      }
    },
    "sqlite": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-sqlite"],
      "env": {
        "DATABASE_PATH": "./zlibrary.db"
      }
    },
    "github": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}",
        "REPO": "loganrooks/zlibrary-mcp"
      }
    },
    "sequential": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-sequential"],
      "env": {
        "MAX_THINKING_TIME": "30000"
      }
    }
  },
  "defaultTimeout": 60000,
  "retryAttempts": 3
}
```

### Installation Script

```bash
#!/bin/bash
# install_mcp_servers.sh

echo "Installing MCP servers for Z-Library development..."

# Core MCP servers
npm install -D \
  @modelcontextprotocol/server-playwright \
  @modelcontextprotocol/server-filesystem \
  @modelcontextprotocol/server-sqlite \
  @modelcontextprotocol/server-github

# Additional development tools
npm install -D \
  @modelcontextprotocol/server-prometheus \
  @modelcontextprotocol/server-logs

echo "Creating MCP configuration..."
mkdir -p .mcp
cat > .mcp/config.json << 'EOF'
{
  // Configuration content from above
}
EOF

echo "✅ MCP servers installed successfully"
```

## MCP Server Integration Patterns

### Pattern 1: Playwright for E2E Testing
```typescript
class ZLibraryE2ETester {
  private playwright: PlaywrightMCP;

  async testSearchWorkflow(query: string) {
    // Navigate to Z-Library
    await this.playwright.navigate('https://singlelogin.me');

    // Perform search
    await this.playwright.fill('#searchField', query);
    await this.playwright.press('#searchField', 'Enter');

    // Wait for results
    await this.playwright.waitForSelector('.book-item');

    // Capture results
    const results = await this.playwright.evaluate(() => {
      return Array.from(document.querySelectorAll('.book-item')).map(el => ({
        title: el.querySelector('.title')?.textContent,
        author: el.querySelector('.author')?.textContent
      }));
    });

    // Screenshot for debugging
    await this.playwright.screenshot({
      path: `search-${query}-${Date.now()}.png`
    });

    return results;
  }
}
```

### Pattern 2: SQLite for Caching
```typescript
class CacheManager {
  private sqlite: SQLiteMCP;

  async getCachedSearch(query: string): Promise<Book[] | null> {
    const result = await this.sqlite.query(`
      SELECT results FROM searches
      WHERE query = ? AND created_at > datetime('now', '-1 hour')
      ORDER BY created_at DESC LIMIT 1
    `, [query]);

    return result[0]?.results ? JSON.parse(result[0].results) : null;
  }

  async cacheSearch(query: string, results: Book[]) {
    await this.sqlite.execute(`
      INSERT INTO searches (query, results, result_count)
      VALUES (?, ?, ?)
    `, [query, JSON.stringify(results), results.length]);
  }
}
```

### Pattern 3: Filesystem Monitoring
```typescript
class DownloadWatcher {
  private filesystem: FilesystemMCP;

  async watchDownloads() {
    await this.filesystem.watch('./downloads', async (event) => {
      if (event.type === 'create' && event.path.endsWith('.pdf')) {
        console.log(`New download: ${event.path}`);

        // Auto-process for RAG
        await this.processForRAG(event.path);
      }
    });
  }

  async cleanOldDownloads() {
    const files = await this.filesystem.list('./downloads');
    const thirtyDaysAgo = Date.now() - (30 * 24 * 60 * 60 * 1000);

    for (const file of files) {
      if (file.stats.mtime < thirtyDaysAgo) {
        await this.filesystem.delete(file.path);
        console.log(`Cleaned old file: ${file.path}`);
      }
    }
  }
}
```

## Recommended Workflow

### Development Cycle with MCP Servers

1. **Start Development Session**:
```bash
# Start all MCP servers
npm run mcp:start

# Watch logs
npm run mcp:logs
```

2. **Test with Playwright**:
```bash
# Run E2E tests
npm run test:e2e

# Debug specific scenario
npm run test:e2e -- --grep "login"
```

3. **Monitor with SQLite**:
```bash
# Check cache effectiveness
sqlite3 zlibrary.db "SELECT COUNT(*) as cache_hits FROM searches WHERE created_at > datetime('now', '-1 hour')"

# Domain health
sqlite3 zlibrary.db "SELECT domain, failure_count, last_success FROM domains ORDER BY failure_count DESC"
```

4. **Clean Up**:
```bash
# Stop MCP servers
npm run mcp:stop

# Clean test artifacts
npm run clean
```

## Performance Impact

### Resource Usage
- **Playwright**: ~200MB RAM, CPU spikes during navigation
- **SQLite**: <50MB RAM, minimal CPU
- **Filesystem**: Negligible
- **Sequential**: Variable based on complexity
- **GitHub**: Network only

### Optimization Tips
1. Run Playwright in headless mode for CI
2. Use SQLite WAL mode for better concurrency
3. Batch filesystem operations
4. Cache GitHub API responses
5. Limit Sequential thinking time

---

*Configure these MCP servers based on your development needs. Start with Playwright and SQLite as minimum.*