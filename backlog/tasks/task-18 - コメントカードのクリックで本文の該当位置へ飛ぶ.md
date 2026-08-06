---
id: TASK-18
title: コメントカードのクリックで本文の該当位置へ飛ぶ
status: Done
assignee: []
created_date: '2026-08-06 01:29'
updated_date: '2026-08-06 01:40'
labels:
  - 機能追加
  - comment
  - ui
dependencies: []
ordinal: 18000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 決定事項

- コメント rail のカードをクリックしたら、そのコメントの本文ハイライトへスクロールする (2026-08-06 ユーザー依頼)
- ハイライトの無いコメントは所属 block へ飛ぶ
- 飛び先は画面上部 1/4 の位置、smooth スクロール。既に視界内 (上 15%〜70%) にある場合は動かさない
- ボタン・入力欄のクリックでは飛ばない (既存の除外をそのまま使う)
- 本文ハイライト → カードの既存動作は変えない
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 カードクリックで本文のハイライト位置へスクロールする (headless で実測)
- [x] #2 ハイライトが視界内にある場合はスクロールしない
- [x] #3 python3 -m unittest discover -s tests 全 pass
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Description の ## 決定事項 に決定内容が記録されている
- [x] #2 Implementation Plan に決定事項を分解した todo がある
- [x] #3 Implementation Notes に検討経緯 (rationale) が記録されている
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
- [x] scrollBodyToComment を実装しカードクリックへ接続
- [x] test 追加 (3 問付き) と mutation 確認
- [x] headless で実測
- [x] version bump (1.28.0)
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-08-06 実装完了。飛び先はハイライト (.cx[data-comment]) 優先、無ければ所属 block。視界の上 15%〜70% にある場合は動かさない。smooth スクロールは headless の仮想時間で進まないため、検証は scrollTo の呼び出し横取りで実施 — 実カードのクリックで scrollTo(4037) が 1 回呼ばれ、飛んだ後の再クリックは呼ばれないことを確認。

test: 初版の assert は関数定義の文字列に一致して mutation (呼び出し除去) が生き残ったため、呼び出し箇所を特定する形へ修正し、落ちることを確認した。unittest 313 件 OK。ユーザー実機確認 ok (2026-08-06)。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
カードクリックで本文の該当位置へ smooth スクロール。視界内では動かさない。実カードで実測しユーザー確認 ok
<!-- SECTION:FINAL_SUMMARY:END -->
