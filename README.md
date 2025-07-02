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
- `ipython`, `zmq` and `mcp` Python packages

## Quick Start

For first-time users, the fastest way to get started:

1. **Start an IPython kernel**:
   ```bash
   ipython kernel
   ```

2. **Add ipython-mcp to Claude CLI**:
   ```bash
   claude mcp add ipython-kernel "uv run ipython_mcp/server.py"
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

### Lightweight Installation (Claude CLI only)

Run directly with uv (no pip installation required, may be slower on startup; best for trying it out at first):

```bash
claude mcp add ipython-kernel "uv run ipython_mcp/server.py"
```

### Full Installation

#### pip (recommended for regular use)

```bash
pip install ipython-mcp
```

*Note: Consider using a virtual environment to avoid dependency conflicts:*
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install ipython-mcp
```

##### Adding to Claude CLI

After installation:

```bash
claude mcp add ipython-kernel ipython-mcp
```

##### Adding to Claude Desktop

Add to your Claude Desktop configuration file:

```json
{
  "mcpServers": {
    "ipython-kernel": {
      "command": "ipython-mcp"
    }
  }
}
```

For uv-based installation:
```json
{
  "mcpServers": {
    "ipython-kernel": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/ipython-mcp",
        "run",
        "ipython_mcp/server.py"
      ]
    }
  }
}
```

## Usage

### Starting an IPython Kernel

**Option 1: Using the demo connection file (recommended for testing)**
```bash
ipython kernel --ConnectionFileMixin.connection_file=~/ipython-mcp/demo_connection.json
```
This uses predictable ports (5555-5559) and makes it easy to connect.

**Option 2: Basic kernel start**
```bash
ipython kernel
```
IPython will create a random connection file. Note the output path:
```
[IPKernelApp] Connection file: /home/user/.local/share/jupyter/runtime/kernel-12345.json
```

**Option 3: From your IDE**
- Most IDEs with Jupyter support will start kernels automatically
- Look for kernel connection info in IDE settings/status

**Option 4: With custom connection file**
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

1. `start_kernel(connection_file=None)` - Start new IPython kernel and auto-connect
2. `connect_to_kernel(connection_file=None)` - Connect to existing IPython kernel
3. `execute_code(code)` - Execute Python code on the connected kernel  
4. `kernel_status()` - Check current connection status
5. `disconnect_kernel()` - Disconnect from current kernel

### Connection File Resolution

The tools use this priority for finding connection files:

1. **Explicit parameter** - `connection_file` argument (highest priority)
2. **Environment variable** - `IPYTHON_MCP_CONNECTION` 
3. **Package default** - Built-in `default_connection.json` (ports 5555-5559)

### Environment Variables

- `IPYTHON_MCP_CONNECTION` - Default connection file path to use when none specified

### Example Workflow

**Simplest approach - let the MCP server handle everything:**
```bash
# In Claude CLI, start a kernel using package defaults
> start a new ipython kernel

# The tool will:
# 1. Use built-in default_connection.json (ports 5555-5559)
# 2. Start IPython kernel in background
# 3. Auto-connect to it
# 4. Return connection details

# Now execute code
> run: import pandas as pd; df = pd.DataFrame({'a': [1,2,3]})
```

**Using environment variable:**
```bash
# Set your preferred connection file
export IPYTHON_MCP_CONNECTION=/path/to/my/connection.json

# In Claude CLI
> start a new ipython kernel
# Will use your env var connection file
```

**Manual kernel startup (traditional approach):**
```bash
# 1. Start kernel manually
ipython kernel

# 2. In Claude CLI, connect to the kernel  
> connect to my ipython kernel using ~/.local/share/jupyter/runtime/kernel-12345.json

# 3. Execute code
> run: import pandas as pd; df = pd.DataFrame({'a': [1,2,3]})
```

## IDE Integration

This project is designed with **Spyder IDE** in mind due to its unique features:

- **Inline plots** - graphs display directly in the IDE without separate windows
- **Flexible code execution** - run individual lines, selections, or entire files seamlessly
- **Integrated IPython console** - no copy/paste artifacts that plague other IDEs
- **Variable explorer** - inspect shared state between Claude and your IDE in real-time

While other IDEs can work with this MCP server, Spyder provides a smooth experience for data science workflows where you want both interactive coding and AI assistance on the same persistent Python environment.

## Security Considerations

This MCP server uses Jupyter's standard connection protocol with HMAC-SHA256 message signing.

### Connection File Security

**IF you're using this locally** (single-user machine):
- The default connection file with demo key (`demo-key-12345`) is perfectly fine
- Binds to localhost (127.0.0.1) only - not accessible from network
- Simplifies setup and debugging with predictable ports and keys

