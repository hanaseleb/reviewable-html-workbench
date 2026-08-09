---
id: TASK-22
title: deck の幅制限を外し本文と同じ折り返しにする
status: In Progress
assignee: []
created_date: '2026-08-09 00:17'
updated_date: '2026-08-09 00:17'
labels:
  - bug
  - renderer
  - preview-ui
dependencies: []
ordinal: 22000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 決定事項

- doc-deck (冒頭要約段落) の max-width: 60ch を削除し、本文と同じ幅で折り返す (2026-08-06 ユーザー報告: 冒頭段落だけ変な位置で改行される。60ch は日本語では約 30 全角文字で、広い画面に対して不自然に狭い)
- 公開版だけ幅制限を解除していた重複規則 (.is-published .doc-deck { max-width: none }) も不要になるため削除
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 preview で deck が本文と同じ右端まで折り返す (screenshot 実測)
- [ ] #2 unittest 全件 pass
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Description の ## 決定事項 に決定内容が記録されている
- [ ] #2 Implementation Plan に決定事項を分解した todo がある
- [ ] #3 Implementation Notes に検討経緯 (rationale) が記録されている
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
- [x] style.css: .doc-deck の max-width: 60ch を削除
- [x] style.css: .is-published .doc-deck の解除規則を削除
- [x] 閲覧中 bundle 2 つへ配布し screenshot + ユーザー実機確認
- [x] version bump (patch。現行 1.28.3 → 1.28.4。plan 起草時の 1.28.2 は TASK-21 の commit で既に消費済み)
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-08-06〜09: 修正・配布・実測済み。headless screenshot で deck が本文と同幅で折り返すことを確認し、ユーザー実機確認 ok (2026-08-09)。unittest 314 件 OK。
<!-- SECTION:NOTES:END -->
