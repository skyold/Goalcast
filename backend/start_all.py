#!/usr/bin/env python3
import asyncio
import subprocess
import sys
import os
import signal
from pathlib import Path

_ROOT = Path(__file__).parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv(_ROOT / ".env")


async def run_main():
    """Run the Goalcast main orchestrator."""
    cmd = [
        sys.executable, "-m", "main", "run",
        "--infinite", "--fetch-interval", "3600"
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(_ROOT),
    )
    return process


async def run_api():
    """Run the FastAPI server."""
    cmd = [
        sys.executable, "-m", "uvicorn",
        "server.server:app",
        "--host", "0.0.0.0",
        "--port", "8000"
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(_ROOT),
    )
    return process


async def main():
    processes = []
    try:
        print("Starting Goalcast API Server...")
        api_proc = await run_api()
        processes.append(api_proc)

        await asyncio.sleep(2)

        print("Starting Goalcast Orchestrator...")
        main_proc = await run_main()
        processes.append(main_proc)

        print("\nAll services started!")
        print("  - API Server: http://0.0.0.0:8000")
        print("  - Orchestrator: Running\n")

        await asyncio.gather(
            *[proc.wait() for proc in processes]
        )
    except asyncio.CancelledError:
        print("\nShutting down services...")
        for proc in processes:
            if proc.returncode is None:
                try:
                    proc.terminate()
                    await proc.wait()
                except Exception:
                    pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
