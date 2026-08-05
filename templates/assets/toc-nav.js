/* 目次の移動と現在位置ハイライト。
 *
 * preview では review-comments.js が同じ処理を持つが、公開用 standalone にはその JS が
 * 入らないため、目次が「リンクは飛ぶがハイライトが動かない」状態になる。読み物として
 * 必要な部分だけを切り出したのがこの file で、公開出力にだけ inline される。
 *
 * preview (canvas がスクロールコンテナ) と standalone (window がスクロール) の両方で
 * 動くよう、スクロール対象を実行時に判定する。
 */
(function () {
  "use strict";

  // 目次から飛んだとき、見出しを可視領域の上端から何 px 下に止めるか。
  // review-comments.js の TOC_JUMP_OFFSET と同じ値にする。
  var JUMP_OFFSET = 28;
  // 現在位置とみなす判定線 (可視領域上端からの距離)。JUMP_OFFSET より少し下に置き、
  // 飛んだ直後にその節が現在位置として光るようにする。
  var CURRENT_LINE = 48;

  function scrollTarget() {
    var canvas = document.querySelector(".canvas");
    if (canvas && canvas.scrollHeight > canvas.clientHeight + 1) {
      return canvas;
    }
    return document.scrollingElement || document.documentElement;
  }

  function viewportTop(target) {
    if (target === document.scrollingElement || target === document.documentElement) {
      return 0;
    }
    return target.getBoundingClientRect().top;
  }

  function rafThrottle(callback) {
    var ticking = false;
    return function () {
      if (ticking) {
        return;
      }
      ticking = true;
      window.requestAnimationFrame(function () {
        ticking = false;
        callback();
      });
    };
  }

  function init() {
    var toc = document.querySelector(".toc");
    if (!toc) {
      return;
    }
    var links = Array.prototype.slice.call(toc.querySelectorAll("a[href^='#']"));
    if (!links.length) {
      return;
    }
    // 目次のリンク先は block の id。見出し要素には id が付かない
    var blocks = Array.prototype.slice.call(document.querySelectorAll(".prose .review-block[id]"));

    links.forEach(function (link) {
      link.addEventListener("click", function (event) {
        event.preventDefault();
        var id = link.getAttribute("href").slice(1);
        var block = document.getElementById(id);
        if (!block) {
          return;
        }
        // block の上端ではなく見出しそのものを基準にする。block の上余白は種類ごとに違い、
        // 上端合わせだと見出しの止まる位置が節ごとにばらつく
        var heading = block.querySelector(":scope > h2, :scope > h3, :scope > h4") || block;
        var target = scrollTarget();
        target.scrollTop += heading.getBoundingClientRect().top - viewportTop(target) - JUMP_OFFSET;
      });
    });

    var update = rafThrottle(function () {
      var top = viewportTop(scrollTarget());
      var current = null;
      for (var i = 0; i < blocks.length; i++) {
        if (blocks[i].getBoundingClientRect().top <= top + CURRENT_LINE) {
          current = blocks[i];
        }
      }
      links.forEach(function (link) {
        link.classList.remove("current");
      });
      if (!current) {
        return;
      }
      for (var j = 0; j < links.length; j++) {
        if (links[j].getAttribute("href") === "#" + current.id) {
          links[j].classList.add("current");
          return;
        }
      }
    });

    window.addEventListener("scroll", update, true);
    window.addEventListener("resize", update);
    update();

    // 目次が長いとき、目次の中だけをスクロールさせる (本文を巻き込まない)
    var list = toc.querySelector("ol.toc-list");
    if (list) {
      list.addEventListener(
        "wheel",
        function (event) {
          var maxScroll = list.scrollHeight - list.clientHeight;
          if (maxScroll <= 0) {
            return;
          }
          var atTop = list.scrollTop <= 0 && event.deltaY < 0;
          var atBottom = list.scrollTop >= maxScroll && event.deltaY > 0;
          if (!atTop && !atBottom) {
            event.preventDefault();
            list.scrollTop += event.deltaY;
          }
        },
        { passive: false }
      );
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
