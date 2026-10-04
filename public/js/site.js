// Shared behaviour for every page: activates affiliate links when allowed and fills the legal notice.
import { AFFILIATES, LEGAL } from './config.js';
import { affiliateHref, isLegalComplete } from './affiliate.js';

for (const a of document.querySelectorAll('a[data-aff]')) {
  const href = affiliateHref(a.dataset.aff, AFFILIATES, LEGAL);
  if (!href) continue;
  a.href = href;
  a.rel = 'sponsored noopener noreferrer';
  a.target = '_blank';
  const tag = document.createElement('span');
  tag.className = 'aff-tag';
  tag.textContent = 'enlace de afiliado';
  a.append(' ', tag);
}

for (const el of document.querySelectorAll('[data-legal]')) {
  el.textContent = String(LEGAL[el.dataset.legal] || '').trim() || 'pendiente de completar';
}
const status = document.querySelector('[data-legal-status]');
if (status) status.textContent = isLegalComplete(LEGAL) ? 'Datos completos.' : 'Datos pendientes: mientras tanto esta web no contiene enlaces de afiliado.';
