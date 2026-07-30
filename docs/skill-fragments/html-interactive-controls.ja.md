## 操作部品 (触って試す / 触った結果を作業へ戻す)

読むだけでなく触って決める資料では、`html` block に操作部品を直接書ける。値を試すスライダー、切り替えのトグル、並べ替えできるカードなどが対象。

### 書ける範囲

- `html` block の中に `<script>` を inline で書ける。`onclick=` 等の inline event handler も使える。
- 外部 host からの読み込みは `check-model` が error にする (`<script src="…">` と `<link rel="stylesheet" href="https://…">` の両方)。bundle が手元で完結する性質を保つため。図表の描画ライブラリが要る場合は Mermaid の `diagram` block を使う。
- 部品の見た目は既存の class (`rate` / `tag-yes` / `num` 等) と揃える。inline `style` の直書きは最小限にする。

### 触った結果を保存する

同梱の `RHWState` を使う。preview server があれば `PUT /annotations/state/<name>.json` で保存し、端末をまたいで同じ状態を見せる。server が無い場合 (publish した standalone、`file://` で開いた場合) は localStorage に落ち、どちらも使えない環境ではメモリ上だけで動く。操作そのものは止まらない。

```html
<label>duration <input type="range" id="dur" min="0" max="2000" value="300"></label>
<output id="durOut">300</output>ms
<script>
  (async function () {
    var dur = document.getElementById("dur");
    var out = document.getElementById("durOut");
    // 保存済みの値があれば復元する
    var saved = await window.RHWState.load("tuning");
    if (saved && saved.duration) { dur.value = saved.duration; out.textContent = saved.duration; }
    dur.addEventListener("input", function () {
      out.textContent = dur.value;
      // 動かしている間の表示更新と一緒に呼んでよい。debounce が server への PUT をまとめる
      window.RHWState.save("tuning", { duration: dur.value }, { debounce: 300 });
    });
  })();
</script>
```

`<name>` は英数字とハイフン・アンダースコアだけ (最大 64 文字)。保存した内容は agent が `annotations/state/<name>.json` として読める。触って決めた結果を作業へ戻す経路がこれになる。文書の中で用途ごとに名前を分ける (`tuning` / `priority-order` など)。

連続して動く部品 (スライダー、テキスト入力) では `{ debounce: 300 }` を渡す。手元の保存 (localStorage) は毎回すぐ行い、server への書き込みだけを入力が止まってから 1 回にまとめる。これを渡さずに `input` で呼ぶと、つまみを端から端まで動かすだけで PUT が 100 回以上飛ぶ。

逆に `debounce` を渡さないのは、操作が 1 回で完結する部品 (ボタン、`dragend`、チェックボックス) のとき。その場で保存され、戻り値の `saved` が `remote` / `local` / `memory` のどれかになる。

`debounce` 付きで待っている間の戻り値は `superseded` になる (新しい値で予約が取り直された、という意味)。最後の呼び出しだけが実際の保存結果を返す。画面に保存状態を出す場合は `superseded` を「保存中」として扱う。

### 使う判断

- 値の範囲を試したい、順序を決めたい、選択肢を絞りたい場面で使う。読んで終わる資料には入れない。
- 操作した結果を agent が受け取る必要があるなら `RHWState.save()` を必ず呼ぶ。呼ばないと結果は画面上だけで消える。
- 操作部品を入れた資料は、`preview` で server 越しに開いて動作を確認する。`file://` で開くと状態が端末間で共有されない状態の確認になる。
