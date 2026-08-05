---
id: TASK-7
title: 印刷/PDF 出力・コード差分・用語集・highlight.js 同梱・表現指針を renderer へ取り込む
status: Done
assignee: []
created_date: '2026-08-04 13:34'
updated_date: '2026-08-05 00:27'
labels: []
dependencies: []
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
外部 skill (mathbullet/skills の html skill) の調査で確認した欠落機能を、bundle 完結方針を維持したまま取り込む。

## 決定事項

- 案 2 を採用 (2026-08-04 ユーザー合意): (a) @media print + export-pdf subcommand、(b) pre.diff コード差分部品、(c) dl.glossary 用語集、(e) highlight.js 同梱による自動着色、(f) 表現指針 3 点の fragment 追記。(d) 数式 (MathJax/KaTeX) は見送り。
- 外部 CDN 読み込みは導入しない。highlight.js は templates/assets/ へ vendored 同梱し、render 条件付き copy + publish inline 化 (mermaid.min.js と同じ機構)。
- highlight.js は BSD-3-Clause 遵守 (2026-08-04 ユーザー指示): /*! banner と license 全文を file 冒頭 comment に保持し、inline 後の standalone HTML にも残す。本体コードは改変しない。
- 自動着色の適用除外 (critic R-002): pre.diff 配下・.nohighlight に加え、tok-* descendant を持つ code を除外し、既存文書の手動着色を保持する。
- export-pdf は headless Chrome で PDF 化。Chrome 不在時は error JSON。外部サービス fallback 禁止。PDF 化はユーザー明示依頼時のみ。print では横スクロール容器の内容保持 (overflow visible / min-width 解除 / pre-wrap / sticky 解除) を行う。
- 用語集は sticky aside でなく文書冒頭の html block (dl.glossary) として置く (3 カラム layout と両立させるため)。
- version は実装時点の現行値から minor bump (critic R-001。2026-08-04 実測 1.22.0 → 1.23.0。4 ファイル同時)。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 code block (language-*)・pre.diff・dl.glossary を含む実文書を render → preview し、ブラウザで着色・差分・用語集の表示を確認した
publish 出力を file:// で開き、オフラインで同じ表示 (着色含む) になることを確認した
export-pdf で PDF が生成され、topbar / rail の無い印刷 layout になっていることを確認した
python3 -m unittest discover -s tests が全 pass、validate が status ok
standalone HTML 内に highlight.js の BSD-3-Clause license 表記が残っている
両 SKILL.md に新部品の対応表行と表現指針が build_skill_docs.py で同期されている

- [x] #2 publish 出力を file:// で開き、オフラインで同じ表示 (着色含む) になることを確認した
- [x] #3 export-pdf で PDF が生成され、topbar / rail の無い印刷 layout になっていることを確認した
- [x] #4 python3 -m unittest discover -s tests が全 pass、validate が status ok
- [x] #5 standalone HTML 内に highlight.js の BSD-3-Clause license 表記が残っている
- [x] #6 両 SKILL.md に新部品の対応表行と表現指針が build_skill_docs.py で同期されている
- [x] #7 手動 tok-* 着色と language-* 自動着色を併置した文書で、language-* は自動着色され tok-* の span/class/表示が保持されることをブラウザで確認した (R-002)
- [x] #8 PDF 内で 720px 超の比較表と長い行のコードが切れずに全内容を読めることを確認した (横スクロール内容保持)
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Description の ## 決定事項 に決定内容が記録されている
- [x] #2 Implementation Plan に決定事項を分解した todo がある
- [x] #3 Implementation Notes に検討経緯 (rationale) が記録されている
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
- [ ] style.css: @media print 追加 (topbar/toc/cmt-rail/操作 UI 非表示、1 カラム化、break-inside avoid、横スクロール容器の内容保持)
- [ ] export_pdf.py 新設 + cli.py に export-pdf subcommand 登録
- [ ] style.css: pre.diff (.add/.del/.ctx) + diff 機能色変数 (light/dark)
- [ ] style.css: dl.glossary (dt/dd 2 カラム grid)
- [ ] highlight.min.js (license banner + 全文付き) と highlight-init.js (pre.diff / .nohighlight / tok-* descendant を除外) を templates/assets/ へ追加
- [ ] render.py: 条件付き asset copy + report.html.j2 の {{ highlight_head }}
- [ ] publish.py: _inline_highlight_script 追加
- [ ] style.css: .hljs-* を --code-* 変数へマップ
- [ ] skill-fragments 更新 (html-style-classes / html-design-guidance) + build_skill_docs.py 同期
- [ ] 新 test 3 本 (render asset 出力 / publish inline / export-pdf 失敗経路、3 問付き)
- [ ] 既存 docs 同期 test の検出力確認 (使い捨て copy で fragment をずらして落とす。落とせなければ直接 diff で代替)
- [ ] version bump: 実装時点の現行値から minor (実測 1.22.0 → 1.23.0、4 ファイル)
- [ ] 実シナリオ検証 (preview 表示 / tok-* 互換 / file:// offline / license 表示 / PDF 生成・内容保持)
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
検討経緯: ユーザー依頼で https://github.com/mathbullet/skills/tree/main/plugins/html/skills/html を調査。外部 skill は CDN 依存 (Google Fonts/MathJax/highlight.js) の単一読み物 HTML 向けで、本 repo の bundle 完結方針とは衝突するため、機能を同梱形式へ翻訳して取り込む方針にした。6 候補 (a)-(f) を提示し、ユーザーが案 2 (数式以外) を採用。数式は利用予定が立った時に再検討。plan: ~/.claude/plans/https-github-com-mathbullet-skills-tree-jazzy-lightning.md、共有対応表: tmp/referent-tables/bee65ee2-885a-47f0-9d43-da1ad436cfdb.md。critic 第 1 gate 合格済み、細部レビュー進行中。

2026-08-04 critic 指摘反映: 画面で overflow-x: auto に逃がす既存 selector (.table-scroll / table.cmp / .code-body / .block-content pre) は印刷でスクロールできず内容が切れるため、@media print で overflow visible + min-width 解除 + pre-wrap 折り返し + sticky 解除の内容保持方針を plan 実装設計 1 に追加。受入の実シナリオに「PDF 内で 720px 超の表と長い行コードが切れず読める」を追加。

2026-08-04 critic 初回 Register R-001〜R-004 (Needs Rework) を全件 blocking 採用: R-001 version 基準値を現行 1.22.0 実測に修正 / R-002 tok-* descendant を自動着色から除外し互換 scenario を受入へ追加 / R-003 license 表示確認を両配布形態の受入操作へ追加 / R-004 既存 docs 同期 test に 3 問 (落とす操作含む) を通してから受入根拠に使う。体制表は critic 判定 Go (verifier 成功条件の明記済み)。

2026-08-04 critic 最終 verdict: Go (R-001〜R-005 全件 resolved。R-005 = plan 内対応表・共有対応表の highlight-init.js 除外条件を §4 の 3 条件に整合)。plan review 完了。実装許可はユーザー承認待ち。

plan: /Users/u1/.claude/plans/https-github-com-mathbullet-skills-tree-jazzy-lightning.md (承認済み 2026-08-04)。plan 受入条件との整合で AC #7 (tok-* 互換) / AC #8 (PDF 内容保持) を追加。

2026-08-04 14:10 (UTC) coder (w9Q:p3, grok) へ実装委譲 (topic-1785852621-66257-712)。委譲文: tmp/claude-sessions/bee65ee2-885a-47f0-9d43-da1ad436cfdb/delegation-coder-task7.md (SC-1〜SC-8)。commit は委譲に含めず lead 確認後に別途。

2026-08-04 lead 直接確認 (coder 報告と独立に実測): unittest 281 OK / version 4 ファイル一致 1.23.0 / publish standalone は外部読み込み 0 件・BSD-3-Clause + Copyright + 取得元 URL + v11.11.1 を保持 / build_skill_docs.py --check 一致・両 SKILL.md に新規記述 5 件ずつ。SC-5 は差し戻し: export-pdf は PDF を生成している (output/tmp/task7-acceptance/task7-acceptance.pdf 394,370 bytes・3 ページ・操作 UI 混入 0・比較表全列・長い行折り返しを pdftotext で確認) のに、Chrome プロセスが終了しないため subprocess timeout となり status:failed を返す実装欠陥。coder へ SC-5a〜SC-5d で差し戻し済み。

2026-08-04 SC-5 修正を lead 実測で確認: export-pdf が status:ok を 2 秒で返し PDF 394,370 bytes 生成、残存 Chrome 0。偽 ok 検査も実施 — index.html 不在は failed、PDF を書かない偽 Chrome では 8 秒で failed かつ PDF 未作成・プロセス残存なし。unittest 283 OK。verifier (w9Q:p4, codex) へ受入検証を委譲 (topic-1785854335-11758-16308, SC-1〜SC-10)。

2026-08-05 verifier 独立検査で NG 3 件。lead が全件再現確認して差し戻し (topic-1785855810-85970-7696): (1) SC-1 render.py:54 の has_pre_code が "<pre><code" 完全一致のため属性付き <pre id=x><code class=language-python> を取りこぼし着色されない。(2) SC-4 同梱 license comment が公式 LICENSE 原文を改変 (COPYRIGHT HOLDERS→REGENTS、the copyright holder→highlight.js)。原文 retain に当たらずユーザー指示違反。lead の初回確認では原文照合を行わず見落とした。(3) SC-5 @media print に theme 上書きが無く、dark 表示端末で PDF が白背景に淡色文字となりコントラスト 1.28:1 (WCAG 4.5:1 未満)。SC-2/3/6/7/8/9/10 は達成として受理。

2026-08-05 差し戻し 3 件の修正を lead 実測で確認: NG-1 = _PRE_CODE_RE (正規表現) で属性付き pre/code を検出、受入 bundle に asset 同梱を確認。NG-2 = 公式 LICENSE 原文 23 行が同梱 file に逐語一致 (改変語 REGENTS / name of highlight.js の残存 0)、standalone にも原文。NG-3 = @media print で :root と data-theme=dark/light に light token を強制。dark 状態の bundle を lead が作成し PDF 化 → pdftoppm 画像化 → pixel 測定で背景(255,255,255)/最暗(35,32,25) コントラスト 16.25:1 (WCAG 4.5:1 を満たす)。回帰: unittest 287 OK / validate ok / light 版 export-pdf status ok。verifier へ 2 巡目再検査を委譲 (topic-1785856212-81746-13375, RC-1〜RC-4)。

2026-08-05 verifier 2 巡目: RC-1 (属性付き pre/code 検出) / RC-3 (dark PDF 16.25:1) / RC-4 (回帰 unittest 287 OK・validate ok・version 5 値 1.23.0・Playwright 2 passed) は達成。RC-2 未達 — license 全文一致 test が tmp/ 配下の gitignore 対象 snapshot を glob し無ければ skipTest するため、clean checkout / CI では skip され、条文の部分改変 (must retain → should retain) を exit 0 のまま見逃すことを verifier が実測。lead も該当行を確認し差し戻し (topic-1785857211-92547-3130)。lead 設計判断: 公式 LICENSE 原文を tests/fixtures/highlightjs-LICENSE.txt として repo に置き、test から skip 経路を除去する。基準明確化: 旧文言 0 の対象は配布物に限定し、負の検査用定数が test 内に残るのは正しいとする。

2026-08-05 license 検査の修正を lead 実測で確認: tests/fixtures/highlightjs-LICENSE.txt を管理元に固定 (skipTest 除去、tmp/ 非参照、git 管理対象)。fixture 条文本体は公式 LICENSE 再取得分と逐語一致 (追加は取得元/取得日/編集禁止の 3 行コメントのみ)。使い捨て copy で must retain → should retain の 1 語改変 → Ran 4 tests / FAILED (failures=2) / skipped 0 を観測 (copy に tmp/ 無しのため clean checkout 相当も兼ねる)。本体 unittest 288 OK。verifier へ 3 巡目再検査を委譲 (topic-1785857618-75917-21987, RC-A/RC-B/RC-C)。

2026-08-05 verifier 3 巡目: RC-A (clean copy で license 4 tests skipped=0、fixture 欠落 copy は skip せず exit 1) / RC-B (must retain→should retain と IMPLIED WARRANTIES→IMPLIED CONDITIONS の 2 箇所改変で双方 exit 1) / RC-C 内容面 (fixture 本文と公式 raw 原文が byte 一致・SHA-256 6c081431591d9df696c82dc598fe1423765b8a299b200ed00b281afd0f64c490、288 OK、配布物の旧文言 0) を達成。RC-C の git 追跡未達は lead 裁定で差し戻さず: commit をユーザー確認後に行う方針による untracked であり実装欠陥ではない。ただし commit 時の必須手順として記録する — (1) tests/fixtures/highlightjs-LICENSE.txt を明示 add (2) commit 後に git ls-files tests/fixtures/ で追跡を確認。lead 側 CI 事前確認: build_skill_docs --check OK / unittest 288 OK / manifest JSON OK / CLI --help OK / version 5 値 1.23.0 一致。

2026-08-05 ユーザーが preview を見て表示の指摘 2 件 (commit 前): (A) 用語集 dl.glossary に行区切り線が存在しない (style.css:687-708 に外枠と gap のみ。ユーザー『薄くてというか存在してない?』が正確)。(B) light 表示でコード差分の文字コントラスト不足 — pre.diff の背景は light でも --code-bg #1d2127 (暗色) だが、light theme の差分文字色は白背景前提の濃い色 (--diff-add-ink #2f6b47 = 2.55:1、--diff-del-ink #9b3428 = 2.24:1、いずれも WCAG 4.5:1 未満)。文脈行 #8b9099 は 5.04:1 で足りるためユーザーの『ここだけ薄い』と一致。coder へ委譲 (topic-1785886160-49368-23701, SC-A1/A2/B1/B2/B3/C)。commit は本件の修正とユーザー再確認の後。

2026-08-05 表示指摘 2 件の修正を lead 実測で確認: (A) dl.glossary の dt/dd に --line-1 の border-bottom を追加、last-of-type で最終行の線なし、first-of-type で上余白調整。bundle の assets/style.css にも反映済み。(B) 差分文字色を light/dark/print の 3 箇所とも #8fce9b (add) / #e08fa8 (del) に統一。lead 再計算: 背景 #1d2127 (light) で add 8.83:1 / del 6.67:1 / ctx 5.04:1、背景 #15181d (dark) で 9.72:1 / 7.34:1 / 5.55:1 — いずれも WCAG 4.5:1 以上。回帰 unittest 288 OK / validate ok。preview (port 58405) が更新後 CSS を配信中。ユーザーの再確認待ち。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
外部 skill (mathbullet/skills html) の調査で見つかった欠落機能のうち案 2 (印刷/PDF・コード差分・用語集・highlight.js 同梱・表現指針) を実装し commit 5026b14 で main へ push、CI (Test / HOL Plugin Scanner) 両方 success。verifier の独立検証を 3 巡実施し 4 件の欠陥 (export-pdf が生成済み PDF を failed 報告 / 属性付き pre code の検出漏れ / dark 表示 PDF の低コントラスト / license 全文一致 test の CI skip) を修正。ユーザーの表示指摘 2 件 (用語集の行・列区切り線なし / light 表示の差分文字コントラスト 2.24-2.55:1) も修正し WCAG 4.5:1 以上 (6.67-8.83:1) を実測。version 1.23.0。数式対応は対象外として見送り。
<!-- SECTION:FINAL_SUMMARY:END -->
