---
name: xiaohongshu-publisher
description: Generate, package, and publish Xiaohongshu image-note posts on macOS. Use when the user wants Codex to write Xiaohongshu-style copy, prepare cover/detail images for a topic, and optionally publish the post through the Xiaohongshu creator platform in Chrome. Typical triggers include requests like "write and post a Xiaohongshu note about ...", "generate a Xiaohongshu post with images", "publish this topic to Xiaohongshu", or "save a Xiaohongshu draft with title/body/hashtags and images".
---

# Xiaohongshu Publisher

Build a Xiaohongshu image-note package end to end: write the note, render matching images locally, and publish or save as draft through the creator site on macOS.

Default to image-note workflow. Do not assume video posting, scheduling, analytics, or comment automation unless the user explicitly asks and local tooling supports it.

## Workflow

1. Turn the user's request into a publishable package.
2. Render images with `scripts/render_note_images.py`.
3. Load the bundled Chrome extension once, then publish or save draft with `scripts/publish_note.py`.
4. Report output paths and any manual blockers.

## Setup Checklist

Complete this once per machine before first publish:

1. Use macOS with Google Chrome.
2. Log into `https://creator.xiaohongshu.com/`.
3. In Chrome, enable `View -> Developer -> Allow JavaScript from Apple Events`.
4. Open `chrome://extensions`, enable `Developer mode`, and load `assets/chrome-extension/` as an unpacked extension.
5. Refresh the Xiaohongshu creator tab after loading or reloading the extension.
6. Verify the bridge before publishing:

```bash
python3 scripts/check_extension_bridge.py
```

The bridge checker should report:

- `bridge_ready: true`
- a `href` under `https://creator.xiaohongshu.com/`

## Build The Content Package

Write the note in Xiaohongshu style:

- Strong opening hook in the first line.
- Short paragraphs and obvious scannability.
- Practical and specific advice over generic filler.
- Natural hashtags at the end, usually 5-10.
- Avoid exaggerated claims, medical/financial promises, or fake personal results.

Create a JSON package before rendering or publishing. Save it under a working directory such as `./xhs-output/<topic-slug>/post.json`.

Use this shape:

```json
{
  "topic": "How to learn AI fast",
  "title": "普通人快速学 AI，先别急着刷课",
  "body": "开头钩子\n\n正文段落 1\n\n正文段落 2",
  "hashtags": ["AI学习", "效率提升", "自我成长"],
  "cover": {
    "title": "快速学 AI",
    "subtitle": "先学能立刻用上的 3 件事"
  },
  "image_pages": [
    {
      "heading": "先学应用，不要先补全理论",
      "bullets": [
        "先让 AI 帮你写、搜、总结",
        "每天固定做 1 个真实任务",
        "把会用放在看懂前面"
      ],
      "footer": "先能用，再系统化"
    }
  ]
}
```

If the user asks only for copy, stop after creating the package. Otherwise continue automatically to rendering and publishing.

## Render Images

Run:

```bash
python3 scripts/render_note_images.py ./xhs-output/<topic-slug>/post.json --outdir ./xhs-output/<topic-slug>/images
```

The renderer creates:

- `cover.png`
- `page-01.png`, `page-02.png`, ...
- `manifest.json`

Prefer 1 cover plus 2-5 detail pages. Keep each page focused on one idea. If the package has too many bullets, split them across pages instead of crowding one image.

## Publish

Before first use, load the unpacked extension from `assets/chrome-extension/` in Chrome developer mode.

Steps:

1. Open `chrome://extensions`
2. Enable `Developer mode`
3. Click `Load unpacked`
4. Select `assets/chrome-extension/`

Quick diagnostic:

```bash
python3 scripts/check_extension_bridge.py
```

For full publish:

```bash
python3 scripts/publish_note.py ./xhs-output/<topic-slug>/post.json --image-dir ./xhs-output/<topic-slug>/images --mode publish
```

For safer default behavior when the user did not explicitly ask to go live:

```bash
python3 scripts/publish_note.py ./xhs-output/<topic-slug>/post.json --image-dir ./xhs-output/<topic-slug>/images --mode draft
```

Assumptions:

- macOS
- Google Chrome installed
- User already logged in at Xiaohongshu creator platform
- Chrome extension from `assets/chrome-extension/` is loaded
- Chrome menu `View -> Developer -> Allow JavaScript from Apple Events` is enabled

The publisher uses page heuristics to switch into `上传图文`, then uses the bundled extension to inject image files into the page's `input[type=file]` through Chrome debugger. It no longer depends on the macOS file picker.

Expected result from a successful run:

- `mode_switch.switched = true`
- `upload_result.ok = true`
- `fill_result.titleOk = true`
- `fill_result.bodyOk = true`
- `action_result.actionOk = true`

## Recovery Rules

If publish automation fails:

1. Keep the generated package and image paths.
2. Report the exact failing step.
3. Do not delete artifacts.
4. If possible, rerun with `--mode draft` before giving up.

## Resources

Read [automation-notes.md](./references/automation-notes.md) when you need the package schema, assumptions, or troubleshooting notes.
