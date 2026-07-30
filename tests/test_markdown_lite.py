from __future__ import annotations

from html.parser import HTMLParser
import unittest

from scripts.html_review_workbench.markdown_lite import (
    normalize_heading_text,
    split_sections,
    to_html,
)


class MarkdownLiteTest(unittest.TestCase):
    def test_split_sections_uses_leading_h1_as_document_title_and_h2_sections(self) -> None:
        title, sections = split_sections("# Plan Title\n\nIntro\n\n## One\nBody\n\n## Two\nMore")

        self.assertEqual(title, "Plan Title")
        self.assertEqual(len(sections), 3)
        self.assertTrue(sections[0].is_preamble)
        self.assertEqual(sections[0].body, "Intro")
        self.assertEqual([section.heading_text for section in sections[1:]], ["One", "Two"])

    def test_split_sections_ignores_headings_inside_fenced_code(self) -> None:
        title, sections = split_sections(
            "\n".join(
                [
                    "# Plan",
                    "",
                    "## Real",
                    "```md",
                    "## Not a section",
                    "```",
                    "",
                    "## Next",
                    "body",
                ]
            )
        )

        self.assertEqual(title, "Plan")
        self.assertEqual([section.heading_text for section in sections], ["Real", "Next"])
        self.assertIn("## Not a section", sections[0].body)

    def test_split_sections_returns_single_preamble_when_no_headings(self) -> None:
        title, sections = split_sections("plain text only")

        self.assertEqual(title, "")
        self.assertEqual(len(sections), 1)
        self.assertTrue(sections[0].is_preamble)
        self.assertEqual(sections[0].body, "plain text only")

    def test_normalize_heading_text_strips_atx_and_inline_markdown(self) -> None:
        self.assertEqual(normalize_heading_text("## `CLI` **Plan** [link](https://example.com) ##"), "CLI Plan link")

    def test_to_html_renders_lists_nested_checkboxes_code_table_quote_and_inline(self) -> None:
        html = to_html(
            "\n".join(
                [
                    "### Detail",
                    "",
                    "- parent",
                    "  - [x] child",
                    "1. first",
                    "",
                    "```python",
                    "print('<safe>')",
                    "```",
                    "",
                    "| A | B |",
                    "| --- | --- |",
                    "| `x` | **y** |",
                    "",
                    "> quoted *text*",
                    "",
                    "Text with `code`, **bold**, *italic*, and [ok](mailto:a@example.com).",
                ]
            )
        )

        self.assertIn("<h3>Detail</h3>", html)
        self.assertIn("<ul>", html)
        self.assertIn('<input type="checkbox" disabled checked>', html)
        self.assertIn('<code class="language-python">print(&#x27;&lt;safe&gt;&#x27;)</code>', html)
        self.assertIn("<table>", html)
        self.assertIn("<blockquote>", html)
        self.assertIn("<code>code</code>", html)
        self.assertIn("<strong>bold</strong>", html)
        self.assertIn("<em>italic</em>", html)
        self.assertIn('href="mailto:a@example.com"', html)

    def test_to_html_escapes_raw_html_and_disallows_javascript_links(self) -> None:
        html = to_html("<script>alert(1)</script>\n\n[bad](javascript:alert(1))")

        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertNotIn('href="javascript:alert(1)"', html)
        self.assertIn("bad (javascript:alert(1))", html)

    def test_to_html_allows_relative_http_https_and_mailto_links(self) -> None:
        html = to_html("[rel](docs/a.md) [http](http://example.com) [https](https://example.com) [mail](mailto:a@example.com)")

        self.assertIn('href="docs/a.md"', html)
        self.assertIn('href="http://example.com"', html)
        self.assertIn('href="https://example.com"', html)
        self.assertIn('href="mailto:a@example.com"', html)

    def test_to_html_disallows_links_with_quotes_spaces_angles_and_controls(self) -> None:
        cases = {
            "quote": '[q](https://example.com/" onclick="alert(1))',
            "space": "[q](https://example.com/ onerror=x)",
            "angle": "[q](https://example.com/<x>)",
            "control": "[q](https://example.com/\x00)",
        }

        for name, markdown in cases.items():
            with self.subTest(name=name):
                html = to_html(markdown)
                self.assertEqual(_AnchorCollector.collect(html), [])
                self.assertIn("q (https://example.com/", html)


class _AnchorCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    @classmethod
    def collect(cls, html: str) -> list[str]:
        parser = cls()
        parser.feed(html)
        return parser.hrefs

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        for name, value in attrs:
            if name == "href" and value is not None:
                self.hrefs.append(value)


if __name__ == "__main__":
    unittest.main()
