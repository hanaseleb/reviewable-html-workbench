---
id: TASK-16
title: コメント本文の引用と強調を表示で解釈する
status: Done
assignee: []
created_date: '2026-08-05 14:42'
updated_date: '2026-08-05 14:54'
labels:
  - 機能追加
  - comment
  - ui
dependencies: []
ordinal: 16000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 決定事項

- コメント本文 (親コメント + 返信) の表示で、> 引用 (入れ子含む)・**強調**・`code` だけを HTML に変換する (2026-08-05 ユーザー依頼: 引用記号が生のまま並び、どこが引用でどこが発言か読み分けられない)
- 外部ライブラリは入れない。escapeHtml を通した後に変換する自前の最小実装とする (bundle 完結方針)
- 保存データ (comments.json) は生テキストのまま。表示だけ変える。編集 textarea も生テキスト
- 見出し・リンク等の完全な Markdown 対応はしない (コメントで実際に使われるのは引用と強調のため)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 agent 返信の > 引用が罫線付きの引用ブロックで表示され、記号が残らない
- [x] #2 **強調** が太字、`code` が等幅で表示される
- [x] #3 本文に HTML を書いても script として解釈されない (escape が変換より先)
- [x] #4 python3 -m unittest discover -s tests 全 pass
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Description の ## 決定事項 に決定内容が記録されている
- [x] #2 Implementation Plan に決定事項を分解した todo がある
- [x] #3 Implementation Notes に検討経緯 (rationale) が記録されている
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
- [x] renderCommentMarkdown / renderInlineMarkdown を review-comments.js に実装
- [x] 親コメント表示と返信表示へ適用
- [x] blockquote / code の CSS を追加
- [x] test 追加 (3 問付き) と mutation 確認
- [x] 実資料の preview で表示確認
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-08-05 実装完了。escape → 変換の順序を固定した自前 renderer (約 40 行)。引用は行頭 > の連続を 1 段むいて再帰することで入れ子に対応。編集用 textarea は生テキストのまま。

検証: (1) node で renderer 単体実行 — 入れ子引用が入れ子 blockquote、**強調**/`code` 変換、<script> は escape されたまま。(2) 実データ (e-presc-innai、引用入り返信 5 件) を headless Chrome で描画 — 返信 25 件中 blockquote 8 個、生の > 残りゼロ、エラーなし。(3) unittest 311 件 OK、平文表示に戻した使い捨て copy で新規 test が落ちることを確認。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
コメント本文の引用・強調・code を表示で解釈する最小 renderer を実装。実データと unit 実行で検証済み
<!-- SECTION:FINAL_SUMMARY:END -->
