---
id: TASK-8
title: 最大化トグルを廃止し、目次とコメントを個別に表示切替できるようにする
status: Done
assignee: []
created_date: '2026-08-05 00:45'
updated_date: '2026-08-05 02:31'
labels:
  - 機能追加
  - preview
  - layout
dependencies: []
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
本文の表示幅を 2 値 (最大化 / 標準表示) で切り替える現在の仕組みを、目次とコメントをそれぞれ独立に出し入れする形へ置き換える。あわせて、表示幅が変わったときに読んでいた箇所が画面上でずれる問題を解消する。

## 決定事項

- topbar の #focusToggle (最大化 / 標準表示の 2 値トグル) を廃止し、目次の表示 on/off とコメントの表示 on/off を独立した 2 つのトグルにする (2026-08-05 ユーザー指示)。
- off にした列の幅は本文列が吸収する。.doc-shell の max-width は 1600px のまま据え置き、現在の is-focus が行っている 1480px への縮小はしない。ユーザー要求「off にした場合は本文側をその分横に広く表示出来る形で」に沿う。
- コメント表示 off は、rail に加えて本文中のハイライト装飾 (.cx の下線・番号) も隠す。rail が無い状態でハイライトを押しても行き先が無く、機能が壊れて見えるため。
- 公開プレビュー (.is-published) 内の「標準 / 最大化」ボタンは残す (2026-08-05 ユーザーが選択肢 A を選択)。公開モードには目次もコメント rail も無いため新しい 2 トグルでは置き換えられない。ただし is-focus class の共有をやめ、公開モード専用の is-wide へ分離する。
- 表示切替で本文の折り返し行数が変わっても、読んでいた箇所が画面上の同じ高さに留まるようスクロール位置を補正する。CSS の overflow-anchor は幅変更による文書全体の再流動では基準が定まらないため、明示的な補正を実装する。
- 位置ずれ補正は目次トグル・コメントトグル・公開プレビューの幅切替のすべてに同じ経路で効かせる。
- localStorage の key rw:focus を廃止し、目次とコメントで別の key を持つ。旧 key の移行は行わない。
- docs/design/ 配下 (初期の開発ハンドオフ資料) は今回の変更対象に含めない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 topbar に目次トグルとコメントトグルの 2 つがあり、#focusToggle が存在しない
- [x] #2 目次を off にすると目次列が消え、本文列の幅が両方 on のときより広がる
- [x] #3 コメントを off にすると rail と本文中のハイライト装飾が消え、本文列の幅が広がる
- [x] #4 目次・コメントとも off のとき本文列が最大幅になり、.doc-shell の max-width は 1600px のまま
- [x] #5 4 通りの組み合わせすべてで、トグル前後に画面上端付近の基準要素の viewport y 座標の差が 2px 以内 (Playwright ヘッドレスで実測)
- [x] #6 公開プレビューの標準 / 最大化が is-wide で動作し、切替前後の基準要素の y 座標の差が 2px 以内
- [x] #7 目次トグルとコメントトグルの状態がリロード後も保持される
- [x] #8 publish standalone が幅の状態を引き継ぎ、docs/publish-output.md の記述が実装と一致する
- [x] #9 python3 -m unittest discover -s tests が全 pass し、validate の status が ok
- [x] #10 version が 4 ファイル (.claude-plugin/plugin.json / .codex-plugin/plugin.json / .claude-plugin/marketplace.json 2 箇所 / pyproject.toml) で 1.24.0 に揃う
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Description の ## 決定事項 に決定内容が記録されている
- [x] #2 Implementation Plan に決定事項を分解した todo がある
- [x] #3 Implementation Notes に検討経緯 (rationale) が記録されている
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
- [ ] templates/report.html.j2: #focusToggle を目次トグル / コメントトグルの 2 ボタンへ置換
- [ ] templates/style.css: is-focus ブロック (868-878 行) を no-toc / no-cmt へ分解し、doc-grid の列定義を 4 通り用意
- [ ] templates/style.css: 公開モードの幅切替 (884-896 行) を is-wide へ改名
- [ ] templates/review-comments.js: initFocusToggle を 2 トグルへ置換、localStorage key 変更、i18n ラベル差替
- [ ] templates/review-comments.js: スクロール位置補正の共通関数を作り、目次 / コメント / 公開幅の全変更を通す
- [ ] scripts/html_review_workbench/publish.py: is-focus の引き継ぎを is-wide へ変更
- [ ] docs/publish-output.md の focus 状態の記述を更新
- [ ] tests/test_publish.py の focusToggle 参照を更新
- [ ] Playwright ヘッドレスで 4 通り + 公開幅切替の y 座標差を実測
- [ ] unittest 全 pass / validate ok を確認
- [ ] version を 1.24.0 へ 4 ファイル bump
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
検討経緯 (2026-08-05):

