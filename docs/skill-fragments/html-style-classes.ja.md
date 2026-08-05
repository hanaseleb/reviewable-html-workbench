## html block で使える表現部品

同梱の `style.css` には、`html` block 内でそのまま使える表現 class が実装済みである。比較・評価・推奨・決定がある内容では、素の `<table>` / `<p>` で終えず、該当する部品を選ぶ。

| 用途 | class | 書き方 |
|---|---|---|
| 表番号 + 表題 | `table-wrap` / `table-cap` / `t-no` / `t-title` / `table-scroll` | `<figure class="table-wrap"><figcaption class="table-cap"><span class="t-no">表 1</span><span class="t-title">3 案の比較</span></figcaption><div class="table-scroll"><table>…</table></div></figure>` |
| 表ヘッダの補助説明 | `axis-sub` | `<th scope="col">実装量<span class="axis-sub">行数の目安</span></th>` |
| 5 段階評価 | `rate` + `good`/`mid`/`low` + `r1`〜`r5` + `pips` / `pip` | `<span class="rate good r4"><span class="pips"><i class="pip"></i><i class="pip"></i><i class="pip"></i><i class="pip"></i><i class="pip"></i></span>容易</span>` (pip は常に 5 個。`rN` が塗る数、`good`/`mid`/`low` が色) |
| 可否・対応状況 | `tag-yes` / `tag-no` / `tag-cell-note` | `<td><span class="tag-yes">対応</span><span class="tag-cell-note">v2.0 以降</span></td>` |
| 桁揃え数値 | `num` | `<td><span class="num">1,024</span></td>` (表中の数値列に使う) |
| 推奨パネル | `reco` / `reco-tag` | `<div class="reco"><span class="reco-tag">推奨</span><p>案 B を採る。理由は…</p></div>` |
| 決定の枠囲み | `decision-panel` | `<div class="decision-panel"><p>…</p></div>` |
| コード内の着色 (新規は language-* 既定) | `language-*` (自動) / 互換の `tok-k` / `tok-f` / `tok-s` / `tok-c` / `tok-n` | 新規: `<pre><code class="language-python">def main():</code></pre>`。手動着色 (互換): `<pre><code><span class="tok-k">def</span> …</code></pre>`。同梱 highlight.js が `language-*` を自動着色する。`tok-*` を含む code / `pre.diff` / `.nohighlight` は自動着色しない |
| コード差分 | `pre.diff` + `.add` / `.del` / `.ctx` | `<pre class="diff"><span class="ctx"> context</span><span class="del">removed</span><span class="add">added</span></pre>`。変更理由を散文で説明してから、必要な断片だけ示す |
| 用語集 | `dl.glossary` | `<dl class="glossary"><dt>用語</dt><dd>定義</dd></dl>`。文書冒頭の `html` block に置く。専門用語は本文で使う前に 1〜2 文で定義し、前提用語が多い文書は用語集を置く |

### 多軸の比較表 (`table.cmp`)

軸が 3 つ以上ある比較、または行数が多くて横スクロールが要る比較には `<table class="cmp">` を使う。通常の `<table>` と違い、ヘッダ行と最初の列 (比較軸) がスクロール中も固定され、推奨案の列を緑で浮かせられる。

| class | 効果 |
|---|---|
| `cmp` (table に付ける) | 比較表本体。`thead th` が sticky ヘッダになる。最小幅 720px のため `table-scroll` の中に入れる |
| `axis` (最初の列の `th` / `td` に付ける) | 比較軸の列が横スクロール中も左端に残る |
| `pick` (`<col>` / `th` / `td` に付ける) | 推奨する案の列を緑系で強調する。`<colgroup><col><col class="pick"></colgroup>` で列単位、または個別セルに付ける |

```html
<figure class="table-wrap">
  <figcaption class="table-cap"><span class="t-no">表 1</span><span class="t-title">3 案の比較</span></figcaption>
  <div class="table-scroll">
    <table class="cmp">
      <colgroup><col><col><col class="pick"><col></colgroup>
      <thead><tr>
        <th scope="col" class="axis">評価軸</th>
        <th scope="col">案 A</th><th scope="col" class="pick">案 B</th><th scope="col">案 C</th>
      </tr></thead>
      <tbody>
        <tr><th scope="row" class="axis">実装量<span class="axis-sub">行数の目安</span></th>
            <td><span class="num">40</span></td><td class="pick"><span class="num">180</span></td><td><span class="num">920</span></td></tr>
      </tbody>
    </table>
  </div>
</figure>
```

軸が 2 つだけ、または行が少なく横スクロールが不要な表では、`cmp` を使わず素の `<table>` にする。sticky と最小幅は狭い表では邪魔になる。

使い分けの基準:

- 比較表には `table-wrap` + `table-cap` で番号と表題を付ける。本文からの参照は「表 1」で行う。
- 軸が 3 つ以上あるなら `table.cmp` + `axis` を使い、推奨案の列に `pick` を付ける。
- 評価軸 (容易さ・成熟度・リスク等) は文字だけでなく `rate` の点表示でも符号化する。
- 推奨・決定は本文の段落に埋めず、`reco` または `decision-panel` で独立させる。
- 段落を文字の大きさで強調しない。強調したい段落があるなら、それは推奨・決定・注意のいずれかなので、`reco` / `decision-panel` / `callout` block のうち内容に合うものを使う。文書全体の導入は `metadata.deck` が担うので、節ごとに導入段落を作らない。
- これらは class 指定だけで効く。`style` 属性の直書きで同等の見た目を再実装しない。
- 色は `metadata.palette` の `brand` / `brand_soft` だけ主題に合わせて上書きできる。コントラスト比は `check-model` / `render` / `validate` が WCAG 4.5:1 で検査し、不足すると error で止まる (brand は最も薄い地色との比、brand_soft は本文色との比、両方指定時は 2 色の相互比も見る)。
