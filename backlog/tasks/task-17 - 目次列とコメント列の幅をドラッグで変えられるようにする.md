---
id: TASK-17
title: 目次列とコメント列の幅をドラッグで変えられるようにする
status: Done
assignee: []
created_date: '2026-08-06 00:40'
updated_date: '2026-08-06 01:17'
labels:
  - 機能追加
  - layout
  - ui
dependencies: []
ordinal: 17000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 決定事項

- preview の目次列 (既定 232px) とコメント列 (既定 332px) の境界をドラッグして幅を変えられるようにする (2026-08-06 ユーザー依頼)
- 列幅は CSS 変数 (--toc-w / --rail-w) に一本化し、ドラッグは変数の書き換えだけを行う (grid 構造は変えない)
- clamp: 目次 160〜400px、コメント 240〜560px (本文列が潰れないように)
- 幅は localStorage に保存し次回も同じ幅。ハンドルのダブルクリックで既定幅へリセット
- 対象は preview のみ。公開出力の目次列は固定のまま (同じ変数を使うので後から拡張可能)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 目次列右端・コメント列左端のドラッグで列幅が変わり、本文列が追従する (headless で実測)
- [x] #2 clamp の上下限を超えない
- [x] #3 リロード後も幅が保持され、ダブルクリックで既定幅に戻る
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
- [x] grid-template-columns の固定値を CSS 変数へ置き換え
- [x] ドラッグハンドルの生成と drag/clamp/保存/リセットを review-comments.js に実装
- [x] test 追加 (3 問付き) と mutation 確認
- [x] headless で実測
- [x] version bump (1.27.0)
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-08-06 実装完了。ハンドルは toc / cmt-rail の中ではなく doc-grid 直下に置いた (両列は overflow で中身を切るため、中に置くとハンドルが clip される)。位置は CSS 変数から calc で導出し、ドラッグ中の追従は既存 schedulePositionCards の間引き実行。

headless 実測: 目次 232→312px (ドラッグ +80)、clamp 400px で停止、ダブルクリックで 232px に復帰、コメント列 332→432px、localStorage 保存 {"toc":400,"rail":432}。変数化を固定値へ戻した使い捨て copy で新規 test が落ちることを確認。unittest 312 件 OK。ユーザー実機確認 ok (2026-08-06)。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
列幅を CSS 変数化しドラッグ変更・clamp・保存・リセットを実装。headless 実測とユーザー実機確認で AC 全達成
<!-- SECTION:FINAL_SUMMARY:END -->
