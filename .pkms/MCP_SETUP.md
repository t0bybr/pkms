# PKMS MCP Server Setup

The PKMS MCP (Model Context Protocol) server exposes PKMS tools to AI agents like Claude Desktop and Cline (VSCode extension).

## Installation

```bash
# Install MCP dependencies
pip install -e ".[mcp]"

# Make server executable
chmod +x .pkms/mcp_server.py
```

## Configuration

### Cline (VSCode Extension)

1. Open VSCode Settings (`Cmd/Ctrl + ,`)
2. Search for "Cline"
3. Click "Edit in settings.json"
4. Add PKMS server:

```json
{
  "cline.mcpServers": {
    "pkms": {
      "command": "python",
      "args": ["/absolute/path/to/pkms/.pkms/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/pkms"
      }
    }
  }
}
```

**Important:** Replace `/absolute/path/to/pkms` with your actual path!

### Claude Desktop

1. Open config file:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. Add PKMS server:

```json
{
  "mcpServers": {
    "pkms": {
      "command": "python",
      "args": ["/absolute/path/to/pkms/.pkms/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/pkms"
      }
    }
  }
}
```

3. Restart Claude Desktop

## Available Tools

### 1. `search`
Search the knowledge base using hybrid search (BM25 + semantic).

**Parameters:**
- `query` (required): Search query
- `limit` (optional): Max results (default: 10)
- `keyword_only` (optional): Use only BM25
- `semantic_only` (optional): Use only semantic search

**Example:**
```
Search for "pizza recipe" in my knowledge base
```

### 2. `get_note`
Retrieve a specific note by ULID or slug.

**Parameters:**
- `identifier` (required): Note ULID or slug

**Example:**
```
Get the note with slug "pizza-recipe"
```

### 3. `list_notes`
List all notes with metadata.

**Parameters:**
- `limit` (optional): Max notes (default: 50)
- `tags` (optional): Filter by tags

**Example:**
```
List all notes tagged "cooking"
```

### 4. `update_metadata`
Update metadata after manual edits to markdown files.

**Parameters:**
- `path` (optional): Specific file or directory

**Example:**
```
Update metadata for all vault notes
```

### 5. `rebuild_indexes`
Rebuild search indexes (BM25 and embeddings).

**Parameters:**
- `full` (optional): Full rebuild (chunk + embed + index)

**Example:**
```
Rebuild search indexes
```

## Usage with Ollama + Cline

Cline supports using Ollama models with MCP tools!

**Setup:**
1. Configure MCP server (see above)
2. In Cline settings, select Ollama as API provider
3. Choose your model (e.g., `llama3.1`, `qwen2.5-coder`)

**Example Prompt:**
```
Search my knowledge base for "docker setup" and create a summary
```

The agent can now use PKMS tools directly!

## Troubleshooting

### "Server not responding"

**Check paths:**
```bash
# Test server manually
python /path/to/pkms/.pkms/mcp_server.py
# Should start without errors
```

**Check Python path:**
```bash
which python
# Use this path in config
```

### "Module not found"

**Install dependencies:**
```bash
cd /path/to/pkms
pip install -e ".[mcp]"
```

### "Permission denied"

**Make executable:**
```bash
chmod +x .pkms/mcp_server.py
```

## Development

To add new tools, edit `.pkms/mcp_server.py`:

1. Add tool definition in `list_tools()`
2. Implement handler in `call_tool()`
3. Restart MCP server (reload Cline/Claude Desktop)

## Learn More

- MCP Specification: https://modelcontextprotocol.io
- Cline Extension: https://github.com/clinebot/cline
- Claude Desktop: https://claude.ai/download
