(function () {
  document.documentElement.dataset.codexXhsBridgeReady = "1";

  document.addEventListener("codex-xhs-upload", async () => {
    let detail = {};
    try {
      detail = JSON.parse(document.documentElement.dataset.codexXhsUploadPayload || "{}");
    } catch (error) {
      detail = {};
    }

    const response = await chrome.runtime.sendMessage({
      type: "codex-xhs-upload",
      payload: detail
    }).catch((error) => ({
      ok: false,
      step: "runtime-message",
      error: String(error?.message || error)
    }));

    document.documentElement.dataset.codexXhsUploadResult = JSON.stringify(response);
  });
})();
