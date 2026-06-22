chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "CAREER_AGENT_EXTRACT_JOB") return false;
  const selection = window.getSelection()?.toString().trim() || "";
  const main = document.querySelector("main") || document.body;
  const pageText = (main?.innerText || document.body.innerText || "").replace(/\s+\n/g, "\n").trim();
  sendResponse({
    pageTitle: document.title,
    pageUrl: window.location.href,
    selectedText: selection,
    pageText: pageText.slice(0, 45000),
  });
  return true;
});
