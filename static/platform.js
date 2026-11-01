(function () {
  "use strict";
  window.pplPlatform = {
    newId() {
      // randomUUID is missing on early iOS 15 and non-HTTPS LAN previews.
      const bytes = new Uint8Array(16);
      window.crypto.getRandomValues(bytes);
      bytes[6] = (bytes[6] & 15) | 64;
      bytes[8] = (bytes[8] & 63) | 128;
      const hex = Array.from(bytes, byte => byte.toString(16).padStart(2, "0"));
      return [hex.slice(0, 4), hex.slice(4, 6), hex.slice(6, 8), hex.slice(8, 10), hex.slice(10)].map(part => part.join("")).join("-");
    },
    download(content, filename, mime) {
      const native = window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.pplExport;
      if (native) {
        native.postMessage({ content, filename });
        return;
      }
      const url = URL.createObjectURL(new Blob([content], { type: mime }));
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
  };
})();
