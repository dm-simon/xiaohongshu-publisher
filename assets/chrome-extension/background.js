const DEBUGGER_VERSION = "1.3";

function withAttachedDebugger(tabId, work) {
  const target = { tabId };
  return chrome.debugger.attach(target, DEBUGGER_VERSION)
    .catch((error) => {
      const message = String(error?.message || error);
      if (message.includes("Another debugger is already attached")) {
        return null;
      }
      throw error;
    })
    .then((attachResult) => work(target).finally(() => {
      if (attachResult === null) {
        return;
      }
      return chrome.debugger.detach(target).catch(() => {});
    }));
}

function sendCommand(target, method, params = {}) {
  return chrome.debugger.sendCommand(target, method, params);
}

async function resolveNodeId(target, selectors) {
  const document = await sendCommand(target, "DOM.getDocument", { depth: -1, pierce: true });
  for (const selector of selectors) {
    const result = await sendCommand(target, "DOM.querySelector", {
      nodeId: document.root.nodeId,
      selector
    });
    if (result?.nodeId) {
      return { nodeId: result.nodeId, selector };
    }
  }
  return null;
}

async function uploadFiles(tabId, payload) {
  const selectors = payload.selectors && payload.selectors.length
    ? payload.selectors
    : [
        'input[type="file"][accept*="image"]',
        'input[type="file"]'
      ];

  return withAttachedDebugger(tabId, async (target) => {
    const resolved = await resolveNodeId(target, selectors);
    if (!resolved) {
      return {
        ok: false,
        step: "resolve-node",
        error: "No matching file input found",
        selectors
      };
    }

    await sendCommand(target, "DOM.setFileInputFiles", {
      nodeId: resolved.nodeId,
      files: payload.files
    });

    return {
      ok: true,
      step: "set-files",
      selector: resolved.selector,
      fileCount: payload.files.length
    };
  });
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type !== "codex-xhs-upload") {
    return false;
  }

  const tabId = sender.tab?.id;
  if (!tabId) {
    sendResponse({ ok: false, step: "tab", error: "Missing sender tab id" });
    return false;
  }

  uploadFiles(tabId, message.payload || {})
    .then(sendResponse)
    .catch((error) => {
      sendResponse({
        ok: false,
        step: "exception",
        error: String(error?.message || error)
      });
    });

  return true;
});
