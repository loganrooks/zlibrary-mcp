# Z-Library MCP - Implementation Roadmap

## ✅ Completed Tasks

### 1. Comprehensive Documentation Created
- ✅ **ISSUES.md**: Documented all 9 critical/high priority issues, 7 medium priority, and numerous improvement opportunities
- ✅ **PROJECT_CONTEXT.md**: Complete project context including architecture, principles, and workflow
- ✅ **PATTERNS.md**: Code patterns for error handling, retry logic, caching, and testing
- ✅ **DEBUGGING.md**: Troubleshooting guide with diagnostic scripts and solutions
- ✅ **MCP_SERVERS.md**: Configuration for Playwright, SQLite, and other development MCP servers
- ✅ **META_LEARNING.md**: Lessons learned, architectural insights, and wisdom transfer
- ✅ **CLAUDE.md**: Updated with references to all .claude documentation

### 2. Research Completed
- ✅ Confirmed Z-Library has NO official API (using internal EAPI)
- ✅ Identified best Python wrapper: `sertraline/zlibrary`
- ✅ Discovered "Hydra mode" infrastructure (personalized domains)
- ✅ Researched alternative APIs (not needed per user preference)

## 🚀 Implementation Priority Queue

### Phase 1: Critical Fixes (Do Now)

#### 1. Fix Venv Manager Test Warnings
**File**: `src/lib/venv-manager.ts`
**Issue**: Line 255 - `Cannot read properties of undefined (reading 'trim')`

```typescript
// Current problematic code (line 255)
const venvPath = configContent?.trim();

// Fix: Add proper null checking
const venvPath = typeof configContent === 'string' ? configContent.trim() : null;
if (!venvPath) {
  throw new Error('Invalid or empty venv config');
}
```

#### 2. Implement Retry Logic with Exponential Backoff
**Create**: `src/lib/retry-manager.ts`

```typescript
export async function withRetry<T>(
  operation: () => Promise<T>,
  options: RetryOptions = {}
): Promise<T> {
  const {
    maxRetries = 3,
    initialDelay = 1000,
    maxDelay = 30000,
    factor = 2,
    shouldRetry = (error: any) => !error.fatal
  } = options;

  let lastError: any;
  let delay = initialDelay;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;

      if (attempt === maxRetries || !shouldRetry(error)) {
        throw error;
      }

      console.log(`Attempt ${attempt + 1} failed, retrying in ${delay}ms...`);
      await new Promise(resolve => setTimeout(resolve, delay));
      delay = Math.min(delay * factor, maxDelay);
    }
  }

  throw lastError;
}
```

#### 3. Add Comprehensive Logging
**Create**: `src/lib/logger.ts`

```typescript
import winston from 'winston';

export const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: { service: 'zlibrary-mcp' },
  transports: [
    new winston.transports.File({ filename: 'logs/error.log', level: 'error' }),
    new winston.transports.File({ filename: 'logs/combined.log' }),
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.simple()
      )
    })
  ]
});
```

### Phase 2: Enhancement Features (Next Week)

#### 4. Implement Fuzzy Search
**Create**: `src/lib/fuzzy-search.ts`

```typescript
import levenshtein from 'fast-levenshtein';

export class FuzzySearcher {
  findBestMatches(query: string, candidates: string[], threshold = 0.8): string[] {
    const scores = candidates.map(candidate => ({
      candidate,
      score: this.calculateSimilarity(query, candidate)
    }));

    return scores
      .filter(s => s.score >= threshold)
      .sort((a, b) => b.score - a.score)
      .map(s => s.candidate);
  }

  private calculateSimilarity(s1: string, s2: string): number {
    const distance = levenshtein.get(s1.toLowerCase(), s2.toLowerCase());
    const maxLength = Math.max(s1.length, s2.length);
    return 1 - (distance / maxLength);
  }
}
```

#### 5. Create Download Queue Management
**Create**: `src/lib/download-queue.ts`