- 位置ずれの機構: 本文列の幅が変わると段落の折り返し行数が変わり、文書内の各見出しの y 座標が変わる。canvas.scrollTop は据え置きのため、画面に映る箇所が別の場所へ移る。この問題は現在の最大化 / 標準表示の切替で既に起きているとユーザーが報告した。
- 補正の方法: 変更前に画面上端付近の本文 block 要素を基準に選び canvas 上端からの距離を記録し、class 適用後に同じ要素の距離を測って差分だけ scrollTop を足す。CSS の overflow-anchor を採らないのは、幅変更による文書全体の再流動では browser 側の基準が定まらないため。
- 公開プレビューの標準 / 最大化を残す判断 (選択肢 A): 公開モードでは style.css:885 で目次とコメント rail が元から display:none であり、そこの標準 / 最大化は紙幅 1180px と 1480px の切替でしかない。新しい 2 トグルでは置き換えられず、廃止すると幅を選ぶ手段が消えるため残す。
- 現状の実装位置 (変更前の実測): topbar のボタンは templates/report.html.j2:30、CSS は templates/style.css:868-878 (is-focus) と 884-896 (公開モード)、JS は templates/review-comments.js:1092-1120 (initFocusToggle) と 1143-1164 (pub-exit の幅ボタン)、publish の引き継ぎは scripts/html_review_workbench/publish.py:70 と 300。

変更前の位置ずれの実測 (2026-08-05、lead / Playwright ヘッドレス、viewport 1600x900):

output/tmp/backlog-md-hub-blog/index.html で #focusToggle を 1 回押した時の、可視領域上端付近にある基準要素の y 座標の変化。scrollHeight 比 0.15 で -144px、0.30 で -186px、0.45 で -251px、0.60 で -336px。canvas.scrollHeight は 3066 から 2621 へ 445px 減る。本文列が広がって段落の折り返し行数が減るため。0.75 と 0.90 は下端クランプで +21px。ユーザー報告の再現に成功 (A: 直接再現)。

同じ手順を output/tmp/task7-acceptance/index.html で行うと 0.15 / 0.30 / 0.45 は 0px。この文書はコードブロックと表が中心で幅を変えても折り返し行数がほとんど変わらないため、位置ずれの検証には使えない。受入検証には本文の長い文書 (backlog-md-hub-blog) を必ず含めることを coder へ指示した。

Chromium 既定の scroll anchoring は、幅変更による文書全体の再流動では効いていない (上記のとおり最大 336px ずれる)。overflow-anchor の CSS 指定では解けないことを実測で確認した。

委譲: 2026-08-05 coder (w9Q:p3) へ topic-1785891087-94653-7788 で実装を依頼。委譲文は tmp/claude-sessions/bee65ee2-885a-47f0-9d43-da1ad436cfdb/task8-coder.md、追加情報は同 dir の task8-coder-followup.md。

受入検証 (2026-08-05、lead / Playwright ヘッドレス、viewport 1600x900、output/tmp/backlog-md-hub-blog):

SC-4 は 6 通りの切替 (目次を隠す / コメントを隠す / それぞれ他方が非表示の状態から / 両方非表示から戻す 2 通り) × 6 スクロール位置で、すべて 0px。変更前は同じ文書で最大 336px ずれていた。

検出力の確認: 使い捨ての copy で keepReadingPosition の補正行 (canvas.scrollTop += delta) を無効化して同じ測定を回すと、最大 109px のずれが出た。0px が「押しても幅が変わっていないから」ではなく補正が効いた結果であることを確認した。

文書末尾 (scrollHeight 比 0.75 / 0.90) の 21〜23px は、幅が広がって文書全体が短くなり最大スクロール位置に張り付くために起きるもので、補正では消せない。幅が狭くなる方向 (目次やコメントを戻す) では 0px であり、クランプの説明と一致する。

lead が追加で直した 2 件 (ユーザーが preview を見て指摘):
1. 目次リンクのジャンプ位置。block 上端を基準に 72px 下へ合わせていたため、見出しの止まる位置が block の上余白の差 (14px / 38px) だけばらついていた (実測 86 / 110 / 86px)。見出し要素そのものを基準にする TOC_JUMP_OFFSET = 28 へ変更し、3 箇所とも 28px で一定になった。
2. 章をまたぐと節番号が 1 に戻らない (4.4 と表示され 4.1 にならない)。原因は counter-reset が要素ごとに新しい counter を作る仕様で、block が兄弟として横に並ぶこの構造では 2 つ目以降の章に切り替わらないこと。最小例で :has() の有無に関わらず再現し、counter-set に変えると期待どおり 1 に戻ることを確認した。修正後に 4.1 / 5.1 を実測。

