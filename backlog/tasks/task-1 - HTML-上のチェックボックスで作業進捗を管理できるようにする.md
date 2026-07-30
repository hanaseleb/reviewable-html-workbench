---
id: TASK-1
title: HTML 上のチェックボックスで作業進捗を管理できるようにする
status: Done
assignee: []
created_date: '2026-07-27 05:27'
updated_date: '2026-07-27 05:37'
labels:
  - 機能追加
  - checklist
  - publish
dependencies: []
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
資料の作業一覧を Notion へ移さず、生成した HTML 単体でチェックしながら進捗管理できるようにする。

## 決定事項
- html block 内に <input type="checkbox" data-task-check="<id>"> を書き、状態管理は templates 側の共通 JS が担う。check-model が html block 内の <script> と inline event handler をエラーにするため (model_quality.py:81-84)、資料側に JS を書かない。
- 主な利用形態は publish で生成する standalone HTML 1 ファイルとする。preview server の port は ephemeral で毎回変わり localStorage の origin が変わるため、preview 経由を主形態にしない。
- チェック状態は localStorage に保存し、加えて JSON エクスポート/インポートを提供する。file:// での localStorage 挙動が未検証のため、効かない環境でも状態を持ち運べるようにする。
- 進捗バーを全体とセクション別に表示する。

## 見積
- agent 実行: 1 session / 30〜60 分
- 人間側関与: ブラウザでの動作確認 1 回 / 15 分
- 不確実性: file:// で localStorage が動作しない場合、エクスポート/インポート運用へ縮退 (+20 分)
- カレンダー期間: 本日中
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 publish した standalone HTML でチェックボックスを操作でき、リロード後も状態が復元される (実測で確認)
- [x] #2 進捗バーが全体・セクション別に正しい件数と割合を表示する
- [x] #3 JSON エクスポートしたファイルをインポートすると状態が復元される
- [x] #4 python3 -m unittest discover -s tests が通る
- [x] #5 plugin.json / marketplace.json / codex plugin.json / pyproject.toml の version が一致する
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Description の ## 決定事項 に決定内容が記録されている
- [x] #2 Implementation Plan に決定事項を分解した todo がある
- [x] #3 Implementation Notes に検討経緯 (rationale) が記録されている
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
- [x] templates/task-checklist.js を追加 (data-task-check の収集・localStorage 保存/復元・進捗バー・export/import)
- [x] templates/style.css にチェックリストと進捗バーのスタイルを追加
- [x] publish.py で checklist asset を standalone HTML へ inline 化
- [x] render.py 側の preview bundle にも同 asset を組み込む
- [x] document-model.json の A〜F タスク表に checkbox を追加
- [x] tests に checklist inline 化の検証を追加
- [x] 4 ファイルの version を minor bump
- [x] publish 実行 → ブラウザで動作確認
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
検討経緯: Notion 登録案がユーザーに却下され、HTML 単体で進捗管理する要求へ変わった。実現方法として (a) html block に script を直接埋める (b) renderer 側に機能追加 (c) workbench 外に単独 HTML を作る、の 3 案を比較した。(a) は model_quality.py が html block 内の script と inline event handler を明示的にエラーにしており、意図して置かれたガードを迂回することになるため不採用。(c) はガントチャートとレビューコメント機能を捨てることになるため不採用。よって (b) を採用した。

保存先の検討: localStorage 単独では preview server の port が ephemeral (--port 指定も無い) のため再起動ごとに origin が変わり状態が消える。よって standalone publish した単一ファイルを file:// で開く形を主形態とした。ただし file:// の localStorage 挙動は未実測のため、JSON エクスポート/インポートを併設して縮退経路を確保する。

実測結果 (Playwright / Chromium 1.61.1, file:// で standalone HTML を開いて確認):
- file:// でも localStorage は動作した。未検証としていた縮退の懸念は現時点の Chromium では発生しない。エクスポート/インポートは保険として維持する。
- チェックボックス 43 件を検出、進捗パネル 1 個、セクション行 6 個、見出しバッジ 6 個を生成。
- 3 件チェックで '3 / 43 (7%)'、バー幅 7%、行に is-checked 付与、localStorage へ保存。リロード後も復元。
- 全解除は 1 回目のクリックでラベルが「もう一度押すと全解除」に変わり件数は変化せず、2 回目で 0 に戻る。
- 書き出した JSON は schema_version / document_id / exported_at / state を持つ。localStorage.clear() 後に読み込んで 4/43 を復元し、リロードしても保持された。
- pageerror は 0 件。

C-8 (消費税納税地異動届) は令和5年1月以降廃止済みで完了させる作業が存在しないため、チェックボックスを付けなかった。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
html block に書いた <input type="checkbox" data-task-check="..."> を templates/assets/task-checklist.js が拾い、localStorage への保存・復元、全体とセクション別の進捗表示、JSON の書き出し・読み込みを行う機能を追加した。publish.py が standalone HTML へ inline 化し、単一ファイルをブラウザで開くだけで進捗管理できる。Playwright + Chromium で file:// を実測し、保存・復元・書き出し・読み込み・全解除の全経路が動作することを確認した。
<!-- SECTION:FINAL_SUMMARY:END -->
