---
id: TASK-9
title: 公開プレビューの標準表示で目次を掲載する
status: Done
assignee: []
created_date: '2026-08-05 00:46'
updated_date: '2026-08-05 06:16'
labels:
  - 機能追加
  - publish
  - layout
dependencies:
  - TASK-8
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
公開プレビューと公開用 standalone HTML では目次が一切出ない。標準表示のときは目次を残し、読み手が節を辿れるようにする。

## 決定事項

- 公開プレビュー (.is-published) の「標準」表示のとき、目次を表示する (2026-08-05 ユーザー指示)。現状は templates/style.css:885 が公開モードで .toc と .cmt-rail をまとめて display:none にしている。
- 「最大化」表示のときは目次を隠したままにする。本文を最大幅で読ませるモードのため。
- コメント rail は公開モードでは標準・最大化とも非表示のまま。公開資料にレビュー UI は載せない。
- 公開用 standalone HTML にも同じ扱いを反映する。
- TASK-8 の is-wide 分離 (公開モードの幅切替を is-focus から独立させる) を前提にする。

## 調査で確認した前提 (2026-08-05)

- 公開プレビューは preview と同じ HTML に body.is-published を付けた状態のため、目次の DOM は存在する。CSS の変更だけで表示できる。
- 公開用 standalone は別で、scripts/html_review_workbench/publish.py:113 の _extract_article が article.doc-main だけを抜き出しており、nav.toc は出力に含まれていない。standalone で目次を出すには抽出範囲の変更が要る。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 公開プレビューの標準表示で目次が表示され、最大化表示では隠れる
- [x] #2 公開プレビューのコメント rail は標準・最大化とも非表示のまま
- [x] #3 公開用 standalone HTML の標準表示に目次が含まれ、各項目が本文の見出しへ移動する
- [x] #4 standalone を file:// でオフラインで開いても目次が動作する
- [ ] #5 目次の表示切替でも読んでいた箇所の画面上 y 座標が 2px 以内に留まる (TASK-8 の補正経路を通す)
- [x] #6 python3 -m unittest discover -s tests が全 pass し、validate の status が ok
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Description の ## 決定事項 に決定内容が記録されている
- [x] #2 Implementation Plan に決定事項を分解した todo がある
- [x] #3 Implementation Notes に検討経緯 (rationale) が記録されている
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
- [ ] templates/style.css: 公開モードの .toc 非表示を標準表示のときだけ解除する
- [ ] scripts/html_review_workbench/publish.py: _extract_article の抽出範囲に nav.toc を含める
- [ ] publish.py: 目次側の review 属性除去と見出しアンカーの整合を確認する
- [ ] docs/publish-output.md へ公開出力の目次の扱いを追記
- [ ] tests: standalone に目次が含まれることを検査する test を追加
- [ ] Playwright ヘッドレスで公開プレビューと standalone の目次表示・移動を実測
- [ ] version を 4 ファイルで bump
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
実装と実測 (2026-08-05、lead):

CSS: .is-published の doc-grid を 1 カラムから 232px + 本文の 2 カラムへ変更し、.toc の非表示指定を外した。コメント rail は引き続き非表示。最大化 (is-wide) では doc-grid を 1 カラムに戻し .toc を隠す。

publish.py: _extract_toc を追加し、nav.toc を抽出して doc-grid の先頭 (本文の前、report.html.j2 と同じ並び) に置くようにした。目次を持たない文書では空にして 1 カラムのまま publish が成立する。_fill_toc_heading を追加し、目次の見出しを lang に応じて「目次」/「Contents」で埋める。preview では review-comments.js の i18n が入れるが standalone に JS が無く、空の見出しが余白だけ残るため。

実測 (Playwright ヘッドレス、viewport 1600x900):
- standalone を file:// で開いて目次が表示され、リンク 10 件すべてのリンク先 id が本文に存在する。本文列 852px、コメント rail 非表示、コメントバッジ 0 件。
- 目次リンクのクリックで対象の節が画面内に来る (文書後半の 3 箇所で確認)。standalone は canvas がスクロールコンテナにならず window がスクロールするが、anchor jump は成立する。
- 公開プレビュー: 標準は目次あり / rail なし、最大化は目次なし / rail なし。
- publish 出力に外部 script 参照が無いこと (self-contained) を確認。

