---
id: TASK-10
title: 目次と見出しを章・節・項の 3 階層に対応させる
status: Done
assignee: []
created_date: '2026-08-05 01:27'
updated_date: '2026-08-05 02:31'
labels:
  - 機能追加
  - preview
  - layout
dependencies: []
ordinal: 10000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
目次と見出しの採番が章と節の 2 階層しか扱えず、項 (heading_level 4) の block が節と同じ深さに並んでいた。3 階層まで扱えるようにする。

## 決定事項

- 目次の入れ子生成 (render.py の _render_toc) を heading_level 2/3/4 に対応させる。従来は h2 と「それ以外」の 2 階層固定だった。
- block の title が項 (h4) のとき、その content 内に書かれた h3/h4 を h5 へ押し下げる (render_blocks.py の _shift_content_headings)。従来は h3 の block だけを対象にしていたため、h4 の block では content 内の見出しが title と同じ大きさで並んでいた。
- 採番する見出しの範囲を common.py の MIN_HEADING_LEVEL = 2 / MAX_HEADING_LEVEL = 4 として定数化する。
- 目次の 3 階層目 (項) の字下げ・文字サイズ・色を style.css に追加する。
- 章をまたいだときに節・項の番号を 1 に戻す修正は TASK-8 で行った (counter-reset ではなく counter-set を使う)。本 task の 3 階層化はその修正と組み合わせて動く。

## 経緯

2026-08-05 に、TASK-8 の受入確認中、作業ツリーへ未 commit の状態で存在することを lead が発見した。lead の作業でも委譲した coder の作業でもなく、mtime は lead の委譲より 12 分前。ユーザーへ確認したところ取り込む方針となった (2026-08-05)。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 項 (h4) を含む文書で目次が章・節・項の 3 階層で出る
- [x] #2 章をまたぐと節番号が 1 に戻り、項の番号が 章.節.項 の形式になる
- [x] #3 h4 の block の content 内に書かれた見出しが title より小さく表示される
- [x] #4 python3 -m unittest discover -s tests が全 pass
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Description の ## 決定事項 に決定内容が記録されている
- [x] #2 Implementation Plan に決定事項を分解した todo がある
- [x] #3 Implementation Notes に検討経緯 (rationale) が記録されている
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
- [x] render.py の _render_toc を heading_level 2/3/4 の入れ子生成へ書き換え
- [x] common.py に MIN_HEADING_LEVEL / MAX_HEADING_LEVEL を追加
- [x] render_blocks.py の _shift_content_headings を h4 の block にも対応
- [x] style.css に目次 3 階層目の見た目を追加
- [x] schemas/document-model.schema.json の heading_level enum を [2,3,4] へ拡張
- [x] skills/visual-html-renderer/SKILL.md に heading_level 4 の使い方を追記
- [x] tests/test_render_toc_levels.py を追加
- [x] 実文書で 3 階層と番号を実測
- [x] TASK-8 と 1 本の commit にまとめる (別 commit へ切り出す当初方針は撤回)
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
実測 (2026-08-05、lead、output/2026-08-02_timely-treatment-notification — 項 (h4) の block を 38 個持つ唯一の文書):

目次の入れ子の深さを HTML から数えた結果、章 11 項目 / 節 16 項目 / 項 38 項目の 3 階層。項の数は document-model.json の heading_level 4 の block 数と一致する。

番号の実測 (Playwright ヘッドレスで見出しを撮影): 2 番目の章の最初の節が 2.1 で、章をまたいで 1 に戻っている。項は 4.1.1 で 章.節.項 の 3 階層。

unittest 292 OK (この変更が入った状態)。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
目次と見出しの採番が章と節の 2 階層しか扱えず、項 (heading_level 4) の block が節と同じ深さに並んでいた問題を解消し、章・節・項の 3 階層に対応させた。項を 38 個含む実文書で、目次が章 11 / 節 16 / 項 38 の 3 階層で入れ子になること、章をまたいだ節番号が 2.1 に戻ること、項の番号が 4.1.1 の形式になることを実測した。schema の heading_level を [2,3,4] へ拡張し、skill 文書にも使い方を追記した。番号のリセットは TASK-8 の counter-set 修正と組み合わせて初めて正しく動くため、当初の別 commit 方針を撤回して TASK-8 と 1 本の commit にまとめた。
<!-- SECTION:FINAL_SUMMARY:END -->
