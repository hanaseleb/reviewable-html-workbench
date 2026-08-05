"""metadata.palette (主題連動 accent) の検証・style 生成・各段ゲートのテスト。"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.html_review_workbench.model_quality import check_model_quality
from scripts.html_review_workbench.palette import (
    contrast_ratio,
    palette_style_block,
    validate_palette,
)
from scripts.html_review_workbench.render import render_bundle
from scripts.html_review_workbench.validate_bundle import validate_bundle


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_MODEL = ROOT / "tests/fixtures/minimal_document_model.json"

# 既定 palette と同値 (style.css の現行値)。検査を通ることが前提条件になる
GOOD_PALETTE = {
    "light": {"brand": "#2f6093", "brand_soft": "#e8eff7"},
    "dark": {"brand": "#6ea4dc", "brand_soft": "#1f2d3c"},
}
# light paper (#fdfcf9) に対しコントラスト不足の淡い色
LOW_CONTRAST_PALETTE = {"light": {"brand": "#dddddd"}}


def _model_with_palette(palette: object) -> dict:
    model = json.loads(FIXTURE_MODEL.read_text(encoding="utf-8"))
    model["metadata"]["palette"] = palette
    # section 型は check-model で error になるため html 型へ置き換える
    model["blocks"][0]["type"] = "html"
    model["blocks"][0]["content"] = "<p>palette fixture</p>"
    return model


class ContrastRatioTest(unittest.TestCase):
    def test_black_on_white_is_max_ratio(self) -> None:
        self.assertAlmostEqual(contrast_ratio("#000000", "#ffffff"), 21.0, places=1)

    def test_same_color_is_min_ratio(self) -> None:
        self.assertAlmostEqual(contrast_ratio("#808080", "#808080"), 1.0, places=3)

    def test_order_does_not_matter(self) -> None:
        self.assertEqual(
            contrast_ratio("#2f6093", "#fdfcf9"),
            contrast_ratio("#fdfcf9", "#2f6093"),
        )


class ValidatePaletteTest(unittest.TestCase):
    def test_missing_palette_is_valid(self) -> None:
        self.assertEqual(validate_palette({}), [])
        self.assertEqual(validate_palette(None), [])
        self.assertEqual(validate_palette({"source": "fixture"}), [])

    def test_current_default_colors_pass(self) -> None:
        self.assertEqual(validate_palette({"palette": GOOD_PALETTE}), [])

    def test_light_only_is_allowed(self) -> None:
        self.assertEqual(validate_palette({"palette": {"light": GOOD_PALETTE["light"]}}), [])

    def test_low_contrast_brand_fails(self) -> None:
        errors = validate_palette({"palette": LOW_CONTRAST_PALETTE})
        self.assertEqual(len(errors), 1)
        self.assertIn("contrast", errors[0])
        # 最も薄い地色 (bg-app #efece5) で判定される
        self.assertIn("light bg-app", errors[0])

    def test_brand_is_judged_against_worst_ground_not_paper(self) -> None:
        """paper だけと比べると通るが bg-app では落ちる色を弾く。

        brand は .prose a (paper 上) / .toc の border (bg-app 上) /
        table.cmp hover (paper-2 上) で使われるため、最悪の地色で判定する。
        """
        # paper (#fdfcf9) 比 5.04 / bg-app (#efece5) 比 4.39 になる色
        borderline = "#6d6d6d"
        self.assertGreaterEqual(contrast_ratio(borderline, "#fdfcf9"), 4.5)
        self.assertLess(contrast_ratio(borderline, "#efece5"), 4.5)
        errors = validate_palette({"palette": {"light": {"brand": borderline}}})
        self.assertEqual(len(errors), 1)
        self.assertIn("bg-app", errors[0])

    def test_brand_on_brand_soft_pair_is_checked(self) -> None:
        """toc/comments トグルは brand_soft 背景に brand 文字を載せるため 2 色の関係も検査する。

        個別には地色・ink と十分なコントラストを持つが、互いに近い色の組み合わせを弾く。
        """
        palette = {"light": {"brand": "#2f6093", "brand_soft": "#7d9dbd"}}
        # 個別検査は両方 pass する
        self.assertEqual(validate_palette({"palette": {"light": {"brand": "#2f6093"}}}), [])
        self.assertEqual(validate_palette({"palette": {"light": {"brand_soft": "#7d9dbd"}}}), [])
        # 組み合わせでは落ちる
        errors = validate_palette({"palette": palette})
        self.assertEqual(len(errors), 1)
        self.assertIn("on brand_soft", errors[0])
        self.assertIn("toc/comments toggles", errors[0])

    def test_brand_as_button_background_is_not_checked(self) -> None:
        """brand 背景の白文字比は検査しない (既定 dark が 2.62 で、課すと既定系統が使えない)。

        代わりに style.css 側で白文字を載せる操作要素を `--control-primary` に分離し、
        palette の上書き対象から外して可読性を固定している
        (test_control_primary_is_separated_from_brand で検証)。
        """
        self.assertLess(contrast_ratio("#ffffff", "#6ea4dc"), 3.0)
        self.assertEqual(validate_palette({"palette": {"dark": {"brand": "#6ea4dc"}}}), [])


class ControlPrimarySeparationTest(unittest.TestCase):
    """白文字を載せる操作要素が palette の上書き対象外であることを検証する。

    verifier 実測の欠陥: dark brand=#ffffff が全検査を通り、Chromium で
    `.pub-exit .pe-btn.primary` の背景・文字がともに白 (比 1.00) になった。
    brand は文字・線用途に限り、操作要素の地色は --control-primary に分ける。
    """

    def setUp(self) -> None:
        self.css = (ROOT / "templates/style.css").read_text(encoding="utf-8")

    def test_control_primary_token_is_defined_for_both_themes(self) -> None:
        self.assertIn("--control-primary: #2f6093;", self.css)
        self.assertIn("--control-primary: #6ea4dc;", self.css)

    def test_no_white_text_sits_on_brand_background(self) -> None:
        offenders = [
            line
            for line in self.css.splitlines()
            if "var(--ink-inverse)" in line and "var(--brand)" in line
        ]
        self.assertEqual(offenders, [], f"white text on --brand background: {offenders}")

    def test_primary_controls_use_control_primary(self) -> None:
        for selector in (".btn.primary", ".pub-exit .pe-btn.primary", ".m-fab", ".agent-avatar"):
            index = self.css.index(selector)
            rule = self.css[index : self.css.index("}", index)]
            self.assertIn("var(--control-primary)", rule, f"{selector} must not use --brand")

    def test_palette_cannot_override_control_primary(self) -> None:
        # palette が出す上書きは --brand / --brand-soft だけ
        style = palette_style_block({"palette": {"dark": {"brand": "#ffffff"}}})
        self.assertIn("--brand:", style)
        self.assertNotIn("--control-primary", style)
        # token 名としても受け付けない
        errors = validate_palette({"palette": {"dark": {"control_primary": "#ffffff"}}})
        self.assertEqual(len(errors), 1)
        self.assertIn("unknown token", errors[0])

    def test_low_contrast_brand_soft_fails_against_ink(self) -> None:
        # dark ink (#e7e3da) に近い明るい背景は ink の文字が読めない
        errors = validate_palette({"palette": {"dark": {"brand_soft": "#d0ccc0"}}})
        self.assertEqual(len(errors), 1)
        self.assertIn("dark ink", errors[0])

    def test_invalid_hex_fails(self) -> None:
        errors = validate_palette({"palette": {"light": {"brand": "blue"}}})
        self.assertEqual(len(errors), 1)
        self.assertIn("6-digit hex", errors[0])

    def test_unknown_theme_and_token_fail(self) -> None:
        errors = validate_palette({"palette": {"sepia": {}, "light": {"paper": "#ffffff"}}})
        self.assertEqual(len(errors), 2)
        self.assertTrue(any("unknown theme" in e for e in errors))
        self.assertTrue(any("unknown token" in e for e in errors))

    def test_non_object_palette_fails(self) -> None:
        errors = validate_palette({"palette": "#2f6093"})
        self.assertEqual(len(errors), 1)


class PaletteStyleBlockTest(unittest.TestCase):
    def test_no_palette_returns_empty(self) -> None:
        self.assertEqual(palette_style_block({}), "")
        self.assertEqual(palette_style_block({"palette": {}}), "")

    def test_light_only_emits_root_rule_only(self) -> None:
        style = palette_style_block({"palette": {"light": {"brand": "#2f6093"}}})
        self.assertIn('<style id="palette-override">', style)
        self.assertIn(":root { --brand: #2f6093; }", style)
        self.assertNotIn("data-theme", style)

    def test_both_themes_emit_both_rules(self) -> None:
        style = palette_style_block({"palette": GOOD_PALETTE})
        self.assertIn(":root { --brand: #2f6093; --brand-soft: #e8eff7; }", style)
        self.assertIn('[data-theme="dark"] { --brand: #6ea4dc; --brand-soft: #1f2d3c; }', style)


class RenderPaletteIntegrationTest(unittest.TestCase):
    def test_render_without_palette_has_no_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            index_path = render_bundle(FIXTURE_MODEL, Path(tmp))
            html = index_path.read_text(encoding="utf-8")
            self.assertNotIn("palette-override", html)
            self.assertNotIn("{{ palette_style }}", html)

    def test_render_with_palette_injects_style_after_stylesheet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "model.json"
            model_path.write_text(
                json.dumps(_model_with_palette(GOOD_PALETTE), ensure_ascii=False), encoding="utf-8"
            )
            output_dir = Path(tmp) / "out"
            index_path = render_bundle(model_path, output_dir)
            html = index_path.read_text(encoding="utf-8")
            self.assertIn('<style id="palette-override">', html)
            # 後勝ちで既定を上書きするため、必ず stylesheet link より後に置く
            self.assertLess(html.index("assets/style.css"), html.index("palette-override"))
            result = validate_bundle(output_dir)
            self.assertTrue(result.ok, result.errors)

    def test_render_with_low_contrast_palette_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "model.json"
            model_path.write_text(
                json.dumps(_model_with_palette(LOW_CONTRAST_PALETTE), ensure_ascii=False),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError) as ctx:
                render_bundle(model_path, Path(tmp) / "out")
            self.assertIn("palette validation failed", str(ctx.exception))


class CheckModelPaletteTest(unittest.TestCase):
    def test_check_model_reports_low_contrast(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "model.json"
            model_path.write_text(
                json.dumps(_model_with_palette(LOW_CONTRAST_PALETTE), ensure_ascii=False),
                encoding="utf-8",
            )
            result = check_model_quality(model_path)
            self.assertFalse(result.ok)
            self.assertTrue(any("contrast" in e for e in result.errors), result.errors)

    def test_check_model_accepts_good_palette(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "model.json"
            model_path.write_text(
                json.dumps(_model_with_palette(GOOD_PALETTE), ensure_ascii=False), encoding="utf-8"
            )
            result = check_model_quality(model_path)
            self.assertTrue(result.ok, result.errors)


class ValidateBundlePaletteTest(unittest.TestCase):
    def test_validate_reports_palette_broken_after_render(self) -> None:
        """render 後にモデル側の palette が壊された場合も validate が検出する。"""
        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "model.json"
            model_path.write_text(
                json.dumps(_model_with_palette(GOOD_PALETTE), ensure_ascii=False), encoding="utf-8"
            )
            output_dir = Path(tmp) / "out"
            render_bundle(model_path, output_dir)
            model_path.write_text(
                json.dumps(_model_with_palette(LOW_CONTRAST_PALETTE), ensure_ascii=False),
                encoding="utf-8",
            )
            result = validate_bundle(output_dir)
            self.assertFalse(result.ok)
            self.assertTrue(any("contrast" in e for e in result.errors), result.errors)


if __name__ == "__main__":
    unittest.main()
