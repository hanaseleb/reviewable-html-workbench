"""目次の入れ子が heading_level 2/3/4 の階層をそのまま写すことを確かめる。

何が壊れたらこの test が落ちるか: 目次の <ol>/<li> の入れ子が崩れると、
節や項が別の章の下にぶら下がって表示され、読み手が文書の構造を辿れなくなる。
"""

import unittest
from xml.etree import ElementTree as ET

from scripts.html_review_workbench.render import _render_toc


def _outline(html: str) -> list[tuple[int, str]]:
    """目次 HTML を (深さ, 見出し文字列) の並びへ潰す。閉じ忘れがあれば例外になる。"""
    acc: list[tuple[int, str]] = []

    def walk(ol: ET.Element, depth: int) -> None:
        for li in ol.findall("li"):
            anchor = li.find("a")
            acc.append((depth, anchor.text if anchor is not None else ""))
            for nested in li.findall("ol"):
                walk(nested, depth + 1)

    walk(ET.fromstring(html), 0)
    return acc


def _block(block_id: str, title: str, level: int) -> dict:
    return {"id": block_id, "title": title, "heading_level": level}


class RenderTocLevelsTest(unittest.TestCase):
    def test_three_levels_nest_by_heading_level(self) -> None:
        blocks = [
            _block("a", "前提", 2),
            _block("b", "前提の節", 3),
            _block("c", "論点 1", 2),
            _block("d", "論点 1-a", 3),
            _block("e", "項 1", 4),
            _block("f", "項 2", 4),
            _block("g", "論点 1-b", 3),
            _block("h", "項 3", 4),
            _block("i", "出典", 2),
        ]
        self.assertEqual(
            _outline(_render_toc(blocks)),
            [
                (0, "前提"),
                (1, "前提の節"),
                (0, "論点 1"),
                (1, "論点 1-a"),
                (2, "項 1"),
                (2, "項 2"),
                (1, "論点 1-b"),
                (2, "項 3"),
                (0, "出典"),
            ],
        )

    def test_two_level_document_is_unchanged(self) -> None:
        """既存文書 (h2/h3 だけ) の見え方を変えていないこと。"""
        blocks = [
            _block("a", "章 1", 2),
            _block("b", "節 1", 3),
            _block("c", "節 2", 3),
            _block("d", "章 2", 2),
        ]
        self.assertEqual(
            _outline(_render_toc(blocks)),
            [(0, "章 1"), (1, "節 1"), (1, "節 2"), (0, "章 2")],
        )

    def test_level_jump_without_parent_gets_placeholder(self) -> None:
        """章の見出しが無いまま項が来ても、入れ子は壊れない。"""
        blocks = [
            _block("a", "章 1", 2),
            _block("b", "項だけ", 4),
            _block("c", "章 2", 2),
        ]
        outline = _outline(_render_toc(blocks))
        self.assertIn((2, "項だけ"), outline)
        self.assertEqual(outline[0], (0, "章 1"))
        self.assertEqual(outline[-1], (0, "章 2"))

    def test_blocks_without_title_are_skipped(self) -> None:
        blocks = [
            _block("a", "章 1", 2),
            {"id": "b", "title": "", "heading_level": 3},
            _block("c", "節 1", 3),
        ]
        self.assertEqual(_outline(_render_toc(blocks)), [(0, "章 1"), (1, "節 1")])


if __name__ == "__main__":
    unittest.main()
