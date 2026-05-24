from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from typing import ClassVar
from xml.etree import ElementTree as ET

import httpx
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Label, Static


@dataclass(frozen=True)
class RssItem:
    title: str
    link: str
    summary: str


class RssPanel(Static):
    """A reusable RSS feed panel.

    Pass a `title`, feed `url`, and optional `max_items` to render any feed.
    """

    DEFAULT_CSS = """
    RssPanel {
        height: 1fr;
    }
    RssPanel #rss-title {
        text-style: bold;
        color: $accent;
    }
    RssPanel #rss-items {
        height: 1fr;
    }
    RssPanel .rss-item {
        margin-bottom: 1;
    }
    """

    ATOM_NS: ClassVar[str] = "{http://www.w3.org/2005/Atom}"

    def __init__(
        self,
        title: str,
        url: str,
        max_items: int = 10,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self.feed_title = title
        self.url = url
        self.max_items = max_items

    def compose(self) -> ComposeResult:
        yield Label(self.feed_title, id="rss-title")
        yield VerticalScroll(id="rss-items")

    def on_mount(self) -> None:
        self.fetch_feed()

    @work(exclusive=True)
    async def fetch_feed(self) -> None:
        container = self.query_one("#rss-items", VerticalScroll)
        headers = {"User-Agent": "PulseDashboard/1.0"}
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
                res = await client.get(self.url, headers=headers)
                res.raise_for_status()
                items = self._parse(res.content)
        except Exception as e:
            await container.mount(
                Static(Text(f"Failed to load feed: {e}", style="bold red"))
            )
            return

        if not items:
            await container.mount(Static(Text("No items found.", style="dim")))
            return

        for item in items[: self.max_items]:
            text = Text()
            text.append(f"• {item.title}\n", style="bold")
            if item.summary:
                text.append(item.summary, style="dim")
            await container.mount(Static(text, classes="rss-item"))

    def _parse(self, content: bytes) -> list[RssItem]:
        root = ET.fromstring(content)
        items: list[RssItem] = []

        # RSS 2.0: <rss><channel><item>...
        for node in root.iter("item"):
            items.append(
                RssItem(
                    title=_text(node.findtext("title")),
                    link=_text(node.findtext("link")),
                    summary=_clean(node.findtext("description")),
                )
            )

        if items:
            return items

        # Atom: <feed><entry>...
        for node in root.iter(f"{self.ATOM_NS}entry"):
            link_el = node.find(f"{self.ATOM_NS}link")
            link = link_el.get("href", "") if link_el is not None else ""
            summary = node.findtext(f"{self.ATOM_NS}summary") or node.findtext(
                f"{self.ATOM_NS}content"
            )
            items.append(
                RssItem(
                    title=_text(node.findtext(f"{self.ATOM_NS}title")),
                    link=link,
                    summary=_clean(summary),
                )
            )

        return items


def _text(value: str | None) -> str:
    return (value or "").strip()


def _clean(value: str | None, max_len: int = 200) -> str:
    if not value:
        return ""
    # Strip tags and collapse whitespace.
    import re

    stripped = re.sub(r"<[^>]+>", "", value)
    stripped = unescape(stripped)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    if len(stripped) > max_len:
        stripped = stripped[: max_len - 1].rstrip() + "…"
    return stripped
