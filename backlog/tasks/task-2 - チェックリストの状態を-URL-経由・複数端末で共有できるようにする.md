---
id: TASK-2
title: チェックリストの状態を URL 経由・複数端末で共有できるようにする
status: Done
assignee: []
created_date: '2026-07-27 13:48'
updated_date: '2026-07-27 13:53'
labels:
  - 機能追加
  - checklist
  - preview
dependencies: []
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
作業チェックリストを file:// の単一ファイルでしか実用的に使えない状態から、安定した URL で開けて端末をまたいで同じ進捗を見られる状態にする。

## 決定事項
- preview server の port を固定できるようにする。現在 preview_server.py:152 で --serve 0 がハードコードされ OS 割当の ephemeral port になっているため、URL が起動ごとに変わり localStorage の origin も変わる。start_preview と CLI に port 引数を通す。
- チェック状態を preview server 側の annotations/checklist-state.json に保存する。PUT だけ実装し、読み出しは既存の静的配信を使う (未保存時は 404 を未設定として扱う)。
- ブラウザ側はサーバー保存と localStorage の両方へ書く。読み出しはサーバー優先、失敗時に localStorage へ退避する。これにより file:// の単一ファイルとしても引き続き動く。
- 同時編集は last-write-wins とする。一人で複数端末から使う前提のため競合解決は入れない。

## 見積
- agent 実行: 1 session / 30〜50 分
- 人間側関与: URL とスマホからの確認 1 回 / 10 分
- 不確実性: Tailscale 経由の他端末アクセスは未実測。届かない場合は bind 設定の切り分けが必要
- カレンダー期間: 本日中
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 preview --port <n> で指定した port が使われ、再起動しても同じ URL になる
- [x] #2 ブラウザでチェックした状態が annotations/checklist-state.json に保存される
- [x] #3 別ブラウザ (別 localStorage) で同じ URL を開くと同じチェック状態が表示される
- [x] #4 preview server が無い file:// でも従来通り localStorage で動作する
- [x] #5 python3 -m unittest discover -s tests が通り 4 ファイルの version が一致する
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Description の ## 決定事項 に決定内容が記録されている
- [x] #2 Implementation Plan に決定事項を分解した todo がある
- [x] #3 Implementation Notes に検討経緯 (rationale) が記録されている
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
- [x] preview_runtime.py に checklist-state.json の PUT ルートを追加
- [x] preview_server.py の start_preview / __main__ に port 引数を通す
- [x] cli.py の preview に --port を追加
- [x] task-checklist.js をサーバー保存優先・localStorage 退避に変更
- [x] tests に port 固定と状態保存の検証を追加
- [x] version を 1.20.0 へ bump
- [x] preview 起動 → 別ブラウザで状態共有を実測
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
検討経緯: 利用者から「なんで URL じゃないんだっけ?」と問われ、TASK-1 の設計判断を見直した。TASK-1 では preview server の port が ephemeral であることを動かせない制約として扱い file:// を主形態にしたが、実際には preview_server.py:152 の --serve 0 がハードコードされていただけで、引数化すれば固定できた。制約かどうかを確認せずに設計を寄せたことが誤りだった。加えて利用端末を確認しておらず、Mac 上の単一ブラウザだけを想定していた。

実測結果 (Playwright / Chromium, http://<tailscale-ip>:7424/index.html):
- 端末 A で 5 件チェック → 別 context (別 localStorage) の端末 B で開くと 5/43 が表示された。B のローカル保存にもサーバー状態が書き戻る。
- 端末 B で 1 件追加 → 端末 A のリロードで 6/43 に反映された。
- published/index.html を file:// で開いた場合も従来通り localStorage で動作し、保存・復元・書き出し・読み込み・全解除がすべて成功。pageerror 0 件。
- 不正 payload (state が object でない) は 400 で拒否し、ファイルを作らないことを test で確認。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
preview CLI に --port を追加して URL を固定できるようにし、チェック状態を preview server 側の annotations/checklist-state.json へ保存する PUT ルートを追加した。ブラウザ側はサーバー優先・localStorage 退避で動くため、URL 経由なら複数端末で同じ進捗を共有でき、file:// の単一ファイルとしても従来通り使える。2 つの独立ブラウザ context で双方向の反映を実測して確認した。
<!-- SECTION:FINAL_SUMMARY:END -->
