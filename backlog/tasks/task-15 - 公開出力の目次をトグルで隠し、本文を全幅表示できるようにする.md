---
id: TASK-15
title: 公開出力の目次をトグルで隠し、本文を全幅表示できるようにする
status: Done
assignee: []
created_date: '2026-08-05 12:56'
updated_date: '2026-08-05 13:08'
labels:
  - 機能追加
  - publish
  - layout
dependencies: []
ordinal: 15000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 決定事項

- 公開出力 (publicar 等に置く standalone HTML) の目次に「隠す」ボタンを付け、隠している間は左上の固定「目次」ボタンで戻せるようにする (2026-08-05 ユーザー依頼)
- 表示切替は既存の is-wide class の付け外しで行う (公開出力には目次なし全幅の CSS が既にあるため、layout 追加はしない)
- 切替時は読んでいた位置がずれないよう、preview と同じ「読点 block 基準の位置補正」を toc-nav.js 側にも実装する
- 状態は localStorage に保存し、次回も同じ表示で開く。保存が無い場合は書き出し時の状態 (標準/ワイド) に従う
- 1300px 以下は目次が元々出ないためボタンも出さない。印刷でも出さない
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 公開 standalone で目次の「隠す」を押すと目次が消え本文が全幅になる (headless で幅を実測)
- [x] #2 隠した状態で左上の「目次」ボタンから戻せる (headless で実測)
- [x] #3 切替の前後で読んでいた block の画面上の位置が保たれる
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
- [x] style.css にトグルボタン 2 つの style と媒体別の非表示を追加
- [x] toc-nav.js にボタン生成・is-wide 切替・位置補正・localStorage 保存を実装
- [x] test 追加 (3 問付き) と mutation 確認
- [x] headless で切替と幅を実測
- [x] version bump (1.26.0)
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-08-05 実装完了。切替は既存 is-wide class の付け外しに寄せ、全幅化 CSS は追加しなかった (TASK-9 で入れた公開出力の is-wide 規則をそのまま使う)。show ボタンの可視性も CSS の兄弟セレクタ (.canvas.is-wide ~ .toc-show-btn) で決め、JS は class 切替だけを持つ。

実測 (headless Chrome、clinial-deck-toc の standalone): 本文幅 1272px → 隠す 1536px → 戻す 1272px。目次 display:none、show ボタン表示、読点 block の画面位置 -64px → -64px (ずれ 0)、localStorage 保存を確認。

test: test_publish_toc.py に 1 件追加 (309 件 OK)。トグル実装を除去した使い捨て copy で対象 test が落ちることを確認。

注意: 公開済み資料へ反映するには bundle 再 render (assets/toc-nav.js の更新) + publicar 再 deploy が必要。

2026-08-05 デザイン往復: ユーザー実機確認で 2 回改訂。(1) 浮いた丸ボタン → 左端密着の取っ手型タブ、(2) 隠す/戻す 2 ボタン → 開閉共通の左端固定タブ 1 つ (矢印の向きだけで状態を示す)。最終実測: タブ位置は両状態とも (0,96) で不動、本文幅 1272⇄1536px、位置ずれ 0。ユーザー確認 ok (2026-08-05)。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
公開出力の目次に隠す/戻すトグルを実装。is-wide 機構流用、位置補正付き、headless 実測で AC 全達成
<!-- SECTION:FINAL_SUMMARY:END -->
