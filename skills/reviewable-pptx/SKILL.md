---
name: reviewable-pptx
description: |
  Convert PPTX or PDF presentations into page-by-page reviewable HTML previews, discuss browser comments in the same threads, attach visual proposal images to agent replies, and produce a validated revision after feedback is resolved. PPTX input can return PPTX or PDF; PDF input always returns PDF. Use whenever a user asks to review or revise a presentation or PDF with positional comments. Triggers: PPTXをレビュー, PDFをレビュー, スライドにコメント, PDFにコメント, PowerPointを確認, コメントを反映してPPTXを修正, review this PPTX, review this PDF, review this deck, comment on these slides, revise the presentation from comments. 使用しない場面: 添付資料を伴わない通常のHTML文書レビュー、計画だけのプレビュー。
---

# Reviewable PPTX / PDF

PPTXまたはPDFをページ画像としてレビューし、位置注釈、コメントへの回答、視覚案、改訂ファイルまで同じスレッドで扱う。

## 原則

- 元ファイルを上書きしない。PPTX入力は最終形式をPPTXかPDFから選び、PDF入力はPDFだけを返す。
- 出力名は `<stem>-revised.pptx` または `<stem>-revised.pdf` とする。
- コメント未解決の間は本番ファイルを変更しない。提案画像は一時コピーから生成する。
- PPTX編集は実行環境の標準PPTX skill/toolingを使う。このpluginへ外部skillのコードを複製しない。
- `document-model.json` の `metadata.pptx.slides` または `metadata.pdf.pages` で `block_id` とページ番号を対応づける。
- 日本語依頼には日本語、英語依頼には英語で返信する。

## 言語方針 / Language behavior

Follow the language of the latest user request for progress updates, preview handoff text, comment replies, and final responses. 元資料は、明示的に翻訳を求められない限り翻訳しない。

## 1. レビューを開始する

入力の拡張子と署名を確認する。PPTX入力で最終形式が未指定なら `pptx` / `pdf` をユーザーに選んでもらう。PDF入力は `pdf` に固定し、PPTXを選択肢に出さない。

renderer repo rootを作業ディレクトリにして実行する。現在のチャットやworkspaceのcwdをrepo rootとして扱わない。

```bash
# PPTX input
python3 -m scripts.html_review_workbench.cli build-pptx-review \
  --input <absolute-input.pptx> \
  --output <absolute-review-dir> \
  --final-format <pptx-or-pdf> \
  --lang ja

# PDF input
python3 -m scripts.html_review_workbench.cli build-pdf-review \
  --input <absolute-input.pdf> \
  --output <absolute-review-dir> \
  --lang ja

python3 -m scripts.html_review_workbench.cli preview \
  --root <absolute-review-dir> \
  --mode local
```

返却JSONの `url` と `stop_command` を渡し、`watch-comments --root <absolute-review-dir>` を開始する。別端末からの閲覧が明示された場合だけ `--mode tailscale` を使う。

## 2. コメントへ回答する

画像をクリックすると点注釈、ドラッグすると矩形注釈になる。座標は画像幅・高さに対する0〜1の比率なので再描画後も位置を保つ。

コメント更新を検知したら `ingest-review` を実行し、`needs_agent_review` の全スレッドへ `add-reply` で回答する。

```bash
python3 -m scripts.html_review_workbench.cli ingest-review --root <absolute-review-dir>
python3 -m scripts.html_review_workbench.cli add-reply \
  --root <absolute-review-dir> \
  --thread-id <thread-id> \
  --kind answer \
  --body "<回答>"
```

視覚案が理解を早める場合は、一時コピーへ提案を適用してPNG化し、本文説明と一緒に返信へ添付する。

```bash
python3 -m scripts.html_review_workbench.cli add-reply \
  --root <absolute-review-dir> \
  --thread-id <thread-id> \
  --kind answer \
  --body "<提案内容>" \
  --image <absolute-proposal-page.png> \
  --image-alt "<提案後のページ説明>"
```

確認が必要なら `--kind clarification_request` を使い、合意まで同じスレッドで続ける。

## 3. 最終成果物へ反映する

1. `check-gates --require-resolved` を実行する。終了コード1なら変更しない。
2. `resolved` のコメントだけを元ファイルのコピーへ反映する。
3. PPTX入力では標準PPTX skill (`document-skills:pptx`) で編集・OOXML検証・全ページ画像QAを行う。PDF指定なら改訂PPTXを一時成果物としてPDFへ書き出し、PDFだけを納品する。
4. PDF入力では必要に応じてページを再構成し、改訂PDFだけを生成・検証する。元PDFが画像主体なら編集可能性を保証しない。
5. 改訂版を同じreview dirへ `--continue-review` で再投入し、`notify-update` を実行する。

```bash
python3 -m scripts.html_review_workbench.cli check-gates \
  --root <absolute-review-dir> \
  --require-resolved

# Revised PPTX source (final output may be PPTX or PDF)
python3 -m scripts.html_review_workbench.cli build-pptx-review \
  --input <absolute-revised.pptx> \
  --output <absolute-review-dir> \
  --final-format <pptx-or-pdf> \
  --lang ja \
  --continue-review

# Revised PDF source
python3 -m scripts.html_review_workbench.cli build-pdf-review \
  --input <absolute-revised.pdf> \
  --output <absolute-review-dir> \
  --lang ja \
  --continue-review

python3 -m scripts.html_review_workbench.cli notify-update \
  --root <absolute-review-dir> \
  --message "改訂版を更新しました"
```

最終応答には改訂ファイルのパス、反映・未反映コメント、検証結果を含める。

## 実シナリオ検証

1. 全ページがPNG化され、レビュー画面で欠けずに表示される。
2. 点・矩形コメントを作成し、`ingest-review` が同じページIDと座標を返す。
3. `add-reply --image` の本文と画像が同じスレッドに表示される。
4. 解決後に同じreview dirへ再投入し、コメント履歴と添付画像が残る。
5. 元ファイルのhashが変わらず、選択した改訂形式の構造検証と全ページ画像QAが通る。

## 必須依存

- PNG化とPDF出力: LibreOffice (`soffice`) と Poppler (`pdftoppm`, `pdfinfo`)
- PPTX編集: platform標準の `document-skills:pptx`

開始時に依存を確認する。PPTX skillがない環境ではレビューとコメント返信までに留め、改訂機能が使えないことを明示する。

## English workflow

For PPTX input, ask for a PPTX or PDF final output when unspecified; for PDF input, always return PDF. Run `build-pptx-review --final-format ...` or `build-pdf-review`, then `preview` and `watch-comments`. A click creates a point annotation and a drag creates a rectangle. Reply with `add-reply`, optionally attaching proposal images. Apply only resolved feedback, validate the selected final format, rebuild the same review directory with `--continue-review`, and call `notify-update`. Never overwrite the source.
