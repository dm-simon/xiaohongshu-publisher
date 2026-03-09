(function () {
  if (window.__codexXhsBridge) {
    return;
  }

  window.__codexXhsBridge = {
    version: "0.1.0",
    lastUploadResult: null,
    uploadImages(detail) {
      window.dispatchEvent(new CustomEvent("codex-xhs-upload", { detail }));
      return true;
    }
  };

  window.addEventListener("message", (event) => {
    if (event.source !== window) {
      return;
    }
    const data = event.data || {};
    if (data.source === "codex-xhs-extension" && data.type === "upload-result") {
      window.__codexXhsBridge.lastUploadResult = data.payload;
    }
  });
})();
