---
id: TASK-11
title: 'notify-update の無言失敗と、更新バナーがリロードで消えない問題を直す (Issue #7)'
status: Done
assignee: []
created_date: '2026-08-05 02:57'
updated_date: '2026-08-05 03:24'
labels:
  - バグ修正
  - preview
  - cli
dependencies: []
ordinal: 11000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
notify-update は preview server 経由でブラウザへ更新通知を送る CLI。--url を省略すると、preview session の URL が見つかっても常に exit 2 で終わり、通知が送られない。

## 決定事項

- cli.py:295 の return 2 を if url is None: ブロック内へ移す。現状は if not url: の直下にあるため、URL が見つかった場合でも send_notify に到達せず、failed の JSON も出力されない (無言の失敗)。
- notify_update の動作を検査する test を追加する。現在この関数を検査する test が無く、CI で検出できなかった。
- 修正後、Issue #7 に結果を返信する。
- version は patch bump (1.24.0 → 1.24.1)。

## 影響 (2026-08-05 lead が実測)

- 再現: preview 起動状態で notify-update --root <dir> を実行すると exit 2 で出力なし。--url を明示すると {"ok": true, "event_type": "document_updated"} で exit 0。
- skills/reviewable-design-doc/SKILL.md の 2 箇所 (400 行付近と 501 行付近) のコマンド例が --url を渡していない。skill の指示どおり動く agent はこの機能を成功させられない。利用者から見ると「コメントを反映したのに更新バナーが出ない」状態になる。
- 混入は ddaa1f7 (2026-07-02、モジュール分割のリファクタ)。約 1 か月間検出されなかった。

## 報告元

GitHub Issue #7 (shout8520、2026-07-31、Windows / v1.22.0 で発見)。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 preview 起動状態で notify-update を --url なしで実行すると exit 0 で {"ok": true} を返す
- [x] #2 preview が起動していない状態では failed の JSON を出力して exit 2 を返す
- [x] #3 notify_update の分岐を検査する test があり、修正前のコードでは落ちることを確認済み
- [x] #4 python3 -m unittest discover -s tests が全 pass
- [x] #5 version が 4 ファイルで 1.24.1 に揃う
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Description の ## 決定事項 に決定内容が記録されている
- [x] #2 Implementation Plan に決定事項を分解した todo がある
- [x] #3 Implementation Notes に検討経緯 (rationale) が記録されている
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
- [ ] scripts/html_review_workbench/cli.py の return 2 を if url is None: ブロック内へ移す
- [ ] notify_update の分岐を検査する test を追加し、修正前のコードで落ちることを確認する
- [ ] preview 起動状態と未起動状態の両方で実測する
- [ ] version を 1.24.1 へ 4 ファイル bump
- [ ] Issue #7 に結果を返信する

- [ ] preview_runtime.py の _handle_sse を、Last-Event-ID が無い初回接続では履歴を再送しない形にする
- [ ] 初回接続で履歴が再送されないこと、Last-Event-ID 付きの再接続では取りこぼさないことを検査する test を追加する
- [ ] preview 起動状態で notify-update → リロードを実測し、バナーが再表示されないことを確認する
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2 件目の不具合 (2026-08-05、ユーザーが preview で発見):

事象: 更新通知バナーの「リロード」ボタンを押してもバナーが消えない。

原因 (lead がコードを読んで特定、未実測): scripts/html_review_workbench/preview_runtime.py:164 の _handle_sse が Last-Event-ID header の無い接続で last_id = 0 とし、EventBus.subscribe に渡している。EventBus は履歴を 200 件保持し last_event_id より後を全て送るため、ブラウザが初回接続 (ページロード / リロード) するたびに過去の document_updated が再送される。ブラウザは初回接続で Last-Event-ID を送らない仕様のため、リロードすると必ず再送が起きてバナーが再表示される。

修正方針: Last-Event-ID が無い初回接続では履歴を再送せず、event_bus.last_id から開始する。header がある再接続 (SSE の自動再接続) では従来どおりその ID の後から送り、切断中のイベントの取りこぼしを防ぐ。

templates/review-comments.js:1875 のリロードボタンは window.location.reload() を呼ぶだけで、こちら側に問題はない。

修正と検証 (2026-08-05、lead):

1 件目 (notify-update の無言失敗): cli.py:295 の return 2 を if url is None: ブロック内へ移した。test は先に書いて落とし (send_notify が呼ばれず失敗)、修正後に 3 件 OK。実機でも preview 起動状態で --url なし実行が {"ok": true, "event_type": "document_updated"} / exit 0 になることを確認した。

2 件目 (更新バナーがリロードで消えない): preview_runtime.py に resolve_sse_start_id を切り出し、Last-Event-ID が無い初回接続では event_bus.last_id から開始する形にした。再接続 (header あり) は従来どおりその ID の後から送り、切断中のイベントを取りこぼさない。test 5 件を先に書いて 3 件落ちることを確認してから修正した。

実機確認 (Playwright ヘッドレス、preview を修正後のコードで再起動): 履歴に通知を 2 件積んだ状態でページを開いてもバナーが出ない、通知を送るとバナーが出る、バナーの「リロード」を押すとバナーが消える。3 点とも確認した。

既存 test 3 件の書き直し (ユーザー承認済み、2026-08-05): test_preview_server の 2 件と test_add_reply の 1 件が「publish してから /events に接続して過去のイベントを受け取る」形で書かれており、今回直した挙動 (初回接続で履歴を再送する) に依存していた。実運用ではブラウザが先に接続し agent が後から通知するため、_open_sse で接続を先に開いてから publish する形へ書き直した。検出力の確認として、使い捨て copy で EventBus.publish がイベントを積まないよう壊すと 3 件とも落ちることを確認した。

全 test 300 OK。version を 1.24.1 へ 4 ファイル bump。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
notify-update は cli.py の return 2 が 1 段浅く、preview session の URL が見つかっても send_notify に到達せず、failed の JSON すら出ない無言の失敗をしていた。skill が --url を渡さない形で呼ぶよう指示しているため、指示どおり動く agent は更新通知を一度も成功させられていなかった。return 2 を if url is None: ブロック内へ移し、preview 起動状態での --url なし実行が {"ok": true} / exit 0 になることを実測した。

あわせてユーザーが発見した「更新バナーのリロードを押しても消えない」問題を直した。原因は JS ではなく server 側で、preview_runtime.py が Last-Event-ID の無い初回接続で履歴 (最大 200 件) を全て再送していたこと。ブラウザは初回接続でこの header を送らないため、リロードのたびに過去の document_updated が蘇っていた。resolve_sse_start_id を切り出し、初回接続は現在位置から、再接続は Last-Event-ID の後から送る形にした。Playwright ヘッドレスと利用者の実機の両方で、履歴があってもページを開いてバナーが出ないこと、通知でバナーが出ること、リロードでバナーが消えることを確認した。

既存 test 3 件が「publish してから接続して過去のイベントを受け取る」形で書かれており、実運用に無い順序を検査していたためこのバグを検出できていなかった。ユーザー承認のうえ、接続を先に開いてから publish する形へ書き直し、EventBus.publish を壊すと 3 件とも落ちることを確認した。全 test 300 OK、version 1.24.1。
<!-- SECTION:FINAL_SUMMARY:END -->
