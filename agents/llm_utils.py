import os
import time
import logging
import concurrent.futures
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

# Load environment variables from .env at module import time.
# We set override=True so that local config takes precedence over shell environments.
load_dotenv(override=True)

logger = logging.getLogger("testprep.llm")
LLM_TIMEOUT_SECONDS = 45
MAX_CHAT_TURNS = 20

def _is_retryable(exc: Exception) -> bool:
    """Only retry on rate limits (429) or temporary server errors (500/503/504).
    Fail instantly on 401 UNAUTHENTICATED or 400 BAD REQUEST to prevent freezing the UI.
    """
    msg = str(exc).lower()
    return any(code in msg for code in ["429", "500", "503", "504", "resource_exhausted", "internal", "timeout"])

def _call_raw(client, model: str, contents, config=None):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            client.models.generate_content,
            model=model,
            contents=contents,
            config=config
        )
        try:
            return future.result(timeout=LLM_TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"Gemini API call exceeded {LLM_TIMEOUT_SECONDS}s timeout limit")

@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def call_gemini_with_retry(client, model: str, contents, config=None):
    """Wraps generate_content() with 3-attempt exponential backoff and a 45-second timeout.
    Uses concurrent.futures to ensure thread-safety inside Streamlit.
    """
    return _call_raw(client, model, contents, config)
