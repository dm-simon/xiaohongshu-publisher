# Automation Notes

## Scope

This skill is optimized for Xiaohongshu image notes published from the macOS web creator flow in Chrome with the bundled extension loaded from `assets/chrome-extension/`.

## Package Schema

Minimum fields:

```json
{
  "title": "Note title",
  "body": "Paragraph one\n\nParagraph two",
  "hashtags": ["TagA", "TagB"],
  "image_pages": [
    {
      "heading": "Page title",
      "bullets": ["Point 1", "Point 2"],
      "footer": "Optional footer"
    }
  ]
}
```

Optional fields:

- `topic`
- `cover.title`
- `cover.subtitle`
- `images` if images are prepared outside the renderer

## Publishing Assumptions

- The user is already logged into `https://creator.xiaohongshu.com/`.
- The account is allowed to publish image notes.
- The bundled Chrome extension is loaded in developer mode.
- Chrome allows JavaScript from Apple Events.
- The active publish tab has been refreshed after the extension was loaded or reloaded.

## Installation Checklist

1. Load `assets/chrome-extension/` from `chrome://extensions`.
2. Refresh the creator page.
3. Run:

```bash
python3 scripts/check_extension_bridge.py
```

4. Confirm the output reports `bridge_ready: true`.

## Failure Modes

- The creator page layout changes and text-based selectors no longer match.
- The Chrome extension is missing, disabled, or cannot attach the debugger.
- A login or safety prompt interrupts publishing.
- The account is rate-limited or temporarily blocked by the platform.

## Agent Behavior

- Keep generated copy and images even on publish failure.
- Prefer `draft` mode unless the user explicitly asked to post live.
- Tell the user exactly whether failure happened during upload, field filling, or final submit.

## Diagnostics

Use `scripts/check_extension_bridge.py` to confirm the script is reading the same creator tab that has the extension loaded.

Use `scripts/publish_note.py` output fields to isolate the failing phase:

- `mode_switch` for `上传图文`
- `upload_result` for image injection
- `fill_result` for title/body
- `action_result` for final click
