# MCP Configuration Templates

Quick reference for adding Z-Library MCP server to your projects.

---

## For This Computer (System-Wide Installation)

**Installation Location**: `/home/rookslog/mcp-servers/zlibrary-mcp/`

### Copy-Paste Configuration

**Copy this into your project's `.mcp.json`**:

```json
{
  "mcpServers": {
    "zlibrary": {
      "command": "node",
      "args": ["/home/rookslog/mcp-servers/zlibrary-mcp/dist/index.js"],
      "env": {
        "ZLIBRARY_EMAIL": "logansrooks@gmail.com",
        "ZLIBRARY_PASSWORD": "190297@Lsr"
      }
    }
  }
}
```

**That's it!** Restart Claude Code and you'll have all 11 Z-Library tools.

---

## When to Add This Config

### ✅ DO Add to .mcp.json For:

**Research Projects**:
- Academic paper searches
- Literature reviews
- Citation analysis
- Bibliography building

**RAG/AI Projects**:
- Knowledge base creation
- Training data collection
- Document corpus building
- Semantic search preparation

**Learning Projects**:
- Finding study materials
- Course development
- Reference libraries

### ❌ DON'T Add to .mcp.json For:

**Pure Coding Projects**:
- Web development (React, Node.js, etc.)
- API development
- Tool building
- General software development

**Data Science (Usually)**:
- Working with existing datasets
- Model training
- Data analysis
- (Unless doing literature review)

**Best Practice**: Only configure servers you actually use in that project!

---

## Quick Test

After adding config and restarting Claude Code:

```
Ask Claude: "What zlibrary tools are available?"

Expected: List of 11 tools including:
- search_books
- search_by_term (navigate by concepts)
- get_book_metadata (60 terms, 11 booklists!)
- download_book_to_file
- And 7 more...
```

---

## Example: Using in a Research Project

**Project**: `~/projects/philosophy-research/`

**Step 1**: Create `.mcp.json`
```bash
cd ~/projects/philosophy-research
cat > .mcp.json << 'EOF'
{
  "mcpServers": {
    "zlibrary": {
      "command": "node",
      "args": ["/home/rookslog/mcp-servers/zlibrary-mcp/dist/index.js"],
      "env": {
        "ZLIBRARY_EMAIL": "logansrooks@gmail.com",
        "ZLIBRARY_PASSWORD": "190297@Lsr"
      }
    }
  }
}
EOF
```

**Step 2**: Restart Claude Code

**Step 3**: Use it!
```
"Search Z-Library for books on phenomenology by Hegel"
"Get the complete metadata for the first result including terms and booklists"
"Download it and process for RAG"
```

---

## Multiple Servers in One Project

You can combine multiple MCP servers:

```json
{
  "mcpServers": {
    "zlibrary": {
      "command": "node",
      "args": ["/home/rookslog/mcp-servers/zlibrary-mcp/dist/index.js"],
      "env": {
        "ZLIBRARY_EMAIL": "logansrooks@gmail.com",
        "ZLIBRARY_PASSWORD": "190297@Lsr"
      }
    },
    "sqlite": {
      "command": "sqlite-mcp",
      "args": ["--db", "research.db"]
    },
    "playwright": {
      "command": "playwright-mcp"
    }
  }
}
```

Each server provides its own tools. Use what you need!

---

## Troubleshooting

### "Tools not showing up"

1. Verify .mcp.json has correct absolute path
2. Restart Claude Code
3. Check logs: `~/mcp-servers/zlibrary-mcp/logs/`

### "ENOENT: no such file"

- Path in .mcp.json must be absolute
- Use: `/home/rookslog/mcp-servers/...`
- Not: `~/mcp-servers/...` (~ doesn't expand in JSON)

### "Rate limit detected"

- Z-Library limits login attempts
- Wait 10-15 minutes
- Normal behavior, handled gracefully

---

## Summary

**System Location**: `/home/rookslog/mcp-servers/zlibrary-mcp/` ✅

**How to Use**:
1. Copy JSON config above
2. Paste into project's `.mcp.json`
3. Restart Claude Code
4. Use 11 Z-Library tools!

**When to Use**: Research, RAG, learning projects

**When NOT to Use**: Pure coding projects (keep it clean!)

**Status**: Ready to use across all your projects! 🚀
