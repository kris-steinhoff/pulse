"""Local apfel server lifecycle and OpenAI-compatible client helpers."""

from __future__ import annotations

import asyncio
import socket
import subprocess
import time
from contextlib import suppress

import httpx


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class ApfelServer:
    """Manage a local `apfel --serve` subprocess and talk to it over HTTP."""

    def __init__(self, host: str = "127.0.0.1") -> None:
        self.host = host
        self.port = _free_port()
        self.model = "default"
        self._proc: subprocess.Popen[bytes] | None = None
        self._ready = False

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}/v1"

    def start(self) -> None:
        if self._proc is not None:
            return
        self._proc = subprocess.Popen(
            [
                "apfel",
                "--serve",
                "--host",
                self.host,
                "--port",
                str(self.port),
                "--quiet",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def stop(self) -> None:
        proc = self._proc
        if proc is None:
            return
        self._proc = None
        with suppress(ProcessLookupError):
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()

    async def wait_ready(self, timeout: float = 15.0) -> bool:
        if self._ready:
            return True
        deadline = time.monotonic() + timeout
        async with httpx.AsyncClient(timeout=2.0) as client:
            while time.monotonic() < deadline:
                try:
                    res = await client.get(f"{self.base_url}/models")
                    if res.status_code == 200:
                        data = res.json().get("data", [])
                        if data:
                            self.model = data[0].get("id", self.model)
                        self._ready = True
                        return True
                except (httpx.HTTPError, OSError):
                    pass
                await asyncio.sleep(0.3)
        return False

    async def summarize(self, snapshot_text: str, timeout: float = 60.0) -> str:
        if not await self.wait_ready():
            raise RuntimeError("apfel server did not become ready in time")
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        """
You are a news editor. Write a summary of the news.

Include two Sections (3 - 5 sentences each):
    - "The Last 24 Hours"
    - "The Last Week"
                    """
                    ),
                },
                {"role": "user", "content": snapshot_text},
            ],
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            res = await client.post(f"{self.base_url}/chat/completions", json=payload)
            res.raise_for_status()
            data = res.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"unexpected response: {data!r}") from exc
        return (content or "").strip() or "(empty response)"
