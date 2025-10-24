"""Tests for document normalizer.

Tests HTML-to-Markdown conversion and boilerplate removal.
Following TDD methodology (RED-GREEN-REFACTOR).
"""



class TestNormalizer:
    """Tests for the Normalizer class."""

    def test_normalizer_converts_html_to_markdown(self) -> None:
        """Test that Normalizer converts HTML to Markdown."""
        from packages.ingest.normalizer import Normalizer

        html = "<h1>Title</h1><p>This is a paragraph.</p>"
        normalizer = Normalizer()
        markdown = normalizer.normalize(html)

        assert "# Title" in markdown or "Title" in markdown
        assert "This is a paragraph" in markdown
        assert "<h1>" not in markdown
        assert "<p>" not in markdown

    def test_normalizer_removes_boilerplate(self) -> None:
        """Test that Normalizer removes common boilerplate content."""
        from packages.ingest.normalizer import Normalizer

        html = """
        <html>
        <head><title>Page Title</title></head>
        <body>
            <nav>Navigation menu</nav>
            <header>Site Header</header>
            <main>
                <article>
                    <h1>Article Title</h1>
                    <p>This is the main content we want to keep.</p>
                </article>
            </main>
            <aside>Sidebar ads</aside>
            <footer>Copyright 2024</footer>
        </body>
        </html>
        """
        normalizer = Normalizer()
        markdown = normalizer.normalize(html)

        # Main content should be preserved
        assert "main content we want to keep" in markdown.lower()

        # Boilerplate should be removed or minimal
        assert len(markdown) < len(html)

    def test_normalizer_handles_empty_html(self) -> None:
        """Test that Normalizer handles empty HTML gracefully."""
        from packages.ingest.normalizer import Normalizer

        normalizer = Normalizer()
        markdown = normalizer.normalize("")

        assert markdown == ""

    def test_normalizer_handles_plain_text(self) -> None:
        """Test that Normalizer handles plain text without HTML tags."""
        from packages.ingest.normalizer import Normalizer

        text = "This is plain text without any HTML."
        normalizer = Normalizer()
        markdown = normalizer.normalize(text)

        assert "This is plain text without any HTML" in markdown

    def test_normalizer_preserves_code_blocks(self) -> None:
        """Test that Normalizer preserves code blocks."""
        from packages.ingest.normalizer import Normalizer

        html = """
        <h1>Code Example</h1>
        <pre><code>
        def hello():
            print("Hello, World!")
        </code></pre>
        """
        normalizer = Normalizer()
        markdown = normalizer.normalize(html)

        assert "def hello()" in markdown
        assert 'print("Hello, World!")' in markdown

    def test_normalizer_removes_scripts_and_styles(self) -> None:
        """Test that Normalizer removes script and style tags."""
        from packages.ingest.normalizer import Normalizer

        html = """
        <html>
        <head>
            <style>body { color: red; }</style>
            <script>alert('hello');</script>
        </head>
        <body>
            <p>Content to keep.</p>
            <script>console.log('remove me');</script>
        </body>
        </html>
        """
        normalizer = Normalizer()
        markdown = normalizer.normalize(html)

        assert "Content to keep" in markdown
        assert "alert" not in markdown
        assert "console.log" not in markdown
        assert "color: red" not in markdown

    def test_normalizer_cleans_whitespace(self) -> None:
        """Test that Normalizer cleans excessive whitespace."""
        from packages.ingest.normalizer import Normalizer

        html = "<p>Text   with    multiple     spaces.</p>"
        normalizer = Normalizer()
        markdown = normalizer.normalize(html)

        # Should normalize to single spaces
        assert "Text with multiple spaces" in markdown or "Text   with" not in markdown
