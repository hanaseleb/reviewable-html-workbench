---
id: TASK-9
title: 公開プレビューの標準表示で目次を掲載する
status: To Do
assignee: []
created_date: '2026-08-05 00:46'
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
- [ ] #1 公開プレビューの標準表示で目次が表示され、最大化表示では隠れる
- [ ] #2 公開プレビューのコメント rail は標準・最大化とも非表示のまま
- [ ] #3 公開用 standalone HTML の標準表示に目次が含まれ、各項目が本文の見出しへ移動する
- [ ] #4 standalone を file:// でオフラインで開いても目次が動作する
- [ ] #5 目次の表示切替でも読んでいた箇所の画面上 y 座標が 2px 以内に留まる (TASK-8 の補正経路を通す)
- [ ] #6 python3 -m unittest discover -s tests が全 pass し、validate の status が ok
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Description の ## 決定事項 に決定内容が記録されている
- [ ] #2 Implementation Plan に決定事項を分解した todo がある
- [ ] #3 Implementation Notes に検討経緯 (rationale) が記録されている
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
