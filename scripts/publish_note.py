#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List


DEFAULT_URL = "https://creator.xiaohongshu.com/publish/publish"
TARGET_HOST = "creator.xiaohongshu.com"


def run_osascript(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )


def load_package(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def collect_images(package: Dict, image_dir: Path = None) -> List[str]:
    if image_dir:
        images = sorted(str(path.resolve()) for path in image_dir.glob("*.png"))
        if images:
            return images

    images = []
    for item in package.get("images") or []:
        path = Path(item).expanduser().resolve()
        if path.exists():
            images.append(str(path))
    return images


def build_body_text(package: Dict) -> str:
    return package.get("body", "").strip()


def js_string(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def apple_string(value: str) -> str:
    compact = value.replace("\\", "\\\\").replace('"', '\\"')
    compact = compact.replace("\n", " ")
    return compact


def execute_js(js_code: str) -> str:
    script = f'''
tell application "Google Chrome"
  set targetTab to missing value
  repeat with wi from 1 to count windows
    set w to window wi
    repeat with ti from 1 to count tabs of w
      set t to tab ti of w
      if (URL of t contains "{TARGET_HOST}") then
        set active tab index of w to ti
        set index of w to 1
        set targetTab to t
        exit repeat
      end if
    end repeat
    if targetTab is not missing value then exit repeat
  end repeat
  if targetTab is missing value then error "No Xiaohongshu creator tab found"
  execute targetTab javascript "{apple_string(js_code)}"
end tell
'''.strip()
    result = run_osascript(script)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "Failed to execute JavaScript in Google Chrome.")
    return result.stdout.strip()


def build_select_graphic_mode_script() -> str:
    return r"""
(() => {
  const queryAll = (selector) => Array.from(document.querySelectorAll(selector));
  const isVisible = (el) => {
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  };
  const cleanText = (el) => (el.innerText || el.textContent || '').replace(/\s+/g, '').trim();
  const rankNode = (el) => {
    const text = cleanText(el);
    if (text === '上传图文') return 100;
    if (text === '图文') return 90;
    if (text === '图文笔记') return 80;
    if (text.includes('上传图文')) return 50 - Math.min(text.length, 40);
    if (text.includes('图文')) return 20 - Math.min(text.length, 20);
    return -999;
  };

  const candidates = queryAll('button, div, span, a, label')
    .filter((el) => isVisible(el))
    .map((el) => ({ el, text: cleanText(el), rank: rankNode(el) }))
    .filter((item) => item.rank > 0)
    .sort((a, b) => b.rank - a.rank || a.text.length - b.text.length);
  const target = candidates[0]?.el;

  if (target) {
    target.scrollIntoView({ block: 'center' });
    target.style.outline = '3px solid #ff2442';
    target.click();
    return JSON.stringify({ switched: true, text: cleanText(target) });
  }

  const imageInput = queryAll('input[type="file"]').find((el) => ((el.accept || '').toLowerCase().includes('image')));
  if (imageInput) {
    return JSON.stringify({ switched: true, text: 'image-input-already-present' });
  }

  return JSON.stringify({ switched: false, text: 'graphic-mode-not-found' });
})();
""".strip()


def build_prepare_upload_script() -> str:
    return r"""
(() => {
  const queryAll = (selector) => Array.from(document.querySelectorAll(selector));
  const cleanText = (el) => (el.innerText || el.textContent || '').replace(/\s+/g, '').trim();
  const isVisible = (el) => {
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  };
  const rankNode = (el) => {
    const text = cleanText(el);
    if (text === '上传图片') return 100;
    if (text === '选择图片') return 95;
    if (text === '点击上传') return 90;
    if (text.includes('上传图片')) return 60 - Math.min(text.length, 20);
    if (text.includes('选择图片')) return 55 - Math.min(text.length, 20);
    if (text.includes('点击上传')) return 50 - Math.min(text.length, 20);
    return -999;
  };

  const trigger = queryAll('button, div, span, label, a')
    .filter((el) => isVisible(el))
    .map((el) => ({ el, text: cleanText(el), rank: rankNode(el) }))
    .filter((item) => item.rank > 0)
    .sort((a, b) => b.rank - a.rank || a.text.length - b.text.length)[0];

  if (trigger) {
    trigger.el.scrollIntoView({ block: 'center' });
    trigger.el.style.outline = '3px solid #ff2442';
  }

  return JSON.stringify({
    ready: true,
    trigger: trigger ? trigger.text : null,
    selectors: [
      'input[type="file"][accept*="image"]',
      'input[type="file"]'
    ]
  });
})();
""".strip()


def build_extension_upload_script(files: List[str], selectors: List[str]) -> str:
    return f"""
(() => {{
  const root = document.documentElement;
  if (root.dataset.codexXhsBridgeReady !== '1') {{
    return JSON.stringify({{ ok: false, step: 'bridge', error: 'Codex Xiaohongshu extension bridge not found' }});
  }}
  root.dataset.codexXhsUploadResult = '';
  root.dataset.codexXhsUploadPayload = JSON.stringify({{
    files: {js_string(files)},
    selectors: {js_string(selectors)}
  }});
  document.dispatchEvent(new CustomEvent('codex-xhs-upload'));
  return JSON.stringify({{ ok: true, step: 'dispatch' }});
}})();
""".strip()


def build_read_upload_result_script() -> str:
    return r"""
(() => {
  const root = document.documentElement;
  if (root.dataset.codexXhsBridgeReady !== '1') {
    return JSON.stringify({ ok: false, step: 'bridge', error: 'Codex Xiaohongshu extension bridge not found' });
  }
  if (!root.dataset.codexXhsUploadResult) {
    return '';
  }
  return root.dataset.codexXhsUploadResult;
})();
""".strip()


def build_fill_script(title: str, body: str) -> str:
    return f"""
(() => {{
  try {{
    const queryAll = (selector) => Array.from(document.querySelectorAll(selector));
    const cleanText = (el) => (el?.innerText || el?.textContent || '').replace(/\\s+/g, '');
    const textIncludes = (el, terms) => terms.some((term) => cleanText(el).includes(term));
    const setNativeValue = (el, value) => {{
      if (!el) return false;
      const proto = Object.getPrototypeOf(el);
      const descriptor = Object.getOwnPropertyDescriptor(proto, 'value');
      if (descriptor && descriptor.set) {{
        descriptor.set.call(el, value);
      }} else {{
        el.value = value;
      }}
      el.dispatchEvent(new Event('input', {{ bubbles: true }}));
      el.dispatchEvent(new Event('change', {{ bubbles: true }}));
      return true;
    }};
    const setEditable = (el, value) => {{
      if (!el) return false;
      el.focus();
      const lines = value.split(/\\n+/).filter(Boolean);
      el.innerHTML = lines.map((line) => `<p>${{line.replace(/[&<>]/g, (ch) => ({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[ch]))}}</p>`).join('');
      el.dispatchEvent(new InputEvent('input', {{ bubbles: true, inputType: 'insertText', data: value }}));
      el.dispatchEvent(new Event('change', {{ bubbles: true }}));
      return true;
    }};

    const titleTarget =
      queryAll('input[placeholder*="标题"], textarea[placeholder*="标题"]').find(Boolean) ||
      queryAll('input, textarea').find((el) => textIncludes(el.parentElement || el, ['标题'])) ||
      queryAll('input, textarea')[0];

    const bodyTarget =
      queryAll('[contenteditable="true"]').find((el) => !textIncludes(el, ['标题'])) ||
      queryAll('textarea').find((el) => !textIncludes(el.parentElement || el, ['标题']));

    const titleOk = titleTarget ? setNativeValue(titleTarget, {js_string(title)}) : false;
    const bodyOk = bodyTarget
      ? (bodyTarget.getAttribute('contenteditable') === 'true'
        ? setEditable(bodyTarget, {js_string(body)})
        : setNativeValue(bodyTarget, {js_string(body)}))
      : false;

    return JSON.stringify({{
      titleOk,
      bodyOk,
      titlePlaceholder: titleTarget ? (titleTarget.getAttribute('placeholder') || '') : '',
      bodyKind: bodyTarget ? (bodyTarget.getAttribute('contenteditable') === 'true' ? 'contenteditable' : bodyTarget.tagName) : ''
    }});
  }} catch (error) {{
    return JSON.stringify({{ titleOk: false, bodyOk: false, error: String(error && error.message || error) }});
  }}
}})();
""".strip()


def build_insert_hashtags_script(hashtags: List[str]) -> str:
    return f"""
(() => {{
  try {{
    const tags = {js_string(hashtags)}
      .map((tag) => String(tag || '').trim().replace(/^#/, ''))
      .filter(Boolean);
    if (!tags.length) {{
      return JSON.stringify({{ hashtagsOk: true, inserted: 0, skipped: 0 }});
    }}

    const queryAll = (selector) => Array.from(document.querySelectorAll(selector));
    const cleanText = (el) => (el?.innerText || el?.textContent || '').replace(/\\s+/g, '');
    const textIncludes = (el, terms) => terms.some((term) => cleanText(el).includes(term));

    const bodyTarget =
      queryAll('[contenteditable="true"]').find((el) => !textIncludes(el, ['标题'])) ||
      queryAll('textarea').find((el) => !textIncludes(el.parentElement || el, ['标题']));
    if (!bodyTarget) {{
      return JSON.stringify({{ hashtagsOk: false, error: 'body target not found' }});
    }}
    const insertText = (text) => {{
      if (!text) return;
      if (bodyTarget.getAttribute('contenteditable') === 'true') {{
        bodyTarget.focus();
        document.execCommand('insertText', false, text);
        bodyTarget.dispatchEvent(new InputEvent('input', {{ bubbles: true, inputType: 'insertText', data: text }}));
      }} else {{
        bodyTarget.value = (bodyTarget.value || '') + text;
        bodyTarget.dispatchEvent(new Event('input', {{ bubbles: true }}));
        bodyTarget.dispatchEvent(new Event('change', {{ bubbles: true }}));
      }}
    }};
    const insertSpace = () => {{
      if (bodyTarget.getAttribute('contenteditable') === 'true') {{
        bodyTarget.focus();
        const down = new KeyboardEvent('keydown', {{ key: ' ', code: 'Space', keyCode: 32, which: 32, bubbles: true }});
        const up = new KeyboardEvent('keyup', {{ key: ' ', code: 'Space', keyCode: 32, which: 32, bubbles: true }});
        bodyTarget.dispatchEvent(down);
        document.execCommand('insertText', false, ' ');
        bodyTarget.dispatchEvent(new InputEvent('input', {{ bubbles: true, inputType: 'insertText', data: ' ' }}));
        bodyTarget.dispatchEvent(up);
      }} else {{
        bodyTarget.value = (bodyTarget.value || '') + ' ';
        bodyTarget.dispatchEvent(new Event('input', {{ bubbles: true }}));
        bodyTarget.dispatchEvent(new Event('change', {{ bubbles: true }}));
      }}
    }};
    const clickAfterLastTag = () => {{
      if (bodyTarget.getAttribute('contenteditable') === 'true') {{
        bodyTarget.focus();
        const range = document.createRange();
        range.selectNodeContents(bodyTarget);
        range.collapse(false);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        const rect = bodyTarget.getBoundingClientRect();
        bodyTarget.dispatchEvent(new MouseEvent('click', {{
          bubbles: true,
          clientX: Math.max(0, rect.right - 5),
          clientY: Math.max(0, rect.bottom - 5)
        }}));
      }} else {{
        const len = (bodyTarget.value || '').length;
        bodyTarget.focus();
        if (bodyTarget.setSelectionRange) {{
          bodyTarget.setSelectionRange(len, len);
        }}
        bodyTarget.dispatchEvent(new MouseEvent('click', {{ bubbles: true }}));
      }}
    }};

    let delay = 0;
    const schedule = (fn, ms) => {{
      delay += ms;
      setTimeout(fn, delay);
    }};

    schedule(() => clickAfterLastTag(), 0);
    schedule(() => insertText('\\n'), 500);
    schedule(() => insertText('\\n'), 0);
    for (let i = 0; i < tags.length; i += 1) {{
      if (i > 0) schedule(() => insertText(' '), 0);
      schedule(() => insertText(`#${{tags[i]}}`), 0);
      schedule(() => clickAfterLastTag(), 1000);
      schedule(() => insertSpace(), 1000);
    }}
    schedule(() => clickAfterLastTag(), 200);
    schedule(() => insertSpace(), 0);

    return JSON.stringify({{ hashtagsOk: true, inserted: tags.length, skipped: 0, scheduled: true, totalDelayMs: delay }});

  }} catch (error) {{
    return JSON.stringify({{ hashtagsOk: false, error: String(error && error.message || error) }});
  }}
}})();
""".strip()


def build_action_script(action: str) -> str:
    return f"""
(() => {{
  try {{
    const queryAll = (selector) => Array.from(document.querySelectorAll(selector));
    const cleanText = (el) => (el?.innerText || el?.textContent || '').replace(/\\s+/g, '').trim();
    const isVisible = (el) => {{
      const rect = el.getBoundingClientRect();
      const style = window.getComputedStyle(el);
      return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
    }};
    const exactAction = {js_string(action)};
    const rankNode = (el) => {{
      const text = cleanText(el);
      if (!text) return -999;
      if (text === exactAction) return 1000;
      if (exactAction === '发布' && (text === '立即发布' || text === '确认发布')) return 950;
      if (exactAction === '保存草稿' && (text === '保存草稿' || text === '保存为草稿')) return 950;
      if (text.includes(exactAction) && text.length <= 8) return 700 - text.length;
      return -999;
    }};
    const candidates = queryAll('button, div, span')
      .filter((el) => isVisible(el))
      .map((el) => {{
        const rect = el.getBoundingClientRect();
        return {{
          el,
          text: cleanText(el),
          rank: rankNode(el),
          tag: (el.tagName || '').toLowerCase(),
          x: rect.left,
          y: rect.top
        }};
      }})
      .filter((item) => item.rank > 0)
      .sort((a, b) => b.rank - a.rank || ((b.tag === 'button') - (a.tag === 'button')) || b.y - a.y || b.x - a.x);
    const actionButton = candidates[0]?.el;
    if (!actionButton) {{
      return JSON.stringify({{ actionOk: false, error: 'action button not found' }});
    }}
    actionButton.click();
    return JSON.stringify({{ actionOk: true, text: cleanText(actionButton) }});
  }} catch (error) {{
    return JSON.stringify({{ actionOk: false, error: String(error && error.message || error) }});
  }}
}})();
""".strip()


def open_publish_page(url: str) -> None:
    script = f'''
tell application "Google Chrome"
  activate
  set targetTab to missing value
  repeat with wi from 1 to count windows
    set w to window wi
    repeat with ti from 1 to count tabs of w
      set t to tab ti of w
      if (URL of t contains "{TARGET_HOST}") then
        set active tab index of w to ti
        set index of w to 1
        set targetTab to t
        exit repeat
      end if
    end repeat
    if targetTab is not missing value then exit repeat
  end repeat
  if targetTab is missing value then
    if (count of windows) = 0 then make new window
    set targetTab to active tab of front window
  end if
  set URL of targetTab to "{url}"
end tell
'''.strip()
    result = run_osascript(script)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "Failed to open Google Chrome.")


