---
id: TASK-6
title: 文字の大きさで段落を強調する lead / lead-note を廃止する
status: Done
assignee: []
created_date: '2026-07-30 09:15'
updated_date: '2026-07-30 09:55'
labels: []
dependencies: []
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 決定事項

lead / lead-note を style.css と skill 一覧から削除する。

- lead は font-size と line-height を変えるだけで、内容の事実を何も符号化していない。SKILL.md に入れた artifact-design 由来の指針「構造装飾は内容の事実を符号化する時だけ使う」に class 自体が反していた
- 文書全体の導入は metadata.deck が担うので、節ごとの導入段落は不要
- 一覧から消すだけでは inline style で再実装される。代替を明示する: 強調したい段落は推奨・決定・注意のいずれかなので reco / decision-panel / callout block のうち内容に合うものを使う
- --fs-lead トークンは doc-deck と document-header が使っているので残す

## 背景

記事を書く過程で lead を 3 箇所に使い、3 箇所すべてで誤用した。どの節も「同じ重さの主張が 2 つ並ぶ」構造で、1 段落目だけ大きくすると 2 段落目が補足に見えてしまう。SKILL.md の記述が「章冒頭の導入段落に使う」だけで、使わない条件がなかったため、節の 1 段落目に機械的に付ける読み方になっていた。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 style.css から .lead / .lead strong / .lead-note の定義が削除されている
- [ ] #2 skill 一覧 (ja / en) から lead の記載が消え、SKILL.md 2 本に残存しない
- [ ] #3 代替の指示 (reco / decision-panel / callout への誘導と metadata.deck の役割) が skill 一覧に書かれている
- [ ] #4 --fs-lead を使っている doc-deck と document-header の表示が壊れていない
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Description の ## 決定事項 に決定内容が記録されている
- [ ] #2 Implementation Plan に決定事項を分解した todo がある
- [ ] #3 Implementation Notes に検討経緯 (rationale) が記録されている
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 検討経緯

### 誤用の発見

記事を書く過程で lead を 3 箇所 (はじめに / なぜ HTML を成果物にするのか / RHW が提供しているもの) に使った。ユーザーがブラウザで見て「なんで文字サイズが違ってるんだっけ?」と指摘した。

確認したところ 3 箇所すべてが同じ構造だった。1 段落目と 2 段落目がどちらも同じ重さの主張で、大きさを変える理由がない。lead を付けると 2 段落目が補足に見える。

原因は SKILL.md の記述だった。「章冒頭の導入段落に使う」とだけ書いてあり、使わない条件がなかったため、節の 1 段落目に機械的に付ける読み方になっていた。

### 削除の判断

ユーザーの「そもそも lead いるんだっけ?」を受けて実装を確認した。lead は font-size と line-height を変えるだけ (style.css の 4 行)、lead-note はそれに色の薄さが加わるだけ (1 行)。

削除を選んだ理由は 3 つ。

1. 文書全体の導入は metadata.deck が既に担っている。節ごとにもう一段導入を作る必要が薄い
2. 「大きくする」以外の意味を持たない。reco や decision-panel は「これは推奨」「これは決定」という内容の区分を符号化しているが、lead は何を符号化しているのか読み手に伝わらない。SKILL.md に入れた artifact-design 由来の指針「構造装飾は内容の事実を符号化する時だけ使う」に class 自体が反していた
3. 誤用のコストが実際に出た。使い方を細かく書くより、選択肢から外す方が確実

### 一覧から消すだけでは足りない理由

強調したいという動機自体は妥当なので、class を消すだけでは inline style で再実装される。代替を明示する形にした。

「段落を文字の大きさで強調しない。強調したい段落があるなら、それは推奨・決定・注意のいずれかなので、reco / decision-panel / callout block のうち内容に合うものを使う。文書全体の導入は metadata.deck が担うので、節ごとに導入段落を作らない。」

「使うな」ではなく「代わりにこれを使う」の形にしたので、動機が内容の区分 (推奨か決定か注意か) を選ぶ判断に変わる。

### トークンの残置

--fs-lead トークンは削除しなかった。doc-deck (文書冒頭の副題) と document-header がまだ使っており、消すと別の箇所が壊れる。

### 検査

lead を検証しているテストは 1 件もなかった。削除後も 274 件すべて OK。配布対象 (templates/ / docs/skill-fragments/ / skills/) に残存参照なし。docs/design/workbench.css (2026-06-14 の静的な参考資料、配布対象外・未参照) にのみ旧定義が残る。
<!-- SECTION:NOTES:END -->
