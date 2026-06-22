chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "CAREER_AGENT_EXTRACT_JOB") return false;
  const selection = window.getSelection()?.toString().trim() || "";
  const main = document.querySelector("main") || document.body;
  const pageText = (main?.innerText || document.body.innerText || "").replace(/\s+\n/g, "\n").trim();
  const extracted = extractJobDetails();
  sendResponse({
    pageTitle: document.title,
    pageUrl: window.location.href,
    selectedText: selection,
    ...extracted,
    pageText: pageText.slice(0, 45000),
  });
  return true;
});

function extractJobDetails() {
  const host = window.location.hostname.toLowerCase();
  const siteRules = [
    {
      source: "linkedin",
      match: "linkedin.",
      title: [".job-details-jobs-unified-top-card__job-title", ".jobs-unified-top-card__job-title", "h1"],
      company: [".job-details-jobs-unified-top-card__company-name", ".jobs-unified-top-card__company-name"],
      location: [".job-details-jobs-unified-top-card__primary-description-container", ".jobs-unified-top-card__bullet"],
      description: [".jobs-description-content__text", "#job-details"],
    },
    {
      source: "naukri",
      match: "naukri.",
      title: [".styles_jd-header-title__rZwM1", ".jd-header-title", "h1"],
      company: [".styles_jd-header-comp-name__MvqAI", ".jd-header-comp-name"],
      location: [".styles_jhc__location__W_pVs", ".location"],
      description: [".styles_JDC__dang-inner-html__h0K4t", ".job-desc", "section"],
    },
    {
      source: "indeed",
      match: "indeed.",
      title: ["[data-testid='jobsearch-JobInfoHeader-title']", "h1"],
      company: ["[data-company-name='true']", "[data-testid='inlineHeader-companyName']"],
      location: ["[data-testid='job-location']", "#jobLocationText"],
      description: ["#jobDescriptionText", "[data-testid='jobsearch-JobComponent-description']"],
    },
  ];
  const rule = siteRules.find((item) => host.includes(item.match)) || {
    source: "generic",
    title: ["[data-testid*='title' i]", "[class*='title' i]", "h1"],
    company: ["[data-testid*='company' i]", "[class*='company' i]"],
    location: ["[data-testid*='location' i]", "[class*='location' i]"],
    description: ["[class*='description' i]", "[id*='description' i]", "article", "main"],
  };
  return {
    source: rule.source,
    extractedTitle: firstText(rule.title),
    extractedCompany: firstText(rule.company),
    extractedLocation: cleanLocation(firstText(rule.location)),
    extractedDescription: firstText(rule.description, 50000),
  };
}

function firstText(selectors, limit = 180) {
  for (const selector of selectors) {
    const node = document.querySelector(selector);
    const text = node?.innerText?.replace(/\s+/g, " ").trim();
    if (text && text.length >= 2) return text.slice(0, limit);
  }
  return null;
}

function cleanLocation(value) {
  if (!value) return null;
  const parts = value.split(/\n|\u00b7|\|/).map((part) => part.trim()).filter(Boolean);
  return (parts.find((part) => /remote|hybrid|mumbai|pune|bengaluru|bangalore|hyderabad|delhi|noida|gurgaon|chennai/i.test(part)) || parts[0] || value).slice(0, 180);
}