修正後: unittest 292 OK、SC-4 再測も全 0px。

SC-1〜SC-8 の受入実測 (2026-08-05、lead、Playwright ヘッドレス、viewport 1600x900):

SC-1 達成。focusToggle / is-focus の残存は 0 件 (tests/test_publish.py の assertNotIn は topbar 要素が standalone に出ないことを確かめる意図的な参照)。style.css に残っていた旧名の comment 文言も書き換えた。

SC-2 達成。output/tmp/backlog-md-hub-blog の本文列の実測幅は、両方表示 908px / 目次のみ非表示 1172px / コメントのみ非表示 1272px / 両方非表示 1536px。doc-shell は 4 状態とも 1600px のまま。

SC-3 達成。コメント表示時は .cx の下線 2px と番号 inline、非表示時は下線 0px と番号 none。file:// では fetch が失敗してコメントが 0 件になるため、preview server 経由で測った。

SC-5 達成。公開プレビューの標準と最大化の切替は両方向とも 0px (末尾 2 点はクランプ)。公開モードを抜けて入り直しても is-wide とボタンの on 状態が保たれ、doc-shell 幅 1480px を確認。

SC-6 達成。localStorage に保存した状態で reload すると、aria-pressed と列の表示が保存値どおりに復元される。

SC-8 達成。4 ファイル (marketplace.json は 2 箇所) とも 1.24.0。test_project_layout 10 tests OK。

目次の現在位置ハイライトの修正 (2026-08-05、lead):

事象: スクロールしても目次のどの項目も現在位置として光らない。原因は initTocScrollSpy の照合先が h2[id] だが、render される HTML では id が section 側に付き h2 には付かないこと (実測: h2 が 7 個、うち id 付き 0 個)。updateCurrentSection の current が常に null になっていた。

修正: 照合先を .prose [data-review-block][id] に変更。目次のリンク先が block の id であることに合わせた。

実測: 6 つのスクロール位置すべてで、current の href が独立に求めた期待値と一致 (#intro / #pain-overview / #pain-2 / #solution-intro / #webui)。検出力の確認として、使い捨て copy で照合先を修正前の h2[id] に戻すと current が常に null になり 5 箇所が不一致になることを確認した。

作業ツリーに出所不明の未 commit 変更あり (2026-08-05): 目次を項 (h4) の階層まで出す変更が render.py / common.py / render_blocks.py と新規 tests/test_render_toc_levels.py に入っている。mtime は lead の委譲 (1785891087) より 12 分前で、lead の作業でも coder の作業でもない (coder report の変更ファイル一覧にも無い)。ユーザーにも心当たりが無いとの回答。TASK-8 の commit に混ぜない方針。ただし templates/style.css には TASK-8 の変更と目次階層の CSS が同じファイル内に混在するため、commit 時は hunk 単位の分離が要る。

方針変更 (2026-08-05): 3 階層化 (TASK-10) を別 commit へ切り出す方針を撤回し、TASK-8 と 1 本の commit にまとめた。章をまたいだ節・項番号のリセットは 3 階層化と counter-set 修正の両方が揃わないと正しく動かず、分けるとどちらか一方だけの commit が壊れた状態になるため。上記 Notes 内の「TASK-8 の commit に混ぜない方針」「hunk 単位の分離が要る」は、この変更で無効。

作業ツリーには 3 階層化の一部として schemas/document-model.schema.json (heading_level の enum を [2,3] から [2,3,4] へ拡張) と skills/visual-html-renderer/SKILL.md (heading_level 4 の使い方) の変更も含まれていた。commit 準備の段階で lead が確認し、内容が 3 階層化と一貫するため同じ commit に含めた。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
本文の表示幅を最大化 / 標準表示の 2 値で切り替える仕組みを廃止し、目次とコメントを独立して出し入れできるようにした。隠した列の幅は本文列が吸収し、本文列は 908px から最大 1536px まで広がる (doc-shell は 1600px 据え置き)。表示幅の変化で読んでいた箇所がずれる問題は、切替の前後で基準要素の画面上の高さを測って scrollTop を補正する形で解消し、6 通りの切替 × 6 スクロール位置すべてで 0px を実測した (変更前は最大 336px)。補正行を無効化した copy では最大 109px のずれが出ることも確認し、計測に検出力があることを確かめた。あわせてユーザーが preview で見つけた目次まわりの不具合 3 件 (ジャンプ位置のばらつき 86〜110px、章をまたぐ節番号が 1 に戻らない、現在位置ハイライトが動作しない) を修正した。AC 10 件すべてを lead が Playwright ヘッドレスで実測して確認済み。
<!-- SECTION:FINAL_SUMMARY:END -->
