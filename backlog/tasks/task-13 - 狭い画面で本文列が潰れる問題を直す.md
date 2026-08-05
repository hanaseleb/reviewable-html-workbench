---
id: TASK-13
title: 狭い画面で本文列が潰れる問題を直す
status: Done
assignee: []
created_date: '2026-08-05 06:23'
updated_date: '2026-08-05 06:28'
labels:
  - バグ修正
  - preview
  - layout
dependencies: []
ordinal: 13000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
目次 232px と comment rail 332px が固定幅のため、画面が狭いと本文列だけが潰れる。レスポンシブの閾値が低く、1025〜1300px の帯で本文が 339〜508px まで縮んでいた。

## 決定事項

- レスポンシブの閾値を上げる。本文がおよそ 600px を切る前に外側の列から順に畳む (2026-08-05 ユーザー指摘)。
  - 3 カラム維持に要る幅: 232 + 600 + 332 + gap 64 + padding 64 = 1292px → 閾値 1300px
  - 2 カラム (本文 + rail) に要る幅: 600 + 332 + gap 32 + padding 64 = 1028px → 閾値 1040px
- 表示切替の列指定 (.canvas.hide-toc / .canvas.hide-comments) は詳細度が高くレスポンシブ側に勝ってしまうため、@media (min-width: 1301px) で囲み、3 カラムを保てる幅でだけ発火させる。
- レスポンシブ側のセレクタに .canvas を足し、公開モード (.is-published) の列指定より詳細度を上げる。
- 公開表示の doc-shell を 1180px から preview と同じ 1600px にする。公開だけ狭いと広い画面で左右に大きな余白ができ、表が切り詰められる。標準と最大化の差は目次の有無で付ける。

## 実測 (2026-08-05 lead、output/tmp/backlog-md-hub-blog)

変更前の本文幅: 1600px → 908px / 1200px → 508px / 1031px → 339px / 1000px → 584px。
1025〜1300px の帯で本文が潰れる。さらに「コメントのみ非表示」では列指定が詳細度でレスポンシブに勝ち、本文が 232px の列に入っていた。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 1400 / 1200 / 1031 / 950px のいずれでも本文列が 600px 以上ある
- [x] #2 表示切替の 3 状態 (両方表示 / 目次のみ非表示 / コメントのみ非表示) すべてで同じことが成り立つ
- [x] #3 公開 HTML の左右余白が preview の通常表示と一致する
- [x] #4 広い画面での表示切替と位置ずれ補正が壊れていない
- [x] #5 python3 -m unittest discover -s tests が全 pass
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Description の ## 決定事項 に決定内容が記録されている
- [x] #2 Implementation Plan に決定事項を分解した todo がある
- [x] #3 Implementation Notes に検討経緯 (rationale) が記録されている
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
- [x] レスポンシブの閾値を 1024/900 から 1300/1040 へ上げる
- [x] 表示切替の列指定を @media (min-width: 1301px) で囲む
- [x] レスポンシブ側のセレクタに .canvas を足して詳細度を上げる
- [x] 公開表示の doc-shell を 1600px にする
- [x] 4 つの幅 x 3 状態 + 公開 HTML で本文幅を実測
- [x] 広い画面でのバッジ重なり・位置ずれ補正の回帰を確認
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
実測 (2026-08-05、lead、Playwright ヘッドレス、output/tmp/backlog-md-hub-blog):

修正後の本文幅 (preview / 表示切替 3 状態 + 公開 HTML):
- 1400px: 両方表示 708 / 目次のみ非表示 972 / コメントのみ非表示 1072 / 公開 1072
- 1200px: 3 状態とも 784 / 公開 784 (目次が畳まれ、本文 + rail の 2 カラム)
- 1031px: 3 状態とも 999 / 公開 999 (1 カラム)
- 950px: 3 状態とも 918 / 公開 918 (1 カラム)

変更前は 1200px で 508、1031px で 339 まで潰れ、「コメントのみ非表示」では列指定が詳細度でレスポンシブに勝って本文が 232px の列に入っていた。

左右余白 (viewport 1835px): preview 118px / 公開 HTML 118px で一致。公開側は rail が無い分だけ本文が広い (preview 908px に対し 1272px)。

回帰確認: 広い画面でのコメントバッジと本文の重なり 0 件 (4 状態)、コメント非表示でバッジ 0 件、表示切替 6 通り x 6 スクロール位置の位置ずれすべて 0px。全 test 305 OK。

追加修正 (2026-08-05、ユーザーが右の空白を指摘):

事象: 1300px 以下でコメント表示を off にすると、本文の右に 352px の空白が残る。公開 HTML も同様 (1200px で columns が 784px 320px)。

原因: @media (max-width: 1300px) の .canvas .doc-grid が 2 列目に 320px を確保するが、rail が display:none (コメント非表示) または DOM ごと存在しない (公開モード) ため、その列が空のまま余白として見えていた。

修正: media query 内に .canvas.hide-comments .doc-grid と .is-published .canvas .doc-grid を追加し、rail が出ない状態では 1 カラムにする。

実測: 1500 / 1405 / 1350 / 1310 / 1301 / 1300 / 1250px のすべてで本文右端から grid 右端までの空きが 0px。1200px のコメント非表示は本文 784px から 1136px へ、公開 HTML も同じく 1136px になった。全 test 305 OK。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
目次 232px と comment rail 332px が固定幅のため、1025〜1300px の帯で本文列だけが潰れていた (1031px で 339px)。レスポンシブの閾値を 1024/900 から 1300/1040 へ上げ、本文がおよそ 600px を切る前に外側の列から順に畳むようにした。閾値は 3 カラム維持に要る幅 (232+600+332+gap 64+padding 64=1292px) と 2 カラムに要る幅 (600+332+32+64=1028px) から決めた。

あわせて 2 つの詳細度の問題を直した。表示切替の列指定 (.canvas.hide-toc / .canvas.hide-comments、詳細度 0,3,0) がレスポンシブ側 (0,1,0) に勝ち、狭い画面でも固定幅の列が残っていた。@media (min-width: 1301px) で囲み、3 カラムを保てる幅でだけ発火させた。またレスポンシブ側のセレクタに .canvas を足し、公開モードの列指定より詳細度を上げた。

公開表示の doc-shell は 1180px から preview と同じ 1600px にした。公開だけ狭いと広い画面 (1835px) で左右に大きな余白ができ、表が右端で切り詰められていた。標準と最大化の差は目次の有無で付ける。

実測で 4 つの幅 x 表示切替 3 状態 + 公開 HTML のすべてで本文列が 600px 以上になり、左右余白も preview と一致した。広い画面でのバッジ重なり・位置ずれ補正の回帰なし。全 test 305 OK。
<!-- SECTION:FINAL_SUMMARY:END -->