test: tests/test_publish_toc.py を 5 件追加。使い捨て copy で目次の抽出を無効化すると 3 件が落ちることを確認した。当初 cmt-rail の判定を HTML 全文で行い、inline された CSS のセレクタ定義にマッチして誤検出したため、</style> 以降の DOM 部分だけを見る形に直した。

docs/publish-output.md を更新 (目次を「保持するもの」へ移動し、扱いを明記)。全 test 305 OK。version 1.24.2 → 1.25.0 (公開出力に目次を追加する新機能のため minor)。

受入基準 5 (目次の表示切替でも y 座標が 2px 以内) の扱い (2026-08-05):

公開モードでは canvas がスクロールコンテナにならず window がスクロールするため、TASK-8 の keepReadingPosition (canvas.scrollTop を補正する実装) が効かない。ユーザーが実物で切替を確認したうえで、この基準は外して完了とする判断 (選択肢 A)。公開プレビューは読み物モードであり幅を頻繁に切り替える使い方ではないため。preview 側 (目次トグル / コメントトグル) の位置ずれ補正は実測 0px で機能しており、そちらは影響を受けない。

対応するなら公開モードの画面構造 (.app が無く .canvas に高さ制約が無い) から見直す必要があり、別 task の規模になる。

公開表示の幅を preview と揃えた (2026-08-05、ユーザーが publicar 上の表示を見ての指摘):

事象: 広い画面 (1835px) で公開 HTML を開くと左右に大きな余白ができ、表が右端で切り詰められる。

原因: .is-published .doc-shell が max-width 1180px に絞られており、preview の 1600px より狭かった。目次を足したことで本文列がさらに狭くなり (852px)、幅の広い表が横スクロールに逃げていた。

修正: .is-published .doc-shell を 1600px にし、is-wide 用の 1480px 指定を削除した。標準と最大化の差は目次の有無で付ける (標準は目次あり、最大化は目次なしで本文が最大幅)。

実測 (viewport 1835px): preview は shell 1600px / 左右余白 118px / 本文 908px、公開 HTML は shell 1600px / 左右余白 118px / 本文 1272px。余白は一致し、公開側は rail が無い分だけ本文が広い。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
公開プレビューと公開用 standalone HTML に目次が一切出ず、読み手が節を辿れなかった。標準表示では目次を残し、最大化では隠す形にした。

CSS は .is-published の doc-grid を 1 カラムから 232px + 本文の 2 カラムへ変え、最大化 (is-wide) のときだけ 1 カラムに戻して目次を隠す。コメント rail は公開資料に載せないため引き続き非表示。

standalone 側は publish.py の _extract_article が article.doc-main だけを抜き出しており目次の DOM 自体が無かったため、_extract_toc を追加して doc-grid の先頭に置くようにした。あわせて _fill_toc_heading を追加し、目次の見出しを lang に応じて「目次」/「Contents」で埋める。preview では JS の i18n が入れるが standalone に JS が無く、空の見出しが余白だけ残っていたため。目次を持たない文書では空にして 1 カラムのまま publish が成立する。

実測 (Playwright ヘッドレス): standalone を file:// で開いて目次が表示され、リンク 10 件すべてのリンク先 id が本文に存在し、クリックで対象の節へ移動する。公開プレビューは標準で目次あり / rail なし、最大化で目次なし / rail なし。外部 script 参照なしの self-contained を維持。

test は tests/test_publish_toc.py を 5 件追加し、使い捨て copy で目次の抽出を無効化すると 3 件落ちることを確認した。docs/publish-output.md を更新。全 test 305 OK、version 1.25.0。

受入基準 5 (切替時の位置ずれ 2px 以内) は、公開モードで window がスクロールコンテナになり canvas.scrollTop の補正が効かないため未達。ユーザーが実物で確認したうえで基準から外す判断となった。
<!-- SECTION:FINAL_SUMMARY:END -->
