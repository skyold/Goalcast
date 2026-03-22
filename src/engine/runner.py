import asyncio
from typing import Optional, AsyncIterator
import anthropic

from src.utils.logger import logger
from config.settings import settings


class AnalysisRunner:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = settings.CLAUDE_MODEL
        self.max_tokens = settings.CLAUDE_MAX_TOKENS
        self.timeout = settings.CLAUDE_TIMEOUT

    async def run(self, prompt: str) -> Optional[str]:
        if not self.api_key:
            logger.error("Anthropic API key not configured")
            return None

        client = anthropic.AsyncAnthropic(api_key=self.api_key)

        for attempt in range(3):
            try:
                logger.info(f"Calling Claude API (attempt {attempt + 1})")

                response = await asyncio.wait_for(
                    client.messages.create(
                        model=self.model,
                        max_tokens=self.max_tokens,
                        messages=[
                            {
                                "role": "user",
                                "content": prompt,
                            }
                        ],
                    ),
                    timeout=self.timeout,
                )

                content = response.content[0].text
                logger.info(f"Claude API response received, length={len(content)}")
                return content

            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1}")
                if attempt == 2:
                    logger.error("All retry attempts failed due to timeout")
                    return None
                await asyncio.sleep(2**attempt)

            except anthropic.RateLimitError:
                wait_time = 2**attempt * 30
                logger.warning(f"Rate limited, waiting {wait_time}s")
                await asyncio.sleep(wait_time)

            except anthropic.APIError as e:
                logger.error(f"API error: {e}")
                if attempt == 2:
                    return None
                await asyncio.sleep(2**attempt)

        return None

    async def run_streaming(self, prompt: str) -> AsyncIterator[str]:
        if not self.api_key:
            logger.error("Anthropic API key not configured")
            return

        client = anthropic.AsyncAnthropic(api_key=self.api_key)

        try:
            logger.info("Calling Claude API with streaming")

            async with client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            return


class SyncAnalysisRunner:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = settings.CLAUDE_MODEL
        self.max_tokens = settings.CLAUDE_MAX_TOKENS

    def run(self, prompt: str) -> Optional[str]:
        if not self.api_key:
            logger.error("Anthropic API key not configured")
            return None

        client = anthropic.Anthropic(api_key=self.api_key)

        try:
            logger.info("Calling Claude API (sync)")

            response = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            content = response.content[0].text
            logger.info(f"Claude API response received, length={len(content)}")
            return content

        except Exception as e:
            logger.error(f"Sync API error: {e}")
            return None
