"""Document normalizer for HTML-to-Markdown conversion.

Implements HTML-to-Markdown conversion and boilerplate removal.
Per research.md: Use readability/justext for boilerplate removal.
"""

import logging
import re
from html.parser import HTMLParser

logger = logging.getLogger(__name__)


class _MarkdownConverter(HTMLParser):
    """HTML to Markdown converter using html.parser."""

    def __init__(self) -> None:
        """Initialize converter."""
        super().__init__()
        self.markdown_parts: list[str] = []
        self.current_text: list[str] = []
        self.in_code = False
        self.in_pre = False
        self.skip_tag = False
        self.heading_level: int | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Handle opening HTML tags."""
        tag = tag.lower()

        # Skip script and style tags
        if tag in ("script", "style", "nav", "footer", "aside"):
            self.skip_tag = True
            return

        if tag == "pre":
            self.in_pre = True
        elif tag == "code":
            self.in_code = True
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.heading_level = int(tag[1])
        elif tag == "br":
            self.current_text.append("\n")
        elif tag == "p":
            if self.current_text and self.current_text[-1] != "\n\n":
                self.current_text.append("\n\n")

    def handle_endtag(self, tag: str) -> None:
        """Handle closing HTML tags."""
        tag = tag.lower()

        if tag in ("script", "style", "nav", "footer", "aside"):
            self.skip_tag = False
            return

        if tag == "pre":
            self.in_pre = False
            self.current_text.append("\n\n")
        elif tag == "code":
            self.in_code = False
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            if self.heading_level:
                # Add markdown heading prefix
                heading_text = "".join(self.current_text).strip()
                self.markdown_parts.append("#" * self.heading_level + " " + heading_text + "\n\n")
                self.current_text = []
                self.heading_level = None
        elif tag == "p":
            text = "".join(self.current_text).strip()
            if text:
                self.markdown_parts.append(text + "\n\n")
                self.current_text = []

    def handle_data(self, data: str) -> None:
        """Handle text data."""
        if self.skip_tag:
            return

        if self.in_code or self.in_pre:
            self.current_text.append(data)
        else:
            # Clean up whitespace for non-code content
            cleaned = re.sub(r"\s+", " ", data)
            if cleaned.strip():
                self.current_text.append(cleaned)

    def get_markdown(self) -> str:
        """Get the converted markdown."""
        # Flush any remaining text
        remaining = "".join(self.current_text).strip()
        if remaining:
            self.markdown_parts.append(remaining)

        markdown = "".join(self.markdown_parts)

        # Clean up excessive blank lines
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)

        return markdown.strip()


class Normalizer:
    """Document normalizer for HTML-to-Markdown conversion.

    Removes boilerplate content and converts HTML to clean Markdown.
    """

    def __init__(self) -> None:
        """Initialize normalizer."""
        logger.info("Initialized Normalizer")

    def normalize(self, html: str) -> str:
        """Normalize HTML document to Markdown.

        Args:
            html: HTML content to normalize.

        Returns:
            str: Normalized Markdown content.
        """
        if not html:
            return ""

        # Convert HTML to Markdown
        converter = _MarkdownConverter()
        try:
            converter.feed(html)
            markdown = converter.get_markdown()
        except Exception as e:
            logger.warning(f"HTML parsing failed, returning cleaned text: {e}")
            # Fallback: strip all tags and clean whitespace
            markdown = re.sub(r"<[^>]+>", " ", html)
            markdown = re.sub(r"\s+", " ", markdown).strip()

        # Additional cleanup
        markdown = self._clean_whitespace(markdown)

        logger.debug(f"Normalized {len(html)} chars HTML to {len(markdown)} chars Markdown")

        return markdown

    def _clean_whitespace(self, text: str) -> str:
        """Clean excessive whitespace from text.

        Args:
            text: Text to clean.

        Returns:
            str: Cleaned text.
        """
        # Remove excessive spaces
        text = re.sub(r" {2,}", " ", text)

        # Remove excessive newlines
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove leading/trailing whitespace from lines
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)

        return text.strip()
