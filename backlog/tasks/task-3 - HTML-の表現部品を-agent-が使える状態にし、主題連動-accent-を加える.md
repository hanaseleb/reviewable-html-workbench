---
id: TASK-3
title: HTML の表現部品を agent が使える状態にし、主題連動 accent を加える
status: Done
assignee: []
created_date: '2026-07-30 00:34'
updated_date: '2026-07-30 05:07'
labels: []
dependencies: []
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 決定事項

- style.css に実装済みで未参照の表現 class (.table-cap / .rate / .reco / .tag-yes / .num / .decision-panel / .lead / .tok-* / .axis-sub) を、visual-html-renderer と reviewable-design-doc の SKILL.md 対応表に載せて解禁する (CSS 変更なし)
- artifact-design (Claude Code 内蔵 skill) 由来の表現指針 4 項を SKILL.md へ追加する: AI が作りがちな見た目の回避 / 構造装飾は事実の符号化 / 読む文書と操作する画面の作法分離 / 余白は gap で作る
- metadata.palette を新設し、brand / brand_soft の 2 トークンだけ light/dark 別に上書き可能にする。中立色・地色・レビュー状態色は固定のまま
- palette は check-model と validate の両方で WCAG コントラスト比 4.5:1 を機械検査し、不足なら error で落とす
- 明朝など書体の変更は対象外 (ユーザー判断)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 SKILL.md 2 本に class 一覧・表現指針・palette 手順が載っている
- [x] #2 palette 未指定で従来と同一 HTML が出る (テストで検証)
- [x] #3 コントラスト不足の palette で check-model と validate が error を返す (テストで検証)
- [x] #4 網羅 bundle で解禁 class 全種が描画され、ユーザーがブラウザで確認済み
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Description の ## 決定事項 に決定内容が記録されている
- [x] #2 Implementation Plan に決定事項を分解した todo がある
- [x] #3 Implementation Notes に検討経緯 (rationale) が記録されている
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. visual-html-renderer/SKILL.md へ class 一覧 + 表現指針 + palette 手順 + 自己レビュー項目を追記
2. reviewable-design-doc/SKILL.md へ同内容を追記
3. schemas の document-model schema に metadata.palette を追加
4. render.py に palette_style 生成、report.html.j2 に {{ palette_style }} を追加
5. validate_bundle.py / model_quality.py に WCAG コントラスト検査を追加
6. テスト追加 (未指定同一 / 指定時 style 注入 / 不足 error)
7. 網羅 bundle + 自然さ bundle で動作確認 → ユーザー確認 → verifier 受入
8. version 1.21.0 で commit (TASK-4 と同一 commit)
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 検討経緯

**出発点**: style.css (1231 行) に表現部品が実装済みだが、renderer からも SKILL.md からも一度も参照されていなかった。不足していたのは CSS ではなく agent への指示だと分かったため、CSS 変更 0 行で解禁する形にした。

**palette の上書き範囲**: 全トークン開放は自由度が高いが読みにくさを防げず、固定のままでは主題連動ができない。brand / brand_soft の 2 トークンに絞り WCAG 4.5:1 を機械検査する形を採った。

**検査の相手色 (自己検証で修正)**: 当初 brand を --paper とだけ比較していたが、style.css を追うと brand は 3 種類の地色 (.prose a は --paper / .toc の現在位置線は --bg-app / table.cmp hover は --paper-2) の上で使われる。--paper 比 5.04 / --bg-app 比 4.39 の色が素通りしていたため、最悪値で判定する形に変えた。あわせて #focusToggle が brand_soft 背景に brand 文字を載せるため、両方指定時の相互比も追加した。

**操作要素の分離 (verifier 指摘で修正)**: 当初「brand 背景の白文字比は検査しない」と判断した (既定 dark brand #6ea4dc の白文字比が 2.62 で、基準を課すと既定系統の色が指定不能になるため)。しかしこれは基準を課せないことと下限を設けないことの混同で、verifier が dark brand=#ffffff で操作要素の背景・文字がともに白 (比 1.00) になることを Chromium で実測した。--control-primary トークンを新設して白文字を載せる 4 箇所 (.btn.primary / .pub-exit .pe-btn.primary / .m-fab / .agent-avatar) を分離し、palette の上書き対象から外した。これで accent の自由度と操作要素の可読性が両立する。

**表現指針の出典**: Claude Code 2.1.220 バイナリに埋め込まれた artifact-design skill 本文 (offset 243333633、9,095 文字) を読み、4 項目を抽出した。書体の指針 (明朝の導入) はユーザー判断で対象外とした。

**検証**: 自動テスト 258 件 pass。網羅用 bundle と別題材の bundle を render し、verifier が別題材で SKILL.md の記載だけを頼りに class を書けることを確認 (迷いなしと報告)。ユーザーがブラウザで表示を確認済み。
<!-- SECTION:NOTES:END -->
