from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from typing import ClassVar
from xml.etree import ElementTree as ET

import httpx
from rich.style import Style
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Label, Static


BADGE_WIDTH = 5


@dataclass(frozen=True)
class RssFeed:
    title: str
    url: str
    short: str | None = None

    @property
    def badge(self) -> str:
        label = self.short or self.title
        return label[:BADGE_WIDTH]


@dataclass(frozen=True)
class RssItem:
    title: str
    link: str
    summary: str
    feed_title: str
    feed_badge: str
    published: datetime | None = None


class RssWidget(Static):
    """A reusable RSS feed widget that aggregates one or more feeds.

    Items from all feeds are merged and sorted by publication date when
    available. Each item shows a tag indicating its source feed, and the
    title is rendered as a clickable terminal hyperlink.
    """

    DEFAULT_CSS = """
    RssWidget {
        height: 1fr;
    }
    RssWidget #rss-title {
        text-style: bold;
        color: $accent;
    }
    RssWidget #rss-items {
        height: 1fr;
        scrollbar-size-vertical: 1;
    }
    RssWidget .rss-item {
        height: 1;
    }
    """

    ATOM_NS: ClassVar[str] = "{http://www.w3.org/2005/Atom}"

    def __init__(
        self,
        feeds: list[RssFeed],
        max_items: int | None = None,
        *,
        title: str | None = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        if not feeds:
            raise ValueError("RssWidget requires at least one feed")
        self.widget_title = title
        self.feeds = feeds
        self.max_items = max_items
        self._last_items: list[RssItem] = []

    def compose(self) -> ComposeResult:
        if self.widget_title:
            yield Label(self.widget_title, id="rss-title")
        yield VerticalScroll(id="rss-items")

    def on_mount(self) -> None:
        self.fetch_feeds()

    def refresh_data(self) -> None:
        self.fetch_feeds()

    @work(exclusive=True)
    async def fetch_feeds(self) -> None:
        container = self.query_one("#rss-items", VerticalScroll)
        await container.remove_children()
        headers = {"User-Agent": "PulseDashboard/1.0"}

        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            results = await asyncio.gather(
                *(self._fetch_one(client, feed, headers) for feed in self.feeds),
                return_exceptions=True,
            )

        items: list[RssItem] = []
        for feed, result in zip(self.feeds, results):
            if isinstance(result, Exception):
                await container.mount(
                    Static(
                        Text(f"[{feed.title}] failed: {result}", style="bold red"),
                        classes="rss-item",
                    )
                )
                continue
            items.extend(result)

        if not items:
            await container.mount(Static(Text("No items found.", style="dim")))
            return

        items.sort(key=_sort_key, reverse=True)

        shown = items if self.max_items is None else items[: self.max_items]
        self._last_items = shown
        for item in shown:
            await container.mount(_RssItemView(item))

    def snapshot(self) -> str:
        title = self.widget_title or "News"
        if not self._last_items:
            return f"## {title}\n(no data)"
        lines = [f"## {title}"]
        for item in self._last_items[:25]:
            when = (
                item.published.strftime("%Y-%m-%d %H:%M")
                if item.published is not None
                else "n/a"
            )
            badge = (item.feed_badge or "").strip() or item.feed_title
            lines.append(f"- [{badge}] {item.title} ({when})")
            if item.summary:
                lines.append(f"  {item.summary}")
        return "\n".join(lines)

    async def _fetch_one(
        self,
        client: httpx.AsyncClient,
        feed: RssFeed,
        headers: dict[str, str],
    ) -> list[RssItem]:
        res = await client.get(feed.url, headers=headers)
        res.raise_for_status()
        return self._parse(res.content, feed.title, feed.badge)

    def _parse(self, content: bytes, feed_title: str, feed_badge: str) -> list[RssItem]:
        root = ET.fromstring(content)
        items: list[RssItem] = []

        # RSS 2.0: <rss><channel><item>...
        for node in root.iter("item"):
            items.append(
                RssItem(
                    title=_text(node.findtext("title")),
                    link=_text(node.findtext("link")),
                    summary=_clean(node.findtext("description")),
                    feed_title=feed_title,
                    feed_badge=feed_badge,
                    published=_parse_date(node.findtext("pubDate")),
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
            published = node.findtext(f"{self.ATOM_NS}published") or node.findtext(
                f"{self.ATOM_NS}updated"
            )
            items.append(
                RssItem(
                    title=_text(node.findtext(f"{self.ATOM_NS}title")),
                    link=link,
                    summary=_clean(summary),
                    feed_title=feed_title,
                    feed_badge=feed_badge,
                    published=_parse_date(published),
                )
            )

        return items


class _RssItemView(Static):
    def __init__(self, item: RssItem) -> None:
        super().__init__(classes="rss-item")
        self._item = item

    def on_mount(self) -> None:
        self._render_for_width(self.size.width or 80)

    def on_resize(self) -> None:
        self._render_for_width(self.size.width)

    def on_mouse_move(self, event) -> None:
        width = self.size.width
        if width and event.x >= width - BADGE_WIDTH:
            self.tooltip = self._item.feed_title
        else:
            self.tooltip = None

    def _render_for_width(self, width: int) -> None:
        self.update(_render(self._item, width))


def _render(item: RssItem, width: int) -> Text:
    if width <= 0:
        width = 80

    sep = " "
    badge_gap = 2
    title = item.title
    summary = item.summary
    badge = (item.feed_badge or "").rjust(BADGE_WIDTH)
    badge_block = badge_gap + BADGE_WIDTH

    title_len = len(title)
    sum_block = len(sep) + len(summary) if summary else 0
    total = title_len + sum_block + badge_block

    if total > width:
        avail = width - title_len - badge_block - len(sep)
        if summary and avail >= 2:
            summary = summary[: avail - 1].rstrip() + "…"
        else:
            summary = ""
            if title_len + badge_block > width:
                title = title[: max(0, width - badge_block - 1)].rstrip() + "…"

    text = Text(no_wrap=True, overflow="ellipsis")
    if item.link:
        text.append(title, style=Style(link=item.link))
    else:
        text.append(title)
    if summary:
        text.append(sep)
        text.append(summary, style="dim")
    used = len(title) + (len(sep) + len(summary) if summary else 0) + BADGE_WIDTH
    pad = max(badge_gap, width - used)
    text.append(" " * pad)
    text.append(badge, style="cyan")
    return text


def _sort_key(item: RssItem) -> datetime:
    if item.published is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if item.published.tzinfo is None:
        return item.published.replace(tzinfo=timezone.utc)
    return item.published


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    try:
        dt = parsedate_to_datetime(value)
        if dt is not None:
            return dt
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


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
