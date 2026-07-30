"""metadata.palette (主題連動 accent) の検証と style 生成。

上書きできるのは brand / brand_soft の 2 トークンだけ。中立色・地色・
レビュー状態色は固定のまま。色選択の失敗が読みにくさへ直結するため、
WCAG 2.x のコントラスト比を check-model / render / validate の各段で
機械検査し、不足は error で止める。
"""

from __future__ import annotations

import re
from typing import Any

HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
MIN_CONTRAST_RATIO = 4.5

# style.css の既定値。palette 検査の相手側 (地色・文字色) はここに固定する。
#
# brand が文字・線として載る地色は 1 つではない。style.css では
#   .prose a / .eyebrow / .summary-h  → --paper
#   .toc li a.current の border      → --bg-app / --bg-rail
#   table.cmp tbody tr:hover td.axis → --paper-2
# と 3 種類あるため、最もコントラストが低くなる地色で判定する。
#
# brand が「背景」になる箇所 (.btn.primary の白文字など) は検査に含めない。
# --brand は文字色・線色・背景色の 3 役を兼ねており、背景側の白文字比まで縛ると
# 文字として十分濃い色が背景としては弾かれる (逆も同じ) というジレンマになる。
# style.css の既定値はこれを文字色側へ寄せて解決しており (light 白文字比 6.53 /
# dark 2.62)、palette もその方針を継承する。既定 dark が 3:1 すら満たさないため、
# ここで基準を課すと既定と同系統の色が指定できなくなる。
THEME_BASE = {
    "light": {
        "grounds": {"paper": "#fdfcf9", "bg-app": "#efece5", "paper-2": "#f7f5f0"},
        "ink": "#232019",
    },
    "dark": {
        "grounds": {"paper": "#1c1f24", "bg-app": "#131519", "paper-2": "#20242a"},
        "ink": "#e7e3da",
    },
}
_ALLOWED_THEMES = ("light", "dark")
_ALLOWED_TOKENS = ("brand", "brand_soft")


def extract_palette(metadata: Any) -> dict[str, dict[str, str]]:
    """metadata から palette 指定を取り出す。未指定なら空 dict。"""
    if not isinstance(metadata, dict):
        return {}
    palette = metadata.get("palette")
    if not isinstance(palette, dict):
        return {}
    return palette


def validate_palette(metadata: Any) -> list[str]:
    """palette の形式とコントラスト比を検査し、error 文字列の一覧を返す。"""
    errors: list[str] = []
    if isinstance(metadata, dict) and "palette" in metadata and not isinstance(metadata["palette"], dict):
        return ["metadata.palette must be an object with light/dark themes"]

    palette = extract_palette(metadata)
    for theme_name, theme in palette.items():
        if theme_name not in _ALLOWED_THEMES:
            errors.append(f"metadata.palette has unknown theme: {theme_name} (allowed: light, dark)")
            continue
        if not isinstance(theme, dict):
            errors.append(f"metadata.palette.{theme_name} must be an object")
            continue
        for token_name, value in theme.items():
            if token_name not in _ALLOWED_TOKENS:
                errors.append(
                    f"metadata.palette.{theme_name} has unknown token: {token_name} (allowed: brand, brand_soft)"
                )
                continue
            if not isinstance(value, str) or not HEX_COLOR_RE.match(value):
                errors.append(
                    f"metadata.palette.{theme_name}.{token_name} must be a 6-digit hex color (got: {value!r})"
                )
                continue
            errors.extend(_contrast_errors(theme_name, token_name, value))
        errors.extend(_pair_contrast_errors(theme_name, theme))
    return errors


def _contrast_errors(theme_name: str, token_name: str, value: str) -> list[str]:
    base = THEME_BASE[theme_name]
    if token_name == "brand":
        # brand は複数の地色の上で文字・線になる。最悪の地色で判定する
        worst_label, worst_ratio = min(
            ((label, contrast_ratio(value, ground)) for label, ground in base["grounds"].items()),
            key=lambda item: item[1],
        )
        if worst_ratio < MIN_CONTRAST_RATIO:
            ground = base["grounds"][worst_label]
            return [
                f"metadata.palette.{theme_name}.brand {value} has contrast {worst_ratio:.2f} "
                f"against {theme_name} {worst_label} {ground} (must be >= {MIN_CONTRAST_RATIO})"
            ]
        return []

    # brand_soft は背景として使われ、その上に ink が載る
    ink = base["ink"]
    ratio = contrast_ratio(value, ink)
    if ratio < MIN_CONTRAST_RATIO:
        return [
            f"metadata.palette.{theme_name}.brand_soft {value} has contrast {ratio:.2f} "
            f"against {theme_name} ink {ink} (must be >= {MIN_CONTRAST_RATIO})"
        ]
    return []


def _pair_contrast_errors(theme_name: str, theme: Any) -> list[str]:
    """brand と brand_soft を同時に指定した場合、その 2 色の関係も検査する。

    style.css の `#focusToggle[aria-pressed="true"]` が brand_soft 背景に brand 文字を
    載せるため、片方ずつ地色と比べただけでは読めない組み合わせが通ってしまう。
    """
    if not isinstance(theme, dict):
        return []
    brand = theme.get("brand")
    soft = theme.get("brand_soft")
    if not (isinstance(brand, str) and HEX_COLOR_RE.match(brand)):
        return []
    if not (isinstance(soft, str) and HEX_COLOR_RE.match(soft)):
        return []
    ratio = contrast_ratio(brand, soft)
    if ratio < MIN_CONTRAST_RATIO:
        return [
            f"metadata.palette.{theme_name} brand {brand} on brand_soft {soft} has contrast "
            f"{ratio:.2f} (must be >= {MIN_CONTRAST_RATIO}; used by the focus toggle)"
        ]
    return []


def palette_style_block(metadata: Any) -> str:
    """palette 指定から上書き用 <style> を作る。未指定なら空文字。

    report.html.j2 では stylesheet link の直後に置かれ、後勝ちで既定トークンを
    上書きする。検証済みの palette だけを渡すこと (render 側で validate 必須)。
    """
    palette = extract_palette(metadata)
    if not palette:
        return ""

    rules: list[str] = []
    light = palette.get("light")
    if isinstance(light, dict) and light:
        rules.append(":root { " + _declarations(light) + " }")
    dark = palette.get("dark")
    if isinstance(dark, dict) and dark:
        rules.append('[data-theme="dark"] { ' + _declarations(dark) + " }")
    if not rules:
        return ""
    return '<style id="palette-override">\n' + "\n".join(rules) + "\n</style>"


def _declarations(theme: dict[str, Any]) -> str:
    parts = []
    if "brand" in theme:
        parts.append(f"--brand: {theme['brand']};")
    if "brand_soft" in theme:
        parts.append(f"--brand-soft: {theme['brand_soft']};")
    return " ".join(parts)


def relative_luminance(hex_color: str) -> float:
    """WCAG 2.x の相対輝度。https://www.w3.org/TR/WCAG21/#dfn-relative-luminance"""
    value = hex_color.lstrip("#")
    channels = []
    for i in (0, 2, 4):
        c = int(value[i : i + 2], 16) / 255.0
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(color_a: str, color_b: str) -> float:
    """WCAG 2.x のコントラスト比 (1.0〜21.0)。"""
    la = relative_luminance(color_a)
    lb = relative_luminance(color_b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)