```typescript
export class DownloadQueue extends EventEmitter {
  private queue: DownloadTask[] = [];
  private active: Map<string, DownloadTask> = new Map();
  private maxConcurrent = 3;

  async add(task: DownloadTask): Promise<void> {
    this.queue.push(task);
    this.emit('taskAdded', task);
    await this.process();
  }

  private async process(): Promise<void> {
    while (this.queue.length > 0 && this.active.size < this.maxConcurrent) {
      const task = this.queue.shift()!;
      this.active.set(task.id, task);

      this.executeTask(task)
        .then(() => {
          this.active.delete(task.id);
          this.emit('taskCompleted', task);
          this.process();
        })
        .catch(error => {
          this.active.delete(task.id);
          this.emit('taskFailed', { task, error });
          this.process();
        });
    }
  }
}
```

### Phase 3: Infrastructure (Week 3)

#### 6. Docker Development Environment
**Create**: `Dockerfile`

```dockerfile
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:18-alpine

RUN apk add --no-cache python3 py3-pip

WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package*.json ./
COPY lib ./lib
COPY zlibrary ./zlibrary
COPY requirements.txt ./

RUN python3 -m venv venv && \
    source venv/bin/activate && \
    pip install -r requirements.txt

CMD ["node", "dist/index.js"]
```

**Create**: `docker-compose.yml`

```yaml
version: '3.8'

services:
  zlibrary-mcp:
    build: .
    environment:
      - ZLIBRARY_EMAIL=${ZLIBRARY_EMAIL}
      - ZLIBRARY_PASSWORD=${ZLIBRARY_PASSWORD}
      - LOG_LEVEL=debug
    volumes:
      - ./downloads:/app/downloads
      - ./processed_rag_output:/app/processed_rag_output
      - ./logs:/app/logs
    ports:
      - "3000:3000"

  playwright:
    image: mcr.microsoft.com/playwright:v1.40.0-focal
    command: npx @modelcontextprotocol/server-playwright
    network_mode: host

  sqlite:
    image: keinos/sqlite3:latest
    volumes:
      - ./data:/data
```

## 📋 Testing Checklist

### After Each Implementation:
- [ ] Run `npm test` - all tests should pass
- [ ] Run `pytest` - Python tests should pass
- [ ] Check `npm run lint` - no linting errors
- [ ] Test with real Z-Library credentials
- [ ] Verify error handling works
- [ ] Check memory usage doesn't increase
- [ ] Update relevant documentation

## 🎯 Success Metrics

### Phase 1 Success (Week 1)
- ✅ No test warnings in console
- ✅ All network requests have retry logic
- ✅ Comprehensive logs for debugging
- ✅ Error messages are informative

### Phase 2 Success (Week 2)
- ✅ Fuzzy search returns relevant results
- ✅ Download queue handles 10+ books
- ✅ Cache hit rate > 30%
- ✅ Domain rotation works automatically

### Phase 3 Success (Week 3)
- ✅ Docker container runs without issues
- ✅ MCP servers integrate properly
- ✅ E2E tests pass with Playwright
- ✅ SQLite caching improves performance

## 🛠️ Development Commands

```bash
# Start development with all MCP servers
npm run dev:full

# Run specific fixes
npm run fix:venv        # Fix venv manager
npm run fix:retry       # Add retry logic
npm run fix:logging     # Setup logging

# Test improvements
npm run test:fuzzy      # Test fuzzy search
npm run test:queue      # Test download queue
npm run test:e2e        # Run E2E with Playwright

# Build and deploy
npm run build:docker    # Build Docker image
npm run deploy:local    # Deploy locally
```

## 📚 Reference Implementation Files

When implementing, refer to these pattern files:
- Retry Logic: `.claude/PATTERNS.md#pattern-retry-with-exponential-backoff`
- Error Handling: `.claude/PATTERNS.md#pattern-error-context-enrichment`
- Logging: `.claude/PATTERNS.md#pattern-structured-logging`
- Testing: `.claude/PATTERNS.md#pattern-test-data-builders`
- Domain Management: `.claude/PATTERNS.md#pattern-dynamic-domain-discovery`

## 🚦 Go/No-Go Criteria

### Before Moving to Production:
1. **Performance**: Search < 2s, Download initiation < 1s
2. **Reliability**: Success rate > 95% for valid requests
3. **Resilience**: Handles domain failures gracefully
4. **Observability**: All operations logged with context
5. **Testing**: >80% code coverage, E2E tests pass

---

*Start with Phase 1 immediately. Each phase builds on the previous one. Update this roadmap as tasks are completed.*