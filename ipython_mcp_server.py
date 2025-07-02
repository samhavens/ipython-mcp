#!/usr/bin/env python3
"""
IPython Kernel MCP Server

A Model Context Protocol server that connects to an existing IPython kernel
and provides code execution capabilities with persistent state.
"""

from mcp.server.fastmcp import FastMCP
import json
import zmq
import uuid
import hmac
import hashlib
import time
from datetime import datetime
from pathlib import Path

# Initialize the MCP server
mcp = FastMCP("ipython-kernel")

# Global connection state
kernel_connection = None
context = None
shell_socket = None
iopub_socket = None


def sign_message(msg_lst, key):
    """Sign a message with HMAC"""
    h = hmac.new(key.encode('utf-8'), digestmod=hashlib.sha256)
    for m in msg_lst:
        h.update(m)
    return h.hexdigest().encode('utf-8')


@mcp.tool()
def connect_to_kernel(connection_file: str) -> str:
    """
    Connect to an existing IPython kernel using its connection file.
    
    Args:
        connection_file: Path to the kernel connection JSON file
        
    Returns:
        Connection status message
    """
    global kernel_connection, context, shell_socket, iopub_socket
    
    try:
        # Read connection file
        connection_path = Path(connection_file).expanduser()
        if not connection_path.exists():
            return f"❌ Connection file not found: {connection_path}"
        
        with open(connection_path, 'r') as f:
            kernel_connection = json.load(f)
        
        # Close existing connections if any
        if shell_socket:
            shell_socket.close()
        if iopub_socket:
            iopub_socket.close()
        if context:
            context.term()
        
        # Create new ZMQ context and sockets
        context = zmq.Context()
        
        # Shell socket for sending requests
        shell_socket = context.socket(zmq.DEALER)
        shell_addr = f"tcp://{kernel_connection['ip']}:{kernel_connection['shell_port']}"
        shell_socket.connect(shell_addr)
        
        # IOPub socket for receiving output
        iopub_socket = context.socket(zmq.SUB)
        iopub_addr = f"tcp://{kernel_connection['ip']}:{kernel_connection['iopub_port']}"
        iopub_socket.connect(iopub_addr)
        iopub_socket.setsockopt(zmq.SUBSCRIBE, b'')
        
        return f"✅ Connected to IPython kernel at {kernel_connection['ip']}:{kernel_connection['shell_port']}"
        
    except Exception as e:
        return f"❌ Failed to connect: {str(e)}"


@mcp.tool()
def execute_code(code: str) -> str:
    """
    Execute Python code on the connected IPython kernel.
    
    Args:
        code: Python code to execute
        
    Returns:
        Execution results including output, results, and any errors
    """
    global kernel_connection, shell_socket, iopub_socket
    
    if not kernel_connection or not shell_socket or not iopub_socket:
        return "❌ Not connected to kernel. Use connect_to_kernel() first."
    
    try:
        # Create execute request message
        msg_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        
        header = {
            "msg_id": msg_id,
            "username": "ipython-mcp",
            "session": session_id,
            "date": datetime.now().isoformat(),
            "msg_type": "execute_request",
            "version": "5.3"
        }
        
        content = {
            "code": code,
            "silent": False,
            "store_history": True,
            "user_expressions": {},
            "allow_stdin": False,
            "stop_on_error": True
        }
        
        # Prepare and sign message
        msg_parts = [
            json.dumps(header).encode('utf-8'),
            b'{}',  # parent_header
            b'{}',  # metadata
            json.dumps(content).encode('utf-8')
        ]
        
        signature = sign_message(msg_parts, kernel_connection['key'])
        
        # Send message
        shell_socket.send_multipart([
            b'',
            b'<IDS|MSG>',
            signature,
            msg_parts[0],
            msg_parts[1],
            msg_parts[2],
            msg_parts[3]
        ])
        
        # Collect output
        results = []
        errors = []
        streams = []
        
        # Wait for execution to complete
        execution_done = False
        timeout_count = 0
        
        while not execution_done and timeout_count < 100:
            try:
                msg = iopub_socket.recv_multipart(zmq.NOBLOCK)
                if len(msg) >= 7:
                    header = json.loads(msg[3])
                    content = json.loads(msg[6])
                    
                    msg_type = header.get('msg_type')
                    
                    if msg_type == 'execute_result':
                        result = content.get('data', {}).get('text/plain', '')
                        if result:
                            results.append(result)
                    
                    elif msg_type == 'stream':
                        stream_text = content.get('text', '').strip()
                        if stream_text:
                            streams.append(stream_text)
                    
                    elif msg_type == 'error':
                        error_name = content.get('ename', 'Error')
                        error_value = content.get('evalue', '')
                        traceback = content.get('traceback', [])
                        
                        error_msg = f"{error_name}: {error_value}"
                        if traceback:
                            # Clean up ANSI codes from traceback
                            clean_traceback = []
                            for line in traceback:
                                # Simple ANSI code removal (basic)
                                clean_line = line.replace('\x1b[0;31m', '').replace('\x1b[0m', '')
                                clean_line = clean_line.replace('\x1b[1;32m', '').replace('\x1b[0;32m', '')
                                clean_traceback.append(clean_line)
                            error_msg += "\n" + "\n".join(clean_traceback)
                        errors.append(error_msg)
                    
                    elif msg_type == 'status':
                        if content.get('execution_state') == 'idle':
                            execution_done = True
                
                timeout_count = 0  # Reset timeout if we got a message
                
            except zmq.Again:
                timeout_count += 1
                time.sleep(0.01)
        
        # Format output
        output_parts = []
        
        # Add streams (print output)
        for stream in streams:
            output_parts.append(stream)
        
        # Add results (expression values)
        for result in results:
            output_parts.append(result)
        
        # Add errors
        for error in errors:
            output_parts.append(f"❌ {error}")
        
        if not output_parts:
            return "✅ Code executed successfully (no output)"
        
        return "\n".join(output_parts)
        
    except Exception as e:
        return f"❌ Execution failed: {str(e)}"


@mcp.tool()
def kernel_status() -> str:
    """
    Get the current kernel connection status.
    
    Returns:
        Status information about the kernel connection
    """
    global kernel_connection
    
    if not kernel_connection:
        return "❌ Not connected to any kernel"
    
    return f"✅ Connected to kernel at {kernel_connection['ip']}:{kernel_connection['shell_port']}"


@mcp.tool()
def disconnect_kernel() -> str:
    """
    Disconnect from the current kernel.
    
    Returns:
        Disconnection status message
    """
    global kernel_connection, context, shell_socket, iopub_socket
    
    try:
        if shell_socket:
            shell_socket.close()
            shell_socket = None
        if iopub_socket:
            iopub_socket.close()
            iopub_socket = None
        if context:
            context.term()
            context = None
        
        kernel_connection = None
        return "✅ Disconnected from kernel"
        
    except Exception as e:
        return f"❌ Error during disconnection: {str(e)}"


if __name__ == "__main__":
    mcp.run()