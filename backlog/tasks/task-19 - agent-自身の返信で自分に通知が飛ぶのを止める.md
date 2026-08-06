---
id: TASK-19
title: agent 自身の返信で自分に通知が飛ぶのを止める
status: Done
assignee: []
created_date: '2026-08-06 01:52'
updated_date: '2026-08-06 01:58'
labels:
  - バグ修正
  - preview
  - comment
dependencies: []
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 決定事項

- agent が add-reply で書いた変更が、file_watcher の mtime 検知で source:"file_watcher" として再配信され、agent 自身への通知になる (2026-08-06 ユーザー報告)。source:"agent" の filter (watch_comments) は既にあるが、この経路がすり抜ける
- server 側で「既に通知済みの書き込み」を記録し、file_watcher は記録と一致する mtime 変化を配信しない
- 記録する契機は 2 つ: comments PUT の書き込み後 / comment_updated イベントの受信後 (source を問わず — 送信者が配信済みのため)
- 外部からの直接編集 (記録に無い mtime) は今までどおり配信する
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 add-reply 相当 (直接書き込み + agent イベント) の後、file_watcher イベントが SSE に流れない (実 server で検証)
- [x] #2 通知なしの直接ファイル編集では file_watcher イベントが今までどおり流れる
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
- [x] CommentChangeTracker を実装し PUT / POST / file_watcher へ配線
- [x] test 追加 (3 問付き) と mutation 確認
- [x] version bump (1.28.1)
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-08-06 実装完了。通知済み mtime の記録は deque(maxlen=8) + lock の CommentChangeTracker。記録契機は comments PUT の書き込み後と comment_updated イベント受信後 (source 不問 — 送信者が配信済みのため)。file_watcher は記録に一致する mtime 変化を配信しない。

残余の race: 書き込みから通知 POST までの数 ms に watcher の poll が挟まると旧来どおり再配信される (確率は poll 2s に対し ms 級)。実害は「まれに従来動作」で済むため許容。

検証: 実 server + 実 CLI の end-to-end test — add-reply 後 3.5s 待って複製イベントが来ないこと、直接編集は配信されることを確認。抑止を外した copy で test が落ちることを確認。unittest 314 件 OK。server 側修正のため、稼働中の旧 preview には効かず、次回起動分から有効。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
file_watcher が agent 自身の書き込みを再配信して自己通知になる経路を、通知済み mtime の記録で遮断。実 server の end-to-end test で検証
<!-- SECTION:FINAL_SUMMARY:END -->
