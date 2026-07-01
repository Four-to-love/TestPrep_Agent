import logging
import json

logger = logging.getLogger("testprep.telemetry")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False

def log_llm_call(agent: str, prompt_chars: int, response_chars: int, latency_ms: int, status: str):
    """Logs a structured JSON record tracking LLM model call parameters and performance."""
    logger.info(json.dumps({
        "event": "llm_call",
        "agent": agent,
        "prompt_chars": prompt_chars,
        "estimated_prompt_tokens": prompt_chars // 4,
        "response_chars": response_chars,
        "estimated_response_tokens": response_chars // 4,
        "latency_ms": latency_ms,
        "status": status
    }))

def log_mcp_call(tool: str, latency_ms: int, status: str, error: str = None):
    """Logs a structured JSON record tracking MCP tool invocation, latency, and status."""
    logger.info(json.dumps({
        "event": "mcp_call",
        "tool": tool,
        "latency_ms": latency_ms,
        "status": status,
        "error": error[:100] if error else None
    }))
