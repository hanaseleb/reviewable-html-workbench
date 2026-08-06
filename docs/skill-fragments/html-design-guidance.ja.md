## 表現の質の指針

見た目の判断に迷った時は、次の 4 つに従う。ユーザーが見た目の方向を明示した場合は、その指定が常に優先する。

1. **AI が作りがちな見た目を避ける。** 次の定番の組み合わせは、指定が無い限り選ばない: cream 地 (#F4F1EA) + serif 見出し + terracotta accent / near-black 地 + acid-green や vermilion の一点差し / 絵文字を節の目印にする / 全要素センタリング / 一様な大きい角丸 / 角丸カードの左端 accent バー。
2. **構造装飾は内容の事実を符号化する。** 01 / 02 / 03 のような番号は、内容が本当に順序を持つ時 (手順・時系列) だけ使う。区切り線・eyebrow・ラベルも、内容の区分を実際に表す時だけ入れ、装飾目的では入れない。
3. **読む文書と操作する画面で作法を変える。** 一覧・ダッシュボード的な内容は上から順に読まれず走査される。要約を詳細より先に置き、状態は数値だけでなく形 (rate の点、tag-yes の色、callout の左帯) でも符号化して、注意が要る箇所が一目で分かるようにする。
4. **余白は layout で作る。** 兄弟要素の間隔は `gap` を持つ flex / grid で作り、要素ごとの margin を積まない。幅の広い表・コード・図は自前の `overflow-x: auto` コンテナ (表は `table-scroll`) に入れ、ページ全体を横スクロールさせない。

## 図と手順の表現指針

- **原典図の引用優先。** 原典に重要な図がある場合は出所を明示して引用し、模倣図を作らない。
- **矢印文字・絵文字を図記号にしない。** 図が要るなら Mermaid diagram block か inline SVG を使う。
- **直列手順をフローチャート化しない。** 単純な直列手順は番号付きリストで表現する。
- **Mermaid の `mindmap` を使わない。** mindmap は日本語などの CJK ラベルで箱の採寸を誤り、文字が箱からはみ出し・重なって崩れる (2026-08-06 実測)。放射状の分類は `flowchart` の中心ノード + 枝で表現する。
- **inline SVG の色は theme に追従させる。** 紙面に直接乗る文字・線 (軸ラベル・行列の見出し・凡例の説明文・座標軸・区切り線) は `fill="currentColor"` / `stroke="currentColor"` で書き、`#333` のような固定色を直書きしない。固定色は light theme でしか読めず、dark theme では紙面と同化して消える。塗りつぶした図形 (rect / path) 自体の色と、その塗りの上に重ねる文字は、両 theme で読める固定色でよい。

## 印刷と PDF

ブラウザの印刷ダイアログ (`@media print`) で topbar / toc / comment rail 等の操作 UI が消え、横スクロールしていた表・コードは折り返して全内容が残る。PDF 化が必要な時だけ `python3 -m scripts.html_review_workbench.cli export-pdf --root <output-dir> [--output <pdf-path>]` を実行する (headless Chrome 必須。不在時は error JSON)。preview URL の提示が既定であり、ユーザーが PDF を明示依頼した時だけ export-pdf する。
