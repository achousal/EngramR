/** Copy-to-clipboard buttons on all code blocks */
function initClipboard(): void {
  document.querySelectorAll<HTMLPreElement>("pre").forEach((pre) => {
    if (pre.querySelector(".copy-btn")) return;

    const wrapper = document.createElement("div");
    wrapper.className = "code-block-wrapper";
    pre.parentNode?.insertBefore(wrapper, pre);
    wrapper.appendChild(pre);

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "copy-btn";
    btn.setAttribute("aria-label", "Copy code");
    btn.innerHTML =
      '<svg class="copy-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>' +
      '<svg class="check-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M20 6L9 17l-5-5"/></svg>';

    wrapper.appendChild(btn);

    btn.addEventListener("click", async () => {
      const code = pre.querySelector("code");
      const text = code ? code.textContent || "" : pre.textContent || "";
      try {
        await navigator.clipboard.writeText(text);
        btn.classList.add("copied");
        setTimeout(() => btn.classList.remove("copied"), 1500);
      } catch {
        // clipboard API may fail in insecure contexts; silently ignore
      }
    });
  });
}

document.addEventListener("DOMContentLoaded", initClipboard);
