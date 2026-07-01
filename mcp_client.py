import asyncio
import threading
import time
from telemetry import log_mcp_call

# Standard MCP SDK Imports
# Note: User must run 'pip install mcp' to install the official MCP Python SDK
from mcp import ClientSession
from mcp.client.sse import sse_client

MCP_SERVER_SSE_URL = "http://localhost:8000/sse"

def run_async_safe(coro):
    """Thread-safe runner for async coroutines, compatible with Streamlit worker threads."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    if loop.is_running():
        # Streamlit's server loop is running in the main thread; run coro in a dedicated thread
        res = []
        err = []
        def target():
            try:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                res.append(new_loop.run_until_complete(coro))
            except Exception as e:
                err.append(e)
            finally:
                new_loop.close()
        t = threading.Thread(target=target)
        t.start()
        t.join()
        if err:
            raise err[0]
        return res[0]
    else:
        return loop.run_until_complete(coro)

async def _call_tool_async(tool_name: str, arguments: dict) -> str:
    """Helper that establishes SSE connection, initializes session, and calls tool."""
    async with sse_client(MCP_SERVER_SSE_URL) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            # Extract combined text content from result
            text_contents = []
            for content in result.content:
                if hasattr(content, "text") and content.text:
                    text_contents.append(content.text)
            return "\n".join(text_contents)

def call_mcp_tool(tool_name: str, arguments: dict) -> str:
    """Synchronous entrypoint to execute an MCP tool over SSE network transport.
    If the network server is offline, it automatically falls back to direct local Python function execution
    to keep the app plug-and-play without requiring a separate running server process.
    """
    t0 = time.time()
    try:
        response_text = run_async_safe(_call_tool_async(tool_name, arguments))
        latency_ms = int((time.time() - t0) * 1000)
        log_mcp_call(tool=tool_name, latency_ms=latency_ms, status="ok")
        return response_text
    except Exception as network_error:
        # Safe Fallback: Execute the tool function locally from the mcp_server module
        try:
            import mcp_server
            local_func = getattr(mcp_server, tool_name, None)
            if local_func:
                # Convert keys if needed (FastMCP uses standard Python args)
                response_text = local_func(**arguments)
                latency_ms = int((time.time() - t0) * 1000)
                log_mcp_call(tool=tool_name + "_local_fallback", latency_ms=latency_ms, status="ok")
                return response_text
            else:
                raise AttributeError(f"Tool function '{tool_name}' not found in mcp_server.py")
        except Exception as local_error:
            # If both fail, log the original network error and raise
            latency_ms = int((time.time() - t0) * 1000)
            log_mcp_call(tool=tool_name, latency_ms=latency_ms, status="error", error=str(network_error))
            raise network_error
