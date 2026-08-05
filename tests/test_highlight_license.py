"""同梱 highlight.min.js の BSD-3-Clause が公式 LICENSE 原文と一致するかの検査。

何が壊れたらこの test は落ちるか (利用者に起きる不都合):
  配布物に載る license 条文が原文と違い、「license 条件を満たした再配布」にならない。
  条文が 1 語だけ改変されても CI が緑のまま通ると、ユーザーの OSS 利用要求が静かに破られる。
判定基準の出所:
  期待値は tests/fixtures/highlightjs-LICENSE.txt (公式 LICENSE 原文の repo 管理元)。
  取得元: https://raw.githubusercontent.com/highlightjs/highlight.js/main/LICENSE
  (fixture 冒頭 comment に URL と取得日。条文本体は 1 文字も変えない)。
落ちるのを見た記録:
  - 修正前の同梱文は REGENTS / name of highlight.js に改変されており FAIL (NG-2)。
  - 3 巡目: 全文一致 test が tmp/ を探し無ければ skip し、使い捨て copy で must→should 改変しても
    suite exit 0 になることを verifier が実測。skip を廃し fixture 固定に直す。
"""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from scripts.html_review_workbench.publish import publish_bundle
from scripts.html_review_workbench.render import render_bundle


ROOT = Path(__file__).resolve().parents[1]
HLJS_PATH = ROOT / "templates" / "assets" / "highlight.min.js"
# clean checkout / CI でも必ず存在する管理元 (tmp/ は参照しない、skip しない)
LICENSE_FIXTURE = ROOT / "tests" / "fixtures" / "highlightjs-LICENSE.txt"

# 配布物に残ってはいけない旧改変表記 (test 内定数としては残してよい)
_FORBIDDEN_IN_DISTRIBUTION = (
    "THE REGENTS AND CONTRIBUTORS",
    "Neither the name of highlight.js nor the names of its contributors",
)


def _license_body_from_fixture(text: str) -> str:
    """fixture から条文本体だけを切り出す (冒頭の取得元 comment を除く)。"""
    idx = text.find("BSD 3-Clause License")
    if idx < 0:
        raise AssertionError(
            "license fixture must contain 'BSD 3-Clause License' body"
        )
    return text[idx:].strip()


def _license_body_from_vendored_header(text: str) -> str:
    """vendored file 先頭 /*! */ から公式 LICENSE 本文相当を取り出す。"""
    start = text.index("/*!")
    end = text.index("*/", start) + 2
    header = text[start:end]
    body_lines: list[str] = []
    for line in header.splitlines():
        if line.startswith(" * "):
            body_lines.append(line[3:])
        elif line == " *":
            body_lines.append("")
    joined = "\n".join(body_lines)
    idx = joined.find("BSD 3-Clause License")
    if idx < 0:
        return ""
    return joined[idx:].strip()


class HighlightLicenseVerbatimTest(unittest.TestCase):
    def test_fixture_exists_and_is_not_empty(self) -> None:
        self.assertTrue(
            LICENSE_FIXTURE.is_file(),
            f"license fixture missing: {LICENSE_FIXTURE} "
            "(must be committed; no skip path)",
        )
        self.assertGreater(LICENSE_FIXTURE.stat().st_size, 0)

    def test_vendored_license_body_matches_fixture_verbatim(self) -> None:
        """同梱 file の license 条文が fixture 原文と 1 文字も違わないこと。"""
        official = _license_body_from_fixture(
            LICENSE_FIXTURE.read_text(encoding="utf-8")
        )
        extracted = _license_body_from_vendored_header(
            HLJS_PATH.read_text(encoding="utf-8")
        )
        self.assertEqual(extracted, official)

    def test_vendored_file_rejects_known_rewrites(self) -> None:
        """配布物に旧改変表記が残っていないこと (適用範囲は配布物のみ)。"""
        text = HLJS_PATH.read_text(encoding="utf-8")
        for phrase in _FORBIDDEN_IN_DISTRIBUTION:
            self.assertNotIn(phrase, text, f"forbidden rewritten phrase: {phrase!r}")

    def test_publish_standalone_keeps_official_license_body(self) -> None:
        official = _license_body_from_fixture(
            LICENSE_FIXTURE.read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            model = {
                "schema_version": "1.0",
                "document_id": "license-pub",
                "title": "License publish",
                "generated_at": "2026-08-05T00:00:00Z",
                "summary": "license",
                "metadata": {},
                "blocks": [
                    {
                        "id": "c",
                        "type": "html",
                        "title": "C",
                        "heading_level": 2,
                        "review_required": True,
                        "content": '<pre id="x"><code class="language-python">x=1</code></pre>',
                    }
                ],
            }
            model_path = tmp_path / "m.json"
            model_path.write_text(__import__("json").dumps(model), encoding="utf-8")
            bundle = tmp_path / "b"
            published = tmp_path / "p"
            render_bundle(model_path, bundle)
            result = publish_bundle(bundle, published)
            self.assertEqual(result["status"], "ok")
            content = (published / "index.html").read_text(encoding="utf-8")
            # inline 後も /*! */ コメント行として全文が残る (切り出しは vendored と同じ)
            extracted = _license_body_from_vendored_header(content)
            self.assertEqual(extracted, official)
            for phrase in _FORBIDDEN_IN_DISTRIBUTION:
                self.assertNotIn(phrase, content)
            self.assertIsNone(re.search(r"<script\s+src=", content))


if __name__ == "__main__":
    unittest.main()