def parse_json_output(raw: str, context: str) -> Dict:
    text = (raw or "").strip()
    if not text:
        raise SystemExit(f"Empty JavaScript response while {context}.")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON while {context}: {text}") from exc


def upload_with_extension(files: List[str], selectors: List[str], timeout_seconds: float) -> Dict:
    dispatch = parse_json_output(execute_js(build_extension_upload_script(files, selectors)), "dispatching upload through extension")
    if not dispatch.get("ok"):
        raise SystemExit(dispatch.get("error") or "Failed to dispatch upload through extension.")

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        raw = execute_js(build_read_upload_result_script())
        if raw:
            result = parse_json_output(raw, "reading upload result")
            if result.get("ok"):
                return result
            raise SystemExit(result.get("error") or f"Upload failed at step {result.get('step')}.")
        time.sleep(1.0)
    raise SystemExit("Timed out waiting for the Chrome extension to upload images.")


def publish(package_path: Path, image_dir: Path, mode: str, url: str, wait_seconds: float, skip_action: bool) -> None:
    package = load_package(package_path)
    images = collect_images(package, image_dir)
    if not images:
        raise SystemExit("No .png images found. Render images first or pass --image-dir.")

    open_publish_page(url)
    time.sleep(wait_seconds)

    mode_payload = parse_json_output(execute_js(build_select_graphic_mode_script()), "switching to graphic-note mode")
    if not mode_payload.get("switched"):
        raise SystemExit(f"Failed to switch to graphic-note mode: {json.dumps(mode_payload, ensure_ascii=False)}")

    time.sleep(2.0)
    prepare_payload = parse_json_output(execute_js(build_prepare_upload_script()), "preparing upload")
    upload_payload = upload_with_extension(images, prepare_payload.get("selectors") or [], timeout_seconds=20.0)

    time.sleep(4.0)
    title = package.get("title", "").strip()
    body = build_body_text(package)
    hashtags = package.get("hashtags") or []
    action_label = "发布" if mode == "publish" else "保存草稿"
    fill_payload = parse_json_output(execute_js(build_fill_script(title, body)), "filling title/body")
    hashtag_payload = parse_json_output(execute_js(build_insert_hashtags_script(hashtags)), "inserting hashtags")
    time.sleep((hashtag_payload.get("totalDelayMs") or 0) / 1000.0 + 1.0)
    action_payload = {"actionOk": False, "skipped": True} if skip_action else parse_json_output(execute_js(build_action_script(action_label)), "clicking publish action")

    print(json.dumps({
        "package": str(package_path),
        "image_dir": str(Path(images[0]).parent),
        "mode": mode,
        "mode_switch": mode_payload,
        "upload_prepare": prepare_payload,
        "upload_result": upload_payload,
        "fill_result": fill_payload,
        "hashtag_result": hashtag_payload,
        "action_result": action_payload,
    }, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish a Xiaohongshu image note in Chrome on macOS.")
    parser.add_argument("package", help="Path to post.json")
    parser.add_argument("--image-dir", default=None, help="Directory containing rendered .png files")
    parser.add_argument("--mode", choices=["draft", "publish"], default="draft", help="Save draft or publish live")
    parser.add_argument("--skip-action", action="store_true", help="Fill content but skip clicking publish/draft action")
    parser.add_argument("--url", default=DEFAULT_URL, help="Creator platform publish URL")
    parser.add_argument("--wait-seconds", type=float, default=8.0, help="Initial page-load wait before switching to image-note mode")
    args = parser.parse_args()

    package_path = Path(args.package).expanduser().resolve()
    image_dir = Path(args.image_dir).expanduser().resolve() if args.image_dir else None

    try:
        publish(package_path, image_dir, args.mode, args.url, args.wait_seconds, args.skip_action)
    except SystemExit:
        raise
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
