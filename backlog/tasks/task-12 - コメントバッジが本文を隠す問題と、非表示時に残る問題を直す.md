---
id: TASK-12
title: コメントバッジが本文を隠す問題と、非表示時に残る問題を直す
status: Done
assignee: []
created_date: '2026-08-05 03:48'
updated_date: '2026-08-05 05:10'
labels:
  - バグ修正
  - preview
  - layout
dependencies: []
ordinal: 12000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ハイライトを付けられなかったコメントを示す「Comment N」バッジが、block の右上に絶対配置され本文テキストの上に重なっている。またコメント表示を off にしても残る。

## 決定事項

- バッジを block の末尾に通常フローで置き、横並び (flex-wrap) にする (2026-08-05 ユーザーが選択肢 A を選択)。本文を一切隠さないことを最優先し、「どの block に属するコメントか」を示す本来の目的も保つ。block が数十 px 縦に伸びることは許容する。
- コメント表示 off のときバッジも隠す (.canvas.hide-comments .review-comment-badges を display:none)。現状は rail とハイライト装飾だけが消え、バッジは残っている。

## 実測 (2026-08-05 lead、output/tmp/backlog-md-hub-blog、viewport 1600x900)

- コメント 17 件のうち 11 件がバッジ表示 (選択テキストを本文中に見つけられなかったもの)。
- バッジ 11 件すべてが、同じ block 内の本文要素 (p / li / h2-h4 / td / th) の矩形と重なっている。両方表示・目次のみ非表示・コメントのみ非表示・両方非表示の 4 状態すべてで 11/11。
- コメント表示を off にしてもバッジは 11 件とも表示されたまま (rail と .cx の装飾は消える)。

## 検討した他の案 (不採用)

- 1 つにまとめる (💬 5): 隠す面積は最小だが個々のコメントを直接選べない。
- 番号だけの小さいバッジ: 変更は最小だが本文の上に重なる問題が残る。
- バッジ廃止: 本文はきれいになるが、どの block のコメントか本文から辿れなくなる。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 バッジが本文要素の矩形と重ならない (実測で 0 件)
- [x] #2 同じ block に複数のコメントがある場合もバッジが横に並び、縦積みで本文を覆わない
- [x] #3 コメント表示 off でバッジが消える
- [x] #4 バッジをクリックすると該当のコメントカードが有効になる動作が保たれる
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
- [ ] style.css の .review-comment-badges を絶対配置から通常フロー + flex-wrap の横並びへ変更
- [ ] .canvas.hide-comments .review-comment-badges を display:none にする
- [ ] バッジと本文の重なりを Playwright で実測し 0 件を確認する
- [ ] バッジのクリックで該当カードが有効になることを確認する
- [ ] version を bump する
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
実装と実測 (2026-08-05、lead、output/tmp/backlog-md-hub-blog、viewport 1600x900):

style.css の .review-comment-badges を position:absolute の縦積みから、通常フローの flex-wrap 横並び (justify-content: flex-end、margin-top: sp-3) へ変更した。あわせて .canvas.hide-comments .review-comment-badges を display:none にした。

変更前: バッジ 11 件すべてが同じ block 内の本文要素の矩形と重なっていた (4 つの表示状態すべてで 11/11)。コメント表示 off でもバッジは 11 件とも残っていた。

変更後: 本文との重なりは 4 状態すべてで 0 件。コメント表示 off ではバッジの表示数が 0 件。バッジをクリックすると対応するカードに is-active が付くことも確認した (Comment 5 → cmt_mrc7baf6 のカード)。

見た目は screenshot で確認済み。バッジは block の末尾右寄せに 1 行で並び、本文テキストを一切隠さない。

全 test 300 OK。version を 1.24.2 へ 4 ファイル bump。

バッジのスリム化 (2026-08-05、ユーザーが選択肢 b を選択):

「Comment N」の綴りが幅の大半を占めていたため、吹き出しアイコン (inline SVG) + 番号だけの表示にした。絵文字は環境で見た目が揃わないので、既存 UI と同じ inline SVG を使う。文字は等幅 font、11px。読み上げと hover 用に aria-label と title へ「Comment N」を残した。

寸法の実測: 変更前 高さ 30px / 幅 約 110px → 高さ 21px / 幅 35px。5 個並んだときの合計幅は約 550px から約 175px になる。

再確認: 本文との重なりは 4 状態すべてで 0 件、コメント表示 off でバッジ 0 件、バッジのクリックで対応カードに is-active が付く。全 test 300 OK。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
ハイライトを付けられなかったコメントを示す「Comment N」バッジが block の右上に絶対配置され、本文テキストの上に重なって文字を隠していた。実測ではバッジ 11 件すべてが本文要素の矩形と重なり、4 つの表示状態すべてで同じ状態だった。あわせてコメント表示を off にしてもバッジだけが残っていた。

絶対配置の縦積みをやめ、block の末尾に通常フローの横並び (flex-wrap、右寄せ) で置く形にした。コメント表示 off では display:none にする。実測で本文との重なりは 4 状態すべて 0 件、コメント表示 off でバッジ 0 件になった。

ユーザーが表示を見て「大きすぎる」と指摘したため 2 段階で縮めた。まず文字 12px→11px と padding の圧縮で高さ 30px→21px / 幅 110px→79px。さらにユーザーが選んだ案 (b) に従い、綴りをやめて吹き出しアイコン (inline SVG) + 番号だけの表示にして幅 35px にした。5 個並んだときの合計幅は約 550px から約 175px。絵文字ではなく inline SVG を使うのは環境で見た目が揃わないため。読み上げと hover 用に aria-label と title へ「Comment N」を残した。

バッジのクリックで対応カードに is-active が付く動作は維持。全 test 300 OK、version 1.24.2。
<!-- SECTION:FINAL_SUMMARY:END -->
