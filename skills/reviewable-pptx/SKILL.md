---
name: reviewable-pptx
description: |
  Convert PPTX presentations into slide-by-slide reviewable HTML previews, discuss browser comments in the same threads, attach visual proposal images to agent replies, and produce a validated revised PPTX after feedback is resolved. Use whenever a user provides a .pptx and asks to review slides, comment on a deck, discuss presentation changes, receive visual feedback, or revise a PowerPoint from review comments. Triggers: PPTXをレビュー, スライドにコメント, PowerPointを確認, コメントを反映してPPTXを修正, review this PPTX, review this deck, comment on these slides, revise the presentation from comments. 使用しない場面: PPTXを伴わない通常のHTML文書レビュー、計画だけのプレビュー。
---

# Reviewable PPTX

PPTXをスライド画像としてレビューし、コメントへの回答・視覚案・最終PPTXまで同じスレッドで扱う。

## 原則

- 元PPTXを上書きしない。最終成果物は `<stem>-revised.pptx` とする。
- コメント未解決の間は本番PPTXを変更しない。提案画像は一時コピーから生成する。
- PPTX編集は実行環境の標準PPTX skill/toolingを使う。このpluginへ外部skillのコードを複製しない。
- スライドのコメント対応は `document-model.json` の `metadata.pptx.slides` で `block_id` とページ番号を対応づける。
- 日本語依頼には日本語、英語依頼には英語で返信する。

## 言語方針 / Language behavior

Follow the language of the latest user request for progress updates, preview handoff text, comment replies, and final responses. 元のPPTX本文は、明示的に翻訳を求められない限り翻訳しない。

## 1. レビューを開始する

renderer repo rootを作業ディレクトリにして実行する。現在のチャットやworkspaceのcwdをrepo rootとして扱わない。

```bash
python3 -m scripts.html_review_workbench.cli build-pptx-review \
  --input <absolute-input.pptx> \
  --output <absolute-review-dir> \
  --lang ja

python3 -m scripts.html_review_workbench.cli preview \
  --root <absolute-review-dir> \
  --mode local
```

返却JSONの `url` と `stop_command` をユーザーへ渡す。preview起動後は `watch-comments --root <absolute-review-dir>` を監視として開始する。別端末からの閲覧が明示された場合だけ `--mode tailscale` を使い、tailnet内で資料を閲覧できる範囲をユーザーへ伝える。

## 2. コメントへ回答する

コメント更新を検知したら `ingest-review` を実行し、`needs_agent_review` の全スレッドへ `add-reply` で回答する。

```bash
python3 -m scripts.html_review_workbench.cli ingest-review --root <absolute-review-dir>
python3 -m scripts.html_review_workbench.cli add-reply \
  --root <absolute-review-dir> \
  --thread-id <thread-id> \
  --kind answer \
  --body "<回答>"
```

視覚案が理解を早める場合は、元PPTXの一時コピーへ提案を適用してPNG化し、返信へ添付する。画像だけで結論を伝えず、本文にも変更点を書く。

```bash
python3 -m scripts.html_review_workbench.cli add-reply \
  --root <absolute-review-dir> \
  --thread-id <thread-id> \
  --kind answer \
  --body "<提案内容>" \
  --image <absolute-proposal-slide.png> \
  --image-alt "<提案後のスライド説明>"
```

確認が必要なら `--kind clarification_request` を使う。ユーザーが返信するとスレッドは再び `needs_agent_review` になるため、合意まで同じ場所で続ける。

## 3. 最終PPTXへ反映する

1. `check-gates --require-resolved` で全コメントがユーザー合意済みであることを確認する。終了コード1なら変更しない。
2. `resolved` のコメントだけを元PPTXのコピーへ反映する。
3. 標準PPTX skillの手順で内容抽出、OOXML構造検証、全スライド画像QAを行う。
4. 改訂版を同じreview dirへ再投入する。既存document IDとコメント履歴は保持される。
5. `notify-update` でブラウザへ更新を知らせる。

```bash
python3 -m scripts.html_review_workbench.cli check-gates \
  --root <absolute-review-dir> \
  --require-resolved
```

```bash
python3 -m scripts.html_review_workbench.cli build-pptx-review \
  --input <absolute-revised.pptx> \
  --output <absolute-review-dir> \
  --lang ja \
  --continue-review

python3 -m scripts.html_review_workbench.cli notify-update \
  --root <absolute-review-dir> \
  --message "PPTXを更新しました"
```

最終応答には改訂版PPTXのパス、反映したコメント、未反映コメント、検証結果を含める。

## 実シナリオ検証

リリース前に実PPTXで次を確認する。

1. 全スライドがPNG化され、レビュー画面で欠けずに表示される。
2. ブラウザでコメントし、`ingest-review` が同じスライドIDを返す。
3. `add-reply --image` の本文と画像が同じスレッドに表示される。
4. コメントを解決して改訂版を同じreview dirへ再投入し、コメント履歴と添付画像が残る。
5. 元PPTXのhashが変わらず、改訂版PPTXの構造検証と全スライド画像QAが通る。

## 必須依存

- PNG化: LibreOffice (`soffice`) と Poppler (`pdftoppm`)
- 改訂版PPTX作成: platform標準のPPTX skill。Claude Code/Codex環境では `document-skills:pptx` を使う。

開始時に3点を確認する。PPTX skillがない環境ではレビューとコメント返信までに留め、改訂機能が使えないことをユーザーへ明示する。

## English workflow

Run `build-pptx-review`, start `preview`, and monitor `watch-comments`. Reply to every `needs_agent_review` thread with `add-reply`. Attach a rendered proposal slide with `--image` when visual feedback is useful. Apply only resolved feedback to a new `<stem>-revised.pptx`, validate it with the platform PPTX tooling, rebuild the same review directory, and call `notify-update`. Never overwrite the source deck.
