---
id: TASK-5
title: 資料に操作部品を置き、触った結果を agent が読めるようにする
status: Done
assignee: []
created_date: '2026-07-30 09:15'
updated_date: '2026-07-30 09:55'
labels: []
dependencies: []
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 決定事項

Artifact が提供している操作部品 (スライダー・トグル・並べ替え) を RHW でも書けるようにし、触って決めた結果を agent が直接読めるようにする。

- html block 内の inline script と inline event handler を許可する。禁止するのは外部 host からの読み込み (script src / 外部 stylesheet) だけとし、bundle が手元で完結する性質は保つ
- 触った結果の保存先を preview server に新設する。名前は英数字とハイフン・アンダースコアに限り path traversal を防ぐ
- 保存は server → localStorage → メモリの 3 段 fallback とし、publish した standalone や file:// でも操作が止まらないようにする
- 連続入力 (スライダー等) では server への書き込みを debounce でまとめる。手元の保存は毎回即時に行う
- agent は annotations/state/<name>.json をファイルとして読む。Artifact の Copy as prompt (人が手でコピー) より短い経路にする

## 背景

記事執筆のため Artifact の機能範囲を調べた過程で、Artifact が inline JavaScript で操作部品を作れることが分かった。RHW は check-model が script タグを弾いていたため書けなかった。render / validate / publish はいずれも script を通していたので、障壁は検査 4 行だけだった。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 html block の inline script が check-model を通り、render 後の HTML にそのまま残る
- [ ] #2 外部 script src と外部 stylesheet は check-model が error にする
- [ ] #3 PUT /annotations/state/<name>.json で状態が保存され、別ブラウザ相当の GET で読める
- [ ] #4 不正な名前 (../ 等) の PUT が 400 または 404 で拒否され、bundle 外にファイルが作られない
- [ ] #5 debounce 指定時に手元の保存は即時、server への書き込みは入力が止まってから 1 回だけ行われる
- [ ] #6 publish した standalone HTML でも操作部品が動き、helper が inline 化される
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

### 障壁の実測

記事執筆のため Artifact の機能範囲を調べた過程で、Artifact が CSP 下の inline JavaScript で操作部品を作れることが分かった。RHW で同じことができない理由を確かめるため、inline script を含む文書モデルを作って各段階に通した。

| 段階 | 結果 |
|---|---|
| check-model | error (script tag を弾く) |
| render | 通る。検査を呼ばない |
| render 後の HTML | inline script がそのまま残る。CSP なし = 実際に動く |
| publish | 通る。standalone にも残る |
| validate | ok。script を弾かない |

止めていたのは model_quality.py の 4 行だけだった。当初は data-* 属性で宣言して同梱 JS が解釈する方式を推したが、ユーザーの判断で「Artifact でできることを 100% できるようにする」方針を採り、inline script を許可する形にした。

### 検査を緩める範囲

無条件に許可せず、外部 host からの読み込み (script src / 外部 stylesheet) を新たに error にした。Artifact の CSP と同じ思想 (外部読み込みは全ブロック、inline は許可) で、bundle が手元で完結する性質を保つ。

script 検査には元々テストが 1 件もなかった。検査を変えても既存テストが落ちなかったのはそのため。今回 5 件を追加してこの穴を埋めた。

### head での読み込み

helper を </body> 直前で読み込むと、html block の inline script より後に実行されて RHWState が未定義になる。head に移した。publish の standalone でも同じ理由で article より前 (</head> 直前) に inline 化している。テストで順序を検査している。

### debounce の追加

当初は change イベントで保存する設計にし、SKILL.md にも「input ではなく change で呼ぶ」と書いた。理由は input で呼ぶとスライダーを動かすだけで PUT が 100 回以上飛ぶため。

しかしユーザーが実機で試したところ、スライダーを動かしている間は何の反応もなく「保存されない」ように見えた。triage board は dragend で操作と表示が一致していたのに対し、スライダーは動作中に無反応で、利用者から見ると壊れているのと区別が付かない。

save(name, state, {debounce: N}) を追加して解決した。手元の保存 (memory / localStorage) は毎回即時に行い、server への書き込みだけを入力が止まってから 1 回にまとめる。呼び出し側は表示更新と同じ場所で save() を呼べる。debounce 待ちの間の戻り値は superseded とし、画面に「保存中」を出せるようにした。

load() も debounce 待ちの間は server の古い値ではなく手元の値を返すよう直した。

## 残作業

検証ページ (セッション作業領域、gitignore 済み) の slider がまだ change イベント版で、debounce 版に差し替えていない。ユーザーによる動作確認も未実施。
<!-- SECTION:NOTES:END -->
