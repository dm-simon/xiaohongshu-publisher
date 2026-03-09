# Xiaohongshu Publisher Skill

A Codex skill for generating and publishing Xiaohongshu image-note posts on macOS.

It can:

- write Xiaohongshu-style copy from a topic
- render cover and detail images locally
- switch the creator page into `上传图文`
- upload images through a bundled Chrome extension
- fill title and body
- publish live or save as draft

## Requirements

- macOS
- Google Chrome
- a logged-in Xiaohongshu creator account at `https://creator.xiaohongshu.com/`
- Python 3 with Pillow installed
- Chrome setting `View -> Developer -> Allow JavaScript from Apple Events` enabled

## Install

### Install as a Codex skill from this repo

If you use Codex skill installation from a GitHub repo path, point it at this repository.

The repo root is already the skill root and contains `SKILL.md`.

### Manual install

Clone or copy this repository into your Codex skills directory as:

```bash
$CODEX_HOME/skills/xiaohongshu-publisher
```

Typical local path example:

```bash
~/.codex/skills/xiaohongshu-publisher
```

## Chrome extension setup

This skill ships with a local extension under `assets/chrome-extension/`.

1. Open `chrome://extensions`
2. Enable `Developer mode`
3. Click `Load unpacked`
4. Select `assets/chrome-extension/`
5. Refresh the Xiaohongshu creator tab

Run this diagnostic before first publish:

```bash
python3 scripts/check_extension_bridge.py
```

Expected output:

```json
{
  "bridge_ready": true
}
```

## Usage

Prompt Codex with:

```text
Use $xiaohongshu-publisher to write and publish a Xiaohongshu image note about 如何快速学习AI.
```

Or run the scripts directly.

Render images:

```bash
python3 scripts/render_note_images.py ./xhs-output/topic/post.json --outdir ./xhs-output/topic/images
```

Publish live:

```bash
python3 scripts/publish_note.py ./xhs-output/topic/post.json --image-dir ./xhs-output/topic/images --mode publish
```

Save draft:

```bash
python3 scripts/publish_note.py ./xhs-output/topic/post.json --image-dir ./xhs-output/topic/images --mode draft
```

## Repository layout

- `SKILL.md`: Codex skill instructions
- `agents/openai.yaml`: skill UI metadata
- `scripts/`: renderer, publisher, diagnostics
- `assets/chrome-extension/`: bundled Chrome extension used for upload
- `references/`: extra operational notes

## Troubleshooting

- If the bridge check reports `bridge_ready: false`, reload the extension and refresh the creator page.
- If images upload but publishing stops on the page, inspect `action_result` from `scripts/publish_note.py`.
- If generated images show garbled Chinese text, verify the macOS Chinese system fonts are available.

## Notes

- This skill currently targets Xiaohongshu image-note posts, not video posts.
- The bundled automation depends on the current creator-page structure and may need selector updates if Xiaohongshu changes the page.
