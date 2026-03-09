#!/usr/bin/env python3

import json
import subprocess
import sys


TARGET_HOST = "creator.xiaohongshu.com"


def apple_string(value: str) -> str:
    compact = value.replace("\\", "\\\\").replace('"', '\\"')
    compact = compact.replace("\n", " ")
    return compact


def run_osascript(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )


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


def main() -> None:
    js = r"""
(() => {
  const root = document.documentElement;
  return JSON.stringify({
    bridge_ready: root.dataset.codexXhsBridgeReady === '1',
    href: location.href,
    title: document.title,
    upload_result: root.dataset.codexXhsUploadResult || ''
  });
})();
""".strip()
    raw = execute_js(js)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(raw, file=sys.stderr)
        raise SystemExit("Bridge check returned invalid JSON.") from exc
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
