---
id: TASK-14
title: 公開出力の目次を動かす script を同梱し、title の番号二重描画を skill 側で防ぐ
status: Done
assignee: []
created_date: '2026-08-05 06:48'
updated_date: '2026-08-05 07:06'
labels:
  - バグ修正
  - publish
  - skill
dependencies: []
ordinal: 14000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
公開出力に目次を出したが、それを動かす JS が入っておらず現在位置ハイライトとジャンプ位置調整が効かない。さらにブラウザ書き出し版は目次を削除しており本文が潰れる。

## 決定事項

- 目次の移動と現在位置ハイライトだけを行う templates/assets/toc-nav.js を新設し、公開出力にだけ inline する (2026-08-05 ユーザーが選択肢 A を選択)。preview 側は review-comments.js が同じ処理を持つので読み込まない。preview (canvas がスクロールコンテナ) と standalone (window がスクロール) の両方で動くよう、スクロール対象を実行時に判定する。
- publish-export.js (ブラウザからの書き出し) が .toc を削除していたのをやめる。削除すると doc-grid の子が本文だけになり、2 カラム指定の 1 列目 (232px) に押し込まれて潰れる。
- CSS で保険を入れる。.is-published .doc-grid は既定 1 カラムとし、:has(> .toc) のときだけ 2 カラムにする。旧版の書き出し HTML でも潰れない。
- SKILL.md に「title に章番号を書かない」を明記する (2026-08-05 ユーザー指示)。番号は renderer が heading_level と blocks の並びから自動で振る設計だが、その指示が無かったため agent が元資料の番号付き構成をそのまま title に写し、本文と目次で番号が二重になっていた。

## 実測 (2026-08-05 lead)

- ダウンロードされた書き出し HTML: doc-grid の子が ARTICLE のみ、columns 232px 1272px、本文幅 232px。
- 修正後の公開出力: 目次あり、本文 1272px。スクロール追従のハイライトが 3 つの位置すべてで期待値と一致。目次クリックで見出しが画面上端から 28px に止まる (preview と同値)。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 公開出力で目次の現在位置ハイライトがスクロールに追従する
- [x] #2 公開出力で目次リンクのジャンプ位置が preview と同じ 28px になる
- [x] #3 ブラウザからの書き出し HTML で本文が潰れない
- [x] #4 目次を持たない出力では 1 カラムのまま崩れない
- [x] #5 両 SKILL.md に title へ章番号を書かない旨があり、build_skill_docs.py --check が通る
- [x] #6 python3 -m unittest discover -s tests が全 pass
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Description の ## 決定事項 に決定内容が記録されている
- [x] #2 Implementation Plan に決定事項を分解した todo がある
- [x] #3 Implementation Notes に検討経緯 (rationale) が記録されている
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
- [x] templates/assets/toc-nav.js を新設
- [x] render.py が bundle へ copy し、publish.py が目次のある文書にだけ inline する
- [x] publish-export.js の .toc 削除をやめ、toc-nav.js を inline する
- [x] CSS に :has(> .toc) の保険を入れる
- [x] 両 SKILL.md に title の番号禁止を明記
- [x] 実測と全 test
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
目次と見出しの番号表示 (2026-08-05、ユーザー指摘 2 件):

1. 目次の第 1 階層に章番号を付ける。CSS counter (toc-h2) を .toc-list に持たせ、li.toc-h2 > a の ::before に出す。見出しを持たない章 (下位項目だけの入れ物、render.py が空の span を出す形) は :not(:has(> a)) で採番から外し、本文側の番号とずれないようにした。あわせて li.toc-h2 > a の justify-content を space-between から flex-start にした。既定のままだと番号とタイトルが両端に離れ、短いタイトルが右に飛ぶ。

2. 本文の見出し番号のサイズを見出しに合わせる。h2 の番号が 15px、h3 が 13px、h4 が 12px の固定値で、見出し本体より小さく浮いて見えていた。3 つとも font-size: inherit にした。

実測: 目次は 1〜7 の章番号が左寄せで並び、下位の節には番号を出さない。本文の h2 見出しは番号と文字が同じ大きさで揃う。全 test 305 OK。

読み込み時のちらつき修正 (2026-08-05、ユーザーが Cmd+R で発見):

事象: リロードすると本文が一瞬左にずれてから戻る。第 1 章は動く幅が大きく、第 2 章はごく小さい。

原因 (実測で特定): review-comments.js がコメントのハイライト (.cx)、番号 (.cx-num)、バッジを本文へ後から差し込む。番号は inline 要素なので文字幅が増え、差し込みの前後で行の折り返しが変わる。毎フレーム記録すると t=41ms で本文の高さ 2636px / ハイライト 0 件だったものが、t=113ms で 2801px / 15 件になっていた (165px 増、最初の block は 33px 増)。block の位置と grid の列は 899 フレーム通して一度も動いておらず、動いて見えたのは行の中の文字の位置だった。第 1 章はハイライトが多く変化が大きい。

修正: 差し込みが終わるまで .prose を visibility: hidden にする (.prose.is-settling)。class は review-comments.js が冒頭で付け、コメント読み込み後に外す。JS が動かない環境では最初から付かないので本文が消えたままにはならない。読み込みが失敗して外す処理に届かない場合の保険として 1200ms のタイマーでも外す。

実測: t=45ms hidden / t=120ms visible。表示中の block の高さは 1 種類 (456px) のみで、見えている間は一切動かない。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
公開出力に目次を出したが、それを動かす JS が入っておらず現在位置ハイライトとジャンプ位置調整が効かなかった。さらにブラウザ書き出し版は目次を削除しており、doc-grid の子が本文だけになって 2 カラム指定の 1 列目 (232px) に押し込まれ潰れていた。

toc-nav.js を新設し、目次を出す公開出力にだけ inline する。preview (canvas がスクロールコンテナ) と standalone (window がスクロール) の両方で動くようスクロール対象を実行時に判定する。publish-export.js の .toc 削除をやめ、同じ script を添えるようにした。CSS では :has(> .toc) を使い、目次が無い出力は 1 カラムに戻す保険を入れた (旧版の書き出し HTML でも潰れない)。

実測でスクロール追従のハイライトが 3 つの位置すべてで期待値と一致し、目次クリックで見出しが画面上端から 28px に止まる (preview と同値)。

章タイトルが二重に描画される問題 (3. 3. 解決すべき…) は、資料の title に手書きの番号が入っていたことが原因で、根本は SKILL.md に「title に章番号を書かない」の指示が無かったこと。番号は renderer が heading_level と blocks の並びから自動で振る設計だが、その前提が書かれていなかったため agent が元資料の番号付き構成をそのまま写していた。両 SKILL.md (日英) に明記した。

あわせてユーザー指摘で 2 件直した。目次の第 1 階層に章番号を付け (見出しを持たない入れ物は採番から除外)、本文の見出し番号のサイズを固定値から inherit にして見出し本体と揃えた。

全 test 305 OK、version 1.26.0。
<!-- SECTION:FINAL_SUMMARY:END -->
