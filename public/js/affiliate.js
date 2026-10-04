// Pure helpers, testable in Node: an affiliate link is used only when the legal notice is complete and the URL is https.
export const isLegalComplete = (legal) => ['name', 'nif', 'address', 'email'].every((k) => String(legal?.[k] || '').trim().length > 0);

export function affiliateHref(key, affiliates, legal) {
  const url = String(affiliates?.[key] || '').trim();
  return isLegalComplete(legal) && /^https:\/\/[^\s"'<>]+$/.test(url) ? url : null;
}
