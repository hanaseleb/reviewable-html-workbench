---
id: TASK-20
title: 拡大表示 (zoom overlay) の背景を theme 追従にする
status: In Progress
assignee: []
created_date: '2026-08-06 02:52'
updated_date: '2026-08-06 02:54'
labels:
  - bug
  - renderer
  - preview-ui
dependencies: []
ordinal: 20000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 決定事項

- zoom overlay の背景・文字色を dark 固定 (--surface-dark / --ink-on-overlay) から紙面 theme 追従 (--paper-2 / --ink) へ変更する (2026-08-06 ユーザー報告: light モードで図を最大化すると dark 画像に見える)
- PNG 保存の背景 fallback は「body の地色 → 白」の順にし、dark 固定色 #1c1f24 を廃止する
- ラベル崩れは zoom 起因ではなく mermaid mindmap の CJK ラベル誤採寸 (inline でも崩れることを screenshot で実測)。plugin では直せないため、SKILL の図示指針に「CJK ラベルでは mindmap を使わない」を追記して再発を防ぐ
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 light theme で zoom overlay を開くと背景が紙色 (--paper-2) になり、dark theme では従来どおり dark になる (headless screenshot で確認)
- [ ] #2 PNG 保存の背景が overlay 地色 → body 地色 → 白 の順で解決され、透明背景 PNG を作らない
- [ ] #3 html-design-guidance fragment (ja/en) と両 SKILL.md に mindmap 回避の指針が同期されている
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Description の ## 決定事項 に決定内容が記録されている
- [ ] #2 Implementation Plan に決定事項を分解した todo がある
- [ ] #3 Implementation Notes に検討経緯 (rationale) が記録されている
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
- [x] style.css: overlay 背景/文字/toolbar を theme 変数へ
- [x] diagram-zoom.js: PNG fallback を body 地色 → 白へ
- [x] 不要になった overlay 専用 dark 固定変数 4 つを削除
- [x] test_render_diagram_zoom.py の期待値を新実装へ更新
- [x] html-design-guidance (ja/en) へ mindmap 回避を追記し build_skill_docs.py で同期
- [x] version bump (patch 1.28.1 → 1.28.2)
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-08-06 実測と実装:
- 原因切り分け: headless Chrome (CDP 直叩き。--dump-dom はこの環境で SSE 常駐接続により返らないため node WebSocket で CDP を操作) で、zoom なしの inline mindmap が既に崩れていることを screenshot で確認。zoom は崩れの原因ではない。ユーザーの tab は旧版 (mindmap)。現行資料は flowchart へ再生成済みで崩れない。
- 修正後、light (flowchart zoom = 紙色背景) / dark (mindmap zoom = dark 背景) を screenshot で確認。
- 旧実装値を assert していた test 2 件は、変更で実際に落ちたことを確認してから新実装の期待値へ更新 (検知力の実証)。unittest 314 件 OK。
- ユーザー実機確認済み (2026-08-06 "ok")。
<!-- SECTION:NOTES:END -->
