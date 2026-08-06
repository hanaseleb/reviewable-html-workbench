from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReviewCommentsJavaScriptTest(unittest.TestCase):
    def test_review_comments_js_keeps_hardening_boundaries_visible(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        publish_script = (ROOT / "templates/assets/publish-export.js").read_text(encoding="utf-8")

        for function_name in [
            "loadComments",
            "saveComments",
            "scheduleSelectionCapture",
            "shouldIgnoreSelectionCaptureEvent",
            "selectionAnchorInBlock",
            "captureImageBlockClick",
            "clearDocumentSelectionForNonTextTarget",
            "reviewBlockForRange",
            "renderCommentCards",
            "positionCards",
            "scrollActiveCardIntoView",
            "initCommentRailScroll",
            "resolveHighlightOffsets",
            "findBestOccurrence",
            "activate",
            "initPublishToggle",
            "initPanelToggles",
            "keepReadingPosition",
            "setPublished",
            "threadCardState",
            "normalizeThreadStatus",
            "showSaveError",
        ]:
            self.assertIn(f"function {function_name}", script)

        for function_name in [
            "buildPublishedDoc",
            "collectMermaidScripts",
            "fetchAssetText",
            "downloadPublishedDoc",
        ]:
            self.assertIn(f"function {function_name}", publish_script)

    def test_line_selection_uses_deferred_capture_and_range_endpoint_fallback(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")

        self.assertIn('document.addEventListener("pointerup", scheduleSelectionCapture)', script)
        self.assertIn("shouldIgnoreSelectionCaptureEvent(event)", script)
        self.assertIn("ui.root.contains(event.target)", script)
        self.assertIn('.cx[data-comment], [data-comment-badge]', script)
        self.assertIn("window.setTimeout(captureSelection, 0)", script)
        self.assertIn("closestReviewBlock(range.startContainer)", script)
        self.assertIn("closestReviewBlock(range.endContainer)", script)

    def test_image_block_click_creates_commentable_selection(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")

        self.assertIn('event.target.closest?.(".generated-image img")', script)
        self.assertIn("clearDocumentSelectionForNonTextTarget()", script)
        self.assertIn('selectedText: image.getAttribute("alt")', script)
        self.assertIn("image.getBoundingClientRect()", script)

    def test_comment_click_links_highlight_and_margin_card(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")

        self.assertIn('className = "cx"', script)
        self.assertIn('highlight.dataset.comment = thread.id || ""', script)
        self.assertIn('highlight.dataset.state = threadCardState(thread)', script)
        self.assertIn('card.className = "cmt"', script)
        self.assertIn('card.dataset.cstate = cardState', script)
        self.assertIn('card.dataset.for = thread.id || ""', script)
        self.assertIn('document.querySelectorAll(".cx.is-active, .cmt.is-active")', script)

    def test_activation_reveals_card_in_rail_and_never_scrolls_the_document(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        activate_block = script[script.index("function activate") : script.index("function setActiveClasses")]
        reveal_block = script[script.index("function scrollActiveCardIntoView") : script.index("function schedulePositionCards")]

        # Scrolling the document (the body column) on activation is the bug we
        # removed; only the comment rail may scroll.
        self.assertNotIn("scrollIntoView", script)
        self.assertIn("setActiveClasses(commentId);", activate_block)
        self.assertIn("schedulePositionCards();", activate_block)
        self.assertIn("scrollActiveCardIntoView(commentId)", activate_block)
        self.assertIn('document.getElementById("cmtLayer")', reveal_block)
        self.assertIn("layer.scrollTo", reveal_block)
        self.assertNotIn("window.scroll", reveal_block)

    def test_position_cards_orders_by_anchor_without_absolute_layout(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        position_block = script[script.index("function positionCards") : script.index("function scrollActiveCardIntoView")]

        self.assertNotIn("layoutCardTops", script)
        self.assertNotIn("state.pin", script)
        self.assertIn('card.style.position = "";', position_block)
        self.assertIn('card.style.top = "";', position_block)
        self.assertIn("commentSelector(card.dataset.for)", position_block)
        self.assertIn("getBoundingClientRect().top", position_block)
        self.assertIn("layer.appendChild(card)", position_block)

    def test_comment_rail_scrolls_independently(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")

        self.assertIn("initCommentRailScroll();", script)
        rail_block = script[script.index("function initCommentRailScroll") : script.index("function activate")]

        self.assertIn('layer.addEventListener("wheel"', rail_block)
        self.assertIn("event.preventDefault();", rail_block)
        self.assertIn("layer.scrollTop += event.deltaY;", rail_block)

    def test_highlight_reanchors_selected_text_after_body_edits(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")

        for function_name in [
            "resolveHighlightOffsets",
            "findBestOccurrence",
            "commonPrefixLen",
            "commonSuffixLen",
            "blockAnchorText",
        ]:
            self.assertIn(f"function {function_name}", script)

        select_block = script[script.index("function highlightThreadSelection") : script.index("function highlightByOffsets")]
        resolve_block = script[script.index("function resolveHighlightOffsets") : script.index("function findBestOccurrence")]

        # Offsets are resolved against the current text before falling back.
        self.assertIn("resolveHighlightOffsets(block, thread)", select_block)
        self.assertIn("highlightByOffsets(block, thread, resolved.start, resolved.end, number)", select_block)
        # Stored offsets are trusted only while they still cover the selected text.
        self.assertIn("fullText.slice(anchor.start, anchor.end)", resolve_block)
        self.assertIn("findBestOccurrence(fullText, selected, thread.prefix, thread.suffix)", resolve_block)

    def test_filter_visibility_keeps_highlight_text_visible(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        filter_block = script[script.index("function applyFilterVisibility") : script.index("function shouldShowThreadByFilter")]

        self.assertIn('highlight.querySelectorAll(".cx-num").forEach((badge) => {', filter_block)
        self.assertIn("badge.hidden = !visible;", filter_block)
        self.assertNotIn("highlight.hidden = !visible;", filter_block)

    def test_review_comments_js_does_not_mix_ingestion_classification_into_ui_status(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        status_block = script[script.index("const COMMENT_STATUS") : script.index("const STATUS_VALUES")]

        for classification in ["actionable", "needs_clarification", "blocked", "already_addressed"]:
            self.assertNotIn(classification, status_block)

    def test_publish_preview_exports_clean_html_without_review_runtime(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        publish_script = (ROOT / "templates/assets/publish-export.js").read_text(encoding="utf-8")

        self.assertIn("initPublishToggle();", script)
        self.assertIn('document.body.classList.contains("is-published")', script)
        self.assertIn("window.reviewableWorkbenchPublish.downloadPublishedDoc({ toastMessage: t.publishToast });", script)
        self.assertIn('document.querySelector("#canvas .doc-shell")', publish_script)
        # 書き出しで外すのはレビュー用の表示だけ。目次は読み手のために残す
        for removed in (".cmt-rail", ".doc-status", ".byline", ".cx-num", ".review-comment-badges"):
            self.assertIn(removed, publish_script, f"{removed} を書き出しから外していない")
        self.assertNotIn('querySelectorAll(".toc,', publish_script)
        self.assertIn('clone.querySelector(".toc")', publish_script)
        self.assertIn('clone.querySelectorAll(".cx")', publish_script)
        self.assertIn('clone.querySelectorAll(".review-comment-highlight")', publish_script)
        self.assertIn('clone.querySelectorAll(".review-comment-badge")', publish_script)
        self.assertIn('"<body class=\\"is-published\\">\\n"', publish_script)
        self.assertIn("const css = await collectCSS();", publish_script)
        self.assertIn('const publishOverrides = await fetchAssetText("assets/publish-overrides.css") || DEFAULT_PUBLISH_OVERRIDES;', publish_script)
        self.assertIn("const mermaidScripts = await collectMermaidScripts(clone);", publish_script)
        self.assertIn('toast((options && options.toastMessage) || "Published HTML exported");', publish_script)

    def test_build_published_doc_inlines_diagram_zoom_script(self) -> None:
        script = (ROOT / "templates/assets/publish-export.js").read_text(encoding="utf-8")
        publish_block = script[script.index("async function collectMermaidScripts") : script.index("async function buildPublishedDoc")]

        self.assertIn('clone.querySelector(".mermaid")', publish_block)
        self.assertIn('fetchAssetText("assets/mermaid.min.js")', publish_block)
        self.assertIn('fetchAssetText("assets/diagram-zoom.js")', publish_block)
        self.assertIn('document.querySelector(\'script[data-role="reviewable-mermaid-init"]\')', script)
        self.assertIn("MERMAID_INIT_JS", script)
        self.assertIn("mermaidScripts +", script)

    def test_publish_export_warns_when_toc_script_is_missing(self) -> None:
        """asset を取れないまま黙って書き出すと、目次が光らない HTML が公開まで気づかれない。

        判定基準の出所: 同じ状況で CLI 側の publish.py:_inline_toc_nav_script が repo の
        template から補う実装になっていること (ブラウザ側は fetch できないので補えず、
        知らせるしかない)。2026-08-05 に、asset を持たない bundle が実在することを確認した。
        """
        script = (ROOT / "templates/assets/publish-export.js").read_text(encoding="utf-8")
        block = script[script.index('const tocNav = await fetchAssetText("assets/toc-nav.js")') :]
        block = block[: block.index("const html =")]

        self.assertIn("else", block)
        self.assertIn("toast(", block)

    def test_utility_bar_is_hidden_until_opened_from_toolbar(self) -> None:
        """Export/Import バーが常時表示に戻ると、rail 下部の返信欄と送信ボタンを覆って
        コメント操作ができなくなる。

        判定基準の出所: 2026-08-05 のユーザー報告 2 件 (返信入力とバーが重なった
        スクリーンショット。focus 連動の非表示でも未入力時の送信ボタンが覆われたままだった)
        と、その修正設計 (既定 hidden + topbar の JSON ボタンで開閉)。
        """
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        self.assertIn('"review-comments-utility" hidden', script)
        self.assertIn("initUtilityToggle", script)
        self.assertIn("jsonToggle", script)
        css = (ROOT / "templates/style.css").read_text(encoding="utf-8")
        self.assertIn(".review-comments-utility[hidden] { display: none; }", css)

    def test_card_click_scrolls_body_to_comment(self) -> None:
        """カードをクリックしても本文が動かず、コメントの対象箇所を目視で探すことになる。

        判定基準の出所: TASK-18 の決定事項 (カードクリックで本文ハイライトへスクロール、
        ハイライト無しは所属 block へ、視界の上 15%〜70% にあるなら動かさない)。
        """
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        # カードクリックの handler から呼ばれている (関数定義の存在だけでは通らない形で見る)
        self.assertIn("activate(thread.id, false);\n      scrollBodyToComment(thread);", script)
        fn = script[script.index("function scrollBodyToComment") :]
        fn = fn[: fn.index("\n  function ", 1)]
        self.assertIn("commentSelector(thread.id)", fn)
        self.assertIn("getElementById(thread.block_id)", fn)
        self.assertIn("viewHeight * 0.15", fn)
        self.assertIn("viewHeight * 0.7", fn)
        self.assertIn('behavior: "smooth"', fn)

    def test_column_widths_are_draggable_via_css_variables(self) -> None:
        """列幅のドラッグ変更が失われると、目次・コメント列の幅を読者が調整できない。
        変数化が崩れると保存済みの幅が layout に反映されず、既定幅に固定されたままになる。

        判定基準の出所: TASK-17 の決定事項 (列幅は CSS 変数 --toc-w / --rail-w に一本化し、
        ドラッグは変数の書き換えだけを行う。clamp は目次 160〜400 / コメント 240〜560)。
        """
        css = (ROOT / "templates/style.css").read_text(encoding="utf-8")
        self.assertIn("var(--toc-w, 232px) minmax(0, 1fr) var(--rail-w, 332px)", css)
        self.assertIn(".col-resizer", css)
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        self.assertIn("initColumnResizers", script)
        self.assertIn('{ key: "toc", varName: "--toc-w", host: ".toc", grow: 1, min: 160, max: 400 }', script)
        self.assertIn('{ key: "rail", varName: "--rail-w", host: ".cmt-rail", grow: -1, min: 240, max: 560 }', script)
        self.assertIn("COL_WIDTH_STORAGE_KEY", script)

    def test_comment_markdown_renders_quotes_and_emphasis(self) -> None:
        """agent 返信の > 引用や **強調** が記号のまま平文表示され、どこが引用で
        どこが発言か読み分けられない。

        判定基準の出所: 2026-08-05 のユーザー報告 (引用記号が生のまま並ぶ返信の
        スクリーンショットと「どこが引用か分からない」の指摘) と、その修正設計
        (escape を通した後に blockquote / strong / code だけへ変換する)。
        """
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        # 親コメントと返信の両方の表示に適用されている
        self.assertIn("renderCommentMarkdown(thread.comment", script)
        self.assertIn("renderCommentMarkdown(reply.body)", script)
        # 編集用 textarea は生テキストのまま (markdown HTML を混ぜない)
        self.assertIn("data-thread-comment-editor rows=\"3\" hidden>${escapeHtml(thread.comment", script)
        # escape が変換より先 (本文の HTML を script として解釈させない)
        fn = script[script.index("function renderInlineMarkdown") :]
        fn = fn[: fn.index("return s;")]
        self.assertLess(fn.index("escapeHtml"), fn.index("<code>"))
        self.assertLess(fn.index("escapeHtml"), fn.index("<strong>"))

    def test_published_i18n_keys_exist(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        ja_block = script[script.index("ja: {") : script.index("},\n    en: {")]
        en_block = script[script.index("en: {") : script.index("},\n  });")]

        for key in [
            "publishLabel",
            "publishActive",
            "publishTitle",
            "publishStandard",
            "publishMax",
            "publishDownload",
            "publishExit",
            "publishExitLabel",
            "publishToast",
        ]:
            self.assertIn(f"{key}:", ja_block)
            self.assertIn(f"{key}:", en_block)

    def test_published_escape_handler(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        start = script.index("function initPublishToggle()")
        publish_block = script[start : script.index("function setPublished", start)]

        self.assertIn('event.key === "Escape"', publish_block)
        self.assertIn("is-published", publish_block)

    def test_sse_functions_exist(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        for function_name in [
            "initEventSource",
            "fetchAndMergeComments",
            "mergeRemoteComments",
            "showUpdateBanner",
        ]:
            self.assertIn(f"function {function_name}", script)

    def test_sse_i18n_keys_exist(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        ja_block = script[script.index("ja: {") : script.index("},\n    en: {")]
        en_block = script[script.index("en: {") : script.index("},\n  });")]

        for key in ["agentReplied", "docUpdated", "reloadBtn", "closeBtn"]:
            self.assertIn(f"{key}:", ja_block, f"Missing ja i18n key: {key}")
            self.assertIn(f"{key}:", en_block, f"Missing en i18n key: {key}")

    def test_save_comments_surfaces_server_errors(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        save_block = script[script.index("async function saveComments") : script.index("function scheduleSelectionCapture")]
        ja_block = script[script.index("ja: {") : script.index("},\n    en: {")]
        en_block = script[script.index("en: {") : script.index("},\n  });")]

        self.assertIn("function showSaveError", script)
        self.assertIn("var body = await response.json();", save_block)
        self.assertIn("showSaveError(errorMessage);", save_block)
        self.assertIn("saveError:", ja_block)
        self.assertIn("saveError:", en_block)

    def test_event_source_initialized_after_load(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        load_block = script[script.index("loadComments().then") : script.index("function createUi")]

        self.assertIn("loadComments().then(function ()", load_block)
        self.assertIn("schedulePositionCards();", load_block)
        self.assertIn("initEventSource();", script)

    def test_event_source_opens_events_endpoint(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        init_block = script[script.index("function initEventSource()") : script.index("function fetchAndMergeComments")]

        self.assertIn('if (typeof EventSource === "undefined")', init_block)
        self.assertIn('var es = new EventSource("/events");', init_block)
        self.assertIn('es.addEventListener("comment_updated"', init_block)
        self.assertIn('es.addEventListener("document_updated"', init_block)

    def test_comment_updated_refreshes_remote_comments_except_browser_source(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        init_block = script[script.index("function initEventSource()") : script.index("function fetchAndMergeComments")]
        fetch_block = script[script.index("async function fetchAndMergeComments()") : script.index("function mergeRemoteComments")]

        self.assertIn("var data = JSON.parse(event.data);", init_block)
        self.assertIn('if (data.source === "browser")', init_block)
        self.assertIn("return;", init_block)
        self.assertIn("fetchAndMergeComments();", init_block)
        self.assertIn('fetch(COMMENTS_URL, { cache: "no-store" })', fetch_block)
        self.assertIn("mergeRemoteComments(payload);", fetch_block)

    def test_status_buttons_refresh_thread_without_full_document_rerender(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        resolve_block = script[
            script.index('card.querySelector("[data-thread-resolve]")') :
            script.index('card.querySelector("[data-thread-delete]")')
        ]
        status_block = script[script.index("async function updateThreadStatus") : script.index("function renderReplies")]

        self.assertIn("await updateThreadStatus(thread, COMMENT_STATUS.resolved);", resolve_block)
        self.assertIn("await updateThreadStatus(thread, COMMENT_STATUS.needsAgentReview);", resolve_block)
        self.assertNotIn("renderComments();", resolve_block)
        self.assertIn("await saveComments();", status_block)
        self.assertIn("refreshThreadDisplay(thread);", status_block)
        self.assertIn("function replaceCommentCard(thread)", status_block)
        self.assertIn("current.replaceWith(createCommentCard(thread, index + 1));", status_block)
        self.assertIn("function updateThreadAnchors(thread)", status_block)
        self.assertIn("element.dataset.state = threadCardState(thread);", status_block)
        self.assertIn("function updateBlockCommentState(blockId)", status_block)
        self.assertIn('block.classList.toggle("has-review-comments"', status_block)
        self.assertIn('block.classList.toggle("has-review-replies"', status_block)

    def test_remote_comment_merge_refreshes_existing_threads_without_full_document_rerender(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        merge_block = script[script.index("function mergeRemoteComments") : script.index("function showUpdateBanner")]

        self.assertIn("state.comments.comments.push(newThread);", merge_block)
        self.assertIn("old.replies = newThread.replies;", merge_block)
        self.assertIn("old.status = newThread.status;", merge_block)
        self.assertIn("var hasNewThread = false;", merge_block)
        self.assertIn("var changedExistingThreads = [];", merge_block)
        self.assertIn("var hasAgent = addedReplies.some", merge_block)
        self.assertIn("changed = true;", merge_block)
        self.assertIn("if (hasNewThread) {", merge_block)
        self.assertIn("renderComments();", merge_block)
        self.assertIn("changedExistingThreads.forEach(refreshThreadDisplay);", merge_block)
        self.assertIn("toast(t.agentReplied);", merge_block)
        self.assertNotIn("updateCardStatus(old.id, newThread)", merge_block)

    def test_document_updated_banner_requires_manual_reload(self) -> None:
        script = (ROOT / "templates/review-comments.js").read_text(encoding="utf-8")
        document_event_block = script[
            script.index('es.addEventListener("document_updated"') : script.index('es.addEventListener("error"')
        ]
        banner_block = script[script.index("function showUpdateBanner") :]

        self.assertIn("showUpdateBanner(message);", document_event_block)
        self.assertNotIn("window.location.reload()", document_event_block)
        self.assertIn('class="rub-reload"', banner_block)
        self.assertIn('banner.querySelector(".rub-reload").addEventListener("click"', banner_block)
        self.assertIn("window.location.reload();", banner_block)


if __name__ == "__main__":
    unittest.main()
