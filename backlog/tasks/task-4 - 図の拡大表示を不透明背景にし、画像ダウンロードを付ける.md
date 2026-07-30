---
id: TASK-4
title: 図の拡大表示を不透明背景にし、画像ダウンロードを付ける
status: Done
assignee: []
created_date: '2026-07-30 00:34'
updated_date: '2026-07-30 05:07'
labels: []
dependencies: []
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 決定事項

- .diagram-zoom-overlay の background を rgba(0,0,0,.85) から不透明 (--surface-dark) へ差し替える。--overlay-strong の定義自体は変えない
- diagram-zoom.js の zoom-toolbar にダウンロードボタンを追加する。SVG を XMLSerializer で直列化し canvas 2x で PNG 化して <a download> で保存。foreignObject 起因で PNG 化が失敗する環境では SVG ダウンロードへ fallback
- 外部送信なし。render bundle と publish standalone の両方に効く (既存の inline 化経路)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 拡大表示の背景が不透明で背後の本文が透けない (ブラウザで確認済み)
- [x] #2 ダウンロードボタンで PNG が保存される。失敗時は SVG fallback が働く
- [x] #3 publish standalone でも拡大とダウンロードが動く
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Description の ## 決定事項 に決定内容が記録されている
- [x] #2 Implementation Plan に決定事項を分解した todo がある
- [x] #3 Implementation Notes に検討経緯 (rationale) が記録されている
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. style.css の .diagram-zoom-overlay background を --surface-dark へ
2. diagram-zoom.js toolbar にダウンロードボタン + PNG 化 + SVG fallback
3. 動作確認 (render bundle / publish standalone) → ユーザー確認
4. version 1.21.0 で commit (TASK-3 と同一 commit)
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 検討経緯

**背景の不透明化**: .diagram-zoom-overlay の background が --overlay-strong (rgba(0,0,0,.85)) で 15% 透けていた。--overlay-strong の定義自体は他用途で使われる可能性があるため変えず、拡大 overlay のセレクタだけ既存の不透明トークン --surface-dark へ差し替えた。

**PNG 化の方式**: mermaid.min.js を読み、getEffectiveHtmlLabels が ya(e.htmlLabels ?? e.flowchart?.htmlLabels ?? !0) で既定 true と確認した。つまり flowchart のラベルは foreignObject の HTML として描かれ、data URI 経由で canvas に描くと中身が落ちて文字なし PNG になる (無言の失敗)。PNG 化の前に foreignObject を同じ位置・行構成の SVG text/tspan へ平坦化する処理を入れ、平坦化しきれない foreignObject が残った場合は PNG を作らず SVG へ落とす二重の安全網にした。

**ラベル背景の復元 (verifier 指摘で修正)**: text だけへ置換した結果、Mermaid が edge ラベルに付けていた背景色が失われ、保存 PNG で矢印線が「style 注入」等の文字を横切っていた (verifier が Chromium 実測で発見)。resolveLabelBackground() を追加し、元 SVG の foreignObject 内側から祖先を最大 4 階層遡って最初の不透明 backgroundColor を採り、見つかれば text の直前に同位置・同サイズの rect を挿入する形にした。透明のまま (ノードラベルは親 shape が既に塗られている) なら矩形を作らない。

**背景色の取得**: overlay の getComputedStyle().backgroundColor を使うが、overlay が閉じている / CSS 変数が未解決の場合に透明 PNG を作らないよう既定値 (#1c1f24) へ倒す分岐を入れた。

**残した注記 (非 blocking)**: 背景矩形の幅が foreignObject の width 由来のため、中央揃えした文字が数 px はみ出る箇所がある (「palette 破壊を検出」の右端)。可読性は保たれているので今回は直さない。将来ラベルが極端に長い図で読みにくくなったら、text の getBBox から矩形幅を決める形へ変える。

**検証**: verifier が Chromium 実測で foreignObject 13→0、edge ラベルの背景矩形 0→4、node ラベル側 7→7 を確認。drawImage 強制失敗時の SVG fallback、standalone publish での PNG 保存も確認済み。Playwright 5 passed。Safari は WebKit binary 不在で未確認。
<!-- SECTION:NOTES:END -->
