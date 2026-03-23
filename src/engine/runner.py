import asyncio
from typing import Optional, AsyncIterator

from utils.logger import logger
from config.settings import settings


class AnalysisRunner:
    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or settings.LLM_PROVIDER
        self.model = settings.LLM_MODEL
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.timeout = settings.LLM_TIMEOUT

    async def run(self, prompt: str) -> Optional[str]:
        if self.provider == "deepseek":
            return await self._run_deepseek(prompt)
        elif self.provider == "anthropic":
            return await self._run_anthropic(prompt)
        else:
            logger.error(f"Unknown LLM provider: {self.provider}")
            return None

    async def _run_deepseek(self, prompt: str) -> Optional[str]:
        api_key = settings.DEEPSEEK_API_KEY
        base_url = settings.DEEPSEEK_BASE_URL

        if not api_key:
            logger.error("DeepSeek API key not configured")
            return None

        try:
            from openai import AsyncOpenAI
        except ImportError:
            logger.error("openai package not installed. Run: pip install openai")
            return None

        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

        for attempt in range(3):
            try:
                logger.info(f"Calling DeepSeek API (attempt {attempt + 1})")

                response = await asyncio.wait_for(
                    client.chat.completions.create(
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

                content = response.choices[0].message.content
                logger.info(f"DeepSeek API response received, length={len(content)}")
                return content

            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1}")
                if attempt == 2:
                    logger.error("All retry attempts failed due to timeout")
                    return None
                await asyncio.sleep(2**attempt)

            except Exception as e:
                logger.error(f"DeepSeek API error: {e}")
                if attempt == 2:
                    return None
                await asyncio.sleep(2**attempt)

        return None

    async def _run_anthropic(self, prompt: str) -> Optional[str]:
        api_key = settings.ANTHROPIC_API_KEY

        if not api_key:
            logger.error("Anthropic API key not configured")
            return None

        try:
            import anthropic
        except ImportError:
            logger.error("anthropic package not installed. Run: pip install anthropic")
            return None

        client = anthropic.AsyncAnthropic(api_key=api_key)

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

            except Exception as e:
                logger.error(f"Anthropic API error: {e}")
                if attempt == 2:
                    return None
                await asyncio.sleep(2**attempt)

        return None

    async def run_streaming(self, prompt: str) -> AsyncIterator[str]:
        if self.provider == "deepseek":
            async for chunk in self._run_deepseek_streaming(prompt):
                yield chunk
        elif self.provider == "anthropic":
            async for chunk in self._run_anthropic_streaming(prompt):
                yield chunk

    async def _run_deepseek_streaming(self, prompt: str) -> AsyncIterator[str]:
        api_key = settings.DEEPSEEK_API_KEY
        base_url = settings.DEEPSEEK_BASE_URL

        if not api_key:
            logger.error("DeepSeek API key not configured")
            return

        try:
            from openai import AsyncOpenAI
        except ImportError:
            return

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        try:
            logger.info("Calling DeepSeek API with streaming")

            stream = await client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"DeepSeek streaming error: {e}")

    async def _run_anthropic_streaming(self, prompt: str) -> AsyncIterator[str]:
        api_key = settings.ANTHROPIC_API_KEY

        if not api_key:
            return

        try:
            import anthropic
        except ImportError:
            return

        client = anthropic.AsyncAnthropic(api_key=api_key)

        try:
            async with client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")


class SyncAnalysisRunner:
    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or settings.LLM_PROVIDER
        self.model = settings.LLM_MODEL
        self.max_tokens = settings.LLM_MAX_TOKENS

    def run(self, prompt: str) -> Optional[str]:
        if self.provider == "deepseek":
            return self._run_deepseek(prompt)
        elif self.provider == "anthropic":
            return self._run_anthropic(prompt)
        return None

    def _run_deepseek(self, prompt: str) -> Optional[str]:
        api_key = settings.DEEPSEEK_API_KEY
        base_url = settings.DEEPSEEK_BASE_URL

        if not api_key:
            logger.error("DeepSeek API key not configured")
            return None

        try:
            from openai import OpenAI
        except ImportError:
            return None

        client = OpenAI(api_key=api_key, base_url=base_url)

        try:
            logger.info("Calling DeepSeek API (sync)")

            response = client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.choices[0].message.content
            logger.info(f"DeepSeek API response received, length={len(content)}")
            return content

        except Exception as e:
            logger.error(f"DeepSeek sync API error: {e}")
            return None

    def _run_anthropic(self, prompt: str) -> Optional[str]:
        api_key = settings.ANTHROPIC_API_KEY

        if not api_key:
            return None

        try:
            import anthropic
        except ImportError:
            return None

        client = anthropic.Anthropic(api_key=api_key)

        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic sync API error: {e}")
            return None
