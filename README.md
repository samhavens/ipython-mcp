# IPython Kernel MCP Server

An MCP server that connects to existing IPython kernels, allowing Claude to execute code in a shared persistent environment with your IDE.

MCP is an open protocol created by Anthropic that enables AI systems to interact with external tools and data sources. While currently supported by Claude (Desktop and CLI), the open standard allows other LLMs to adopt it in the future.

## Features

- **Connect to existing IPython kernels** via connection files
- **Persistent state** - variables and imports shared between Claude and your IDE
- **Full IPython support** - magic commands, rich display, etc.
- **Real-time collaboration** - you code in IDE, Claude can inspect/debug

## Requirements

- Python 3.8+
- IPython/Jupyter installed
- `zmq` and `mcp` Python packages

## Quick Start

For first-time users, the fastest way to get started:

1. **Start an IPython kernel**:
   ```bash
   ipython kernel
   ```

2. **Add ipython-mcp to Claude CLI**:
   ```bash
   claude mcp add ipython-kernel python /home/gabi/ipython-mcp/ipython_mcp_server.py
   ```

3. **Start using Claude CLI**:
   ```bash
   claude
   ```
   Then connect to your kernel:
   ```
   > connect to my ipython kernel using connection file ~/.local/share/jupyter/runtime/kernel-12345.json
   
   ● ipython-kernel:connect_to_kernel (MCP)(connection_file: "~/.local/share/jupyter/runtime/kernel-12345.json")
     ⎿  ✅ Connected to IPython kernel at 127.0.0.1:5555
   
   > execute x = 42; print(f"x = {x}")
   
   ● ipython-kernel:execute_code (MCP)(code: "x = 42; print(f'x = {x}')")
     ⎿  x = 42
   ```

## Installation

### For Claude CLI

Run directly with Python (no pip installation required):

```bash
claude mcp add ipython-kernel python /home/gabi/ipython-mcp/ipython_mcp_server.py
```

### For Claude Desktop

Add to your Claude Desktop configuration file:

```json
{
  "mcpServers": {
    "ipython-kernel": {
      "command": "python",
      "args": ["/home/gabi/ipython-mcp/ipython_mcp_server.py"]
    }
  }
}
```

## Usage

### Starting an IPython Kernel

**Option 1: From your IDE**
- Most IDEs with Jupyter support will start kernels automatically
- Look for kernel connection info in IDE settings/status

**Option 2: Manual start**
```bash
ipython kernel
```

**Option 3: With specific connection file**
```bash
ipython kernel --ConnectionFileMixin.connection_file=my_connection.json
```

### Finding Connection Files

Connection files are typically located in:
```bash
# List active kernels
ls ~/.local/share/jupyter/runtime/

# Example files:
# kernel-12345.json
# kernel-67890.json
```

### Tools

1. `connect_to_kernel(connection_file)` - Connect to IPython kernel using JSON connection file
2. `execute_code(code)` - Execute Python code on the connected kernel  
3. `kernel_status()` - Check current connection status
4. `disconnect_kernel()` - Disconnect from current kernel

### Example Workflow

```bash
# 1. Start kernel
ipython kernel

# 2. Note the connection file path from kernel output
# 3. In Claude CLI, connect to the kernel
> connect to kernel using ~/.local/share/jupyter/runtime/kernel-12345.json

# 4. Execute code via Claude
> run: import pandas as pd; df = pd.DataFrame({'a': [1,2,3]})

# 5. Meanwhile, in your IDE connected to the same kernel:
# The 'df' variable is available! Both environments share state.

# 6. Back in Claude:
> show me df.head()
```

## Architecture

This MCP server acts as a **bridge** between Claude and existing IPython kernels:

- **Claude** ↔ **MCP Server** ↔ **IPython Kernel** ↔ **Your IDE**
- All parties share the same persistent Python environment
- Variables, imports, and state persist across all connections
- Uses standard Jupyter messaging protocol (ZMQ) for communication