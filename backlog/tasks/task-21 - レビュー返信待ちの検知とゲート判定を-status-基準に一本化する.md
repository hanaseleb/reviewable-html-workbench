---
id: TASK-21
title: レビュー返信待ちの検知とゲート判定を status 基準に一本化する
status: Done
assignee: []
created_date: '2026-08-08 22:56'
updated_date: '2026-08-08 23:55'
labels:
  - バグ修正
  - comment
  - preview
dependencies: []
ordinal: 21000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

2026-08-08 のレビュー往復 (病院評価制度調査 HTML) で、agent への差し戻し 2 件が見逃され、ユーザーが「回答しろ」と催促するまで放置された。

- cmt_msk03cbq: ユーザーの質問「ここで言う公式化の意味は?」が未返信のまま
- cmt_msk04ndv: agent 返信 (06:38) の後にユーザーが再指摘 (06:39) したが検知されず

原因: 「誰の番か」を正確に記録する状態機械 (comments.json の thread status) が既に存在するのに、通知 (watch-comments) とゲート (check-gates) の判定がそれを一切使わず、keyword 分類 (classify_thread) という別系統の推定に依存していた。分類は文書側の prefix/suffix に引きずられ (cmt_msk03cbq は本文の「勤務表に」の 表に で actionable 判定)、agent 返信の後にユーザー返信が来た順序も見ないため (cmt_msk04ndv は already_addressed)、両件とも gate=open。通知行は {"gate": "open"} だけで、agent に判断材料が無かった。

## 決定事項

- 判定元を status に一本化する。gate = status=needs_agent_review が 1 件でもあれば blocked、無ければ open。反映候補 = status=resolved
- keyword 分類 taxonomy (classify_thread と keyword 定数群、INGESTION_CLASSIFICATIONS) を廃止する。extract_replacement の機械置換抽出だけ残す
- gate payload は空でも全 key (gate / needs_agent_review_threads / resolved_threads / status_counts) を出す。旧実装の {"gate": "open"} への縮退 (情報ゼロの 1 行) を無くす
- --apply-model は needs_agent_review が残る間は実行しない (status 集計を適用より先に行う)。旧実装は適用が gate 計算より先で、返信待ちが残ったまま model が書き換わる配線だった
- 反映は status=resolved の thread だけに限定する (旧実装は actionable 分類なら未解決でも適用し得た)
- check-gates の --state 引数を削除する。ingest-review の --state は state v2 の書き先として残す
- SKILL.md に「gate は設計反映の可否だけを表す。返信要否は needs_agent_review_threads で見る」を明記し、禁止事項に「gate: open を根拠にコメントを読まず自分宛て無しと判断すること」を追加する
- version は 1.28.2 -> 2.0.0 (入出力仕様変更 = major)

## 旧 gate との意図した挙動差

1. status=needs_agent_review は分類・本文・返信順序に関係なく blocked (事故 2 型の是正。旧実装は open にし得た)
2. agent が返信済み (needs_user_reply) は常に open (旧実装は既定分類 needs_clarification により blocked にし得た)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 実事故 2 型 (agent 返信後のユーザー再指摘 / 本文に操作語を含む未返信質問) が gate=blocked かつ thread id 付きで watch-comments 通知行に載る (検証: 実事故 bundle の copy で preview + PUT + watch 実測)
- [x] #2 needs_agent_review が残る間は --apply-model 指定でも document model が書き換わらない (検証: python3 -m unittest tests.test_ingest_review)
- [x] #3 gate payload が空でも全 key を出す (検証: python3 -m unittest tests.test_resolution_gate)
- [x] #4 自動テスト全件 PASS と plugin manifest 検証通過 (検証: python3 -m unittest discover -s tests / claude plugins validate .)
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Description の ## 決定事項 に決定内容が記録されている
- [x] #2 Implementation Plan に決定事項を分解した todo がある
- [x] #3 Implementation Notes に検討経緯 (rationale) が記録されている
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
- [x] resolution_gate.py を status 判定へ書き換え、GateResult を新 4 欄に組み替え
- [x] ingest_review.py の taxonomy 削除、state v2、resolved-only 適用、返信待ち中の apply 抑止
- [x] cli.py の --state 削除・警告文・help 更新
- [x] テスト書き直し (gate 2 本へ統合 / ingest v2 / watch 統合 / render 3 本更新 / JS 分類語テスト削除)
- [x] SKILL.md・README.md の記述更新
- [x] version 4 ファイルを 2.0.0 へ bump
- [x] 検証 1〜3 (自動テスト / 実シナリオ / 構造検証) を実測
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 検討経緯

対処案は 2 つ提示し、ユーザーが (b) を選択した。

- (a) 最小修正: 通知に status 件数を足し、already_addressed 判定を「最後の返信が agent か」に変える。変更は小さいが、推定器 (keyword 分類) と状態機械 (status) の二重管理が残り、keyword 追加や state cache 経路で同型の見逃しが再発し得る。
- (b) status 一本化 (採用): 決定的な状態機械だけを信じる形にし、再発の入り口を閉じる。keyword 分類が gate に寄与するのは今回の誤動作の場面だけで、正常系では旧実装と同じ結果になることを机上分析で確認した上で選択した。

critic レビューを 2 系統で実施した。

- critic-2 (plan 整合性): R-001 (削除対象の引数名が --state-path と誤記。実際は --state) / R-002 (新旧 gate 比較行列の判定条件が誤りで、正しい実装を不合格にする) / R-003 (--apply-model が gate 計算より先に走る配線が plan に無い) を全件 blocking 採用。2 巡の再 review で全件解消を確認。
- critic-3 (過剰テスト観点、ユーザー指示で別 pane に分離): R-201 (事故 2 型は新実装では同一分岐なので 1 本の table test へ統合) / R-202 (新旧 gate 比較は unit の真理値表と実シナリオに重複するので削除し、実事故 2 件は実シナリオへ統合) / R-203 (分類語 UI 非混入テストは見張る taxonomy が消えるため削除) / R-204 (watch の open/blocked passthrough は同一経路なので 1 本へ統合) を全件採用。R-202 のみ修正付き採用とし、削除した比較の代わりに「旧 gate との意図した挙動差」2 種を決定事項へ明文化した。

## 実装と検証の結果

- Red 確認 (問い 3): 新しい table test を実装前に旧実装で実行し、事故 2 型が両方 'open' != 'blocked' で落ちることを実測。実装後は Green。
- 自動テスト: 306 tests OK (taxonomy 専用テスト削除と統合により 314 -> 306)。
- 実シナリオ: 実事故 bundle の copy を preview server で公開し、ブラウザ相当の PUT でユーザー返信を保存した結果、通知行は {"event": "comment_updated", "data": {"source": "browser"}, "gate": {"gate": "blocked", "needs_agent_review_threads": ["cmt_msk03cbq", "cmt_msk04ndv"], "resolved_threads": [], "status_counts": {"needs_agent_review": 2, "needs_user_reply": 3, "resolved": 0}}}。事故当時は {"gate": "open"} のみだった。
- ユーザー実機確認: 同 bundle の preview URL でユーザーがブラウザからコメントを保存し、gate=blocked と thread id が出ることを確認済み。
- 構造検証: claude plugins validate . -> Validation passed。JSON 3 ファイル OK。check-gates --help から --state が消えたことを確認。
- 変更 file: resolution_gate.py / ingest_review.py / cli.py / tests 6 件 / SKILL.md / README.md / version 4 件。

## 2026-08-09 version 判断の訂正

当初 2.0.0 (major) としたが、ユーザー指摘により 1.28.3 (patch) へ訂正した。AGENTS.md の表の「既存 skill の入出力仕様変更 = major」を字面で機械適用していたが、この plugin の利用者は agent であり、CLI 出力形式の変更は SKILL.md を同じ commit で更新しているため利用者側の追従作業は発生しない。実質は事故の恒久修正であり patch が妥当。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
gate と通知の判定元を comments.json の status に一本化し、keyword 分類 taxonomy を廃止した。実事故 2 型 (agent 返信後の再指摘 / 本文語彙に引きずられた未返信質問) が gate=blocked + thread id 付き通知として検知されることを、旧実装での Red 確認と実事故 bundle の実シナリオ実測で確認済み。
<!-- SECTION:FINAL_SUMMARY:END -->