**BUT IF you need enhanced security** (shared machines, network access, production):
```bash
# Generate a secure connection file with random key
python -c "
import json, secrets
conn = {
    'shell_port': 5555, 'iopub_port': 5556, 'stdin_port': 5557,
    'control_port': 5558, 'hb_port': 5559, 'ip': '127.0.0.1',
    'key': secrets.token_hex(32), 'transport': 'tcp',
    'signature_scheme': 'hmac-sha256', 'kernel_name': ''
}
print(json.dumps(conn, indent=2))
" > secure_connection.json

# Use your secure connection file (via env var or explicit parameter)
export IPYTHON_MCP_CONNECTION=secure_connection.json
ipython kernel --ConnectionFileMixin.connection_file=secure_connection.json
```

**Additional Security Measures**:
- Set restrictive file permissions: `chmod 600 your_connection.json`
- Use different ports to avoid conflicts
- Never commit connection files with real keys to version control
- Consider firewall rules if binding to non-localhost addresses

## WSL/Windows Integration

When using Claude CLI on Windows (which runs in WSL), you may want to run the IPython kernel on the Windows side while keeping the MCP server in WSL. This allows you to use Windows Python environments (like Miniconda) while still accessing them from Claude CLI.

**Start Windows IPython kernel from WSL:**
```bash
# Using PowerShell to start kernel in background
powershell.exe -Command "Start-Process -WindowStyle Hidden cmd -ArgumentList '/c', 'C:\Users\<USERNAME>\miniconda3\Scripts\activate.bat C:\Users\<USERNAME>\miniconda3 && python -m ipykernel_launcher -f <PATH_TO_CONNECTION_JSON>'"
```

Where `<PATH_TO_CONNECTION_JSON>` can be:
- Your own connection file: `\\\\wsl.localhost\\Ubuntu\\home\\<USER>\\my_connection.json`
- Package default (if pip installed on WSL): `\\\\wsl.localhost\\Ubuntu\\home\\<USER>\\.local\\lib\\python3.x\\site-packages\\ipython_mcp\\default_connection.json`
- Development version: `\\\\wsl.localhost\\Ubuntu\\home\\<USER>\\ipython-mcp\\src\\ipython_mcp\\default_connection.json`

This approach:
- Activates your Windows Miniconda environment
- Starts the IPython kernel using the shared connection file
- Runs in a hidden background window
- Allows WSL-based Claude CLI to connect to Windows Python environment

### WSL2 Port Communication (Windows Users)

*Skip this section if you're not on Windows.*

Since Claude CLI is WSL-only on Windows, but you might want to use Windows Python environments or IDEs, you need proper port communication between WSL2 and Windows.

#### .wslconfig File Setup
Location: `C:\Users\{YourUsername}\.wslconfig`

Add mirrored networking configuration:
```ini
# Mirrored networking mode for seamless port communication
networkingMode=mirrored
dnsTunneling=true
firewall=true
autoProxy=true
```

#### Restart WSL2
Run from Windows PowerShell/CMD (NOT from within WSL):
```powershell
wsl --shutdown
# Wait a few seconds, then start WSL again
```

#### What Mirrored Networking Provides

- ✅ Direct localhost communication both ways
- ✅ No manual port forwarding needed
- ✅ Better VPN compatibility
- ✅ Simplified networking (Windows and WSL2 share network interfaces)
- ✅ Firewall rules automatically handled

#### Test Port Communication

Test WSL2 → Windows (localhost):
```bash
# In WSL2, test connection to Windows IPython kernel
python -c "import zmq; ctx = zmq.Context(); sock = ctx.socket(zmq.REQ); sock.connect('tcp://127.0.0.1:5555'); print('Connection successful')"
```

Test Windows → WSL2 (localhost):
```powershell
# In Windows, test connection to WSL2 service
python -c "import zmq; ctx = zmq.Context(); sock = ctx.socket(zmq.REQ); sock.connect('tcp://127.0.0.1:5555'); print('Connection successful')"
```

#### Known Limitations of Mirrored Networking
1. **Localhost-only services**: Some services may not be fully mirrored
2. **mDNS doesn't work** in mirrored mode
3. **Some Docker configurations** may have issues
4. **Requires Windows 11 22H2+** (build 22621+)

## Architecture

This MCP server acts as a **bridge** between Claude and existing IPython kernels:

- **Claude** ↔ **MCP Server** ↔ **IPython Kernel** ↔ **Your IDE**
- All parties share the same persistent Python environment
- Variables, imports, and state persist across all connections
- Uses standard Jupyter messaging protocol (ZMQ) for communication

### Responsibility Boundaries

**The MCP Server manages:**
- Connection to existing kernels via ZMQ sockets
- Message formatting and protocol compliance
- Code execution requests and response handling

**The User manages:**
- Kernel lifecycle (starting, stopping, monitoring)
- Connection file creation and security
- Kernel configuration and environment setup

**Why this separation?**
- **Flexibility**: Start kernels however you prefer (CLI, IDE, Jupyter, etc.)
- **Persistence**: Kernels can outlive MCP connections and be shared between tools
- **Control**: You decide kernel configuration, environment, and lifecycle
- **Simplicity**: MCP server focuses on communication, not process management

The `start_kernel` tool is provided as a **convenience helper** - not a requirement. Many users prefer to start kernels through their IDE, Jupyter, or custom scripts.