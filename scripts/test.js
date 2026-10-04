// Offline tests for the VeriFactu developer tools.
import { buildAlta, altaXml, sha256Hex, altaHashInput } from '../public/js/verifactu.js';
import { anulacionHashInput, parseRecords, verifyRecords, diagnose, qrLink, checkQrUrl } from '../public/js/tools.js';

let failed = 0;
const expect = (label, ok) => { console.log(ok ? 'ok  ' : 'FAIL', label); if (!ok) failed++; };
const AEAT = { nif: '89890001K', number: '12345678/G33', date: '01-01-2024', type: 'F1', taxTotal: '12.35', total: '123.45', prevHash: '', generatedAt: '2024-01-01T19:20:30+01:00' };
const AEAT_HASH = '3C464DAF61ACB827C65FDA19F352A4E3BDC2C640E9E9FC4CC058073F38F12F60';

expect('official AEAT example matches', (await diagnose(AEAT, AEAT_HASH)).match === true);
const zero = await diagnose({ ...AEAT, taxTotal: '12.350' }, AEAT_HASH);
expect('explains an amount formatting mismatch', zero.explained && zero.diffs.some((d) => d.startsWith('CuotaTotal')));
const iso = await diagnose({ ...AEAT, date: '2024-01-01' }, AEAT_HASH);
expect('explains an ISO date mistake', iso.explained && iso.diffs.some((d) => d.startsWith('FechaExpedicionFactura')));
const tz = await diagnose({ ...AEAT, generatedAt: '2024-01-01T19:20:30+0100' }, AEAT_HASH);
expect('explains a timezone without colon', tz.explained && tz.diffs.some((d) => d.startsWith('FechaHoraHusoGenRegistro')));
expect('reports an unexplained mismatch honestly', (await diagnose({ ...AEAT, nif: 'B12345674' }, AEAT_HASH)).explained === false);
expect('anulación hash input uses the AEAT field order', anulacionHashInput({ nif: 'A', number: 'B', date: 'C', prevHash: 'D', generatedAt: 'E' }) === 'IDEmisorFacturaAnulada=A&NumSerieFacturaAnulada=B&FechaExpedicionFacturaAnulada=C&Huella=D&FechaHoraHusoGenRegistro=E');

const issuer = { name: 'Empresa & Hijos SL', nif: 'B76543214' };
const recs = [];
for (let i = 1; i <= 3; i++) recs.push(await buildAlta({ issuer, invoice: { number: `2026-000${i}`, date: '2026-10-04', recipient: { name: 'Cliente', nif: 'B12345674' }, lines: [{ description: 'S', qty: i, price: 100, vat: 21 }] }, prev: recs[i - 2] || null, generatedAt: `2026-10-04T1${i}:00:00+02:00` }));
const xml = recs.map(altaXml).join('\n');
const parsed = parseRecords(xml);
expect('parses every RegistroAlta with its own and previous hash', parsed.length === 3 && parsed[1].hash === recs[1].hash && parsed[1].prevHash === recs[0].hash && parsed[0].first);
const rows = await verifyRecords(parsed);
expect('valid chain verifies end to end', rows.every((r) => r.hashOk && r.chainOk !== false));
const tampered = await verifyRecords(parseRecords(xml.replace(`<sum1:ImporteTotal>${recs[1].total}</sum1:ImporteTotal>`, '<sum1:ImporteTotal>1.00</sum1:ImporteTotal>')));
expect('tampered amount is flagged on that record only', !tampered[1].hashOk && tampered[0].hashOk && tampered[2].hashOk);
const anul = `<sum1:RegistroAnulacion><sum1:IDFactura><sum1:IDEmisorFacturaAnulada>B76543214</sum1:IDEmisorFacturaAnulada><sum1:NumSerieFacturaAnulada>2026-0003</sum1:NumSerieFacturaAnulada><sum1:FechaExpedicionFacturaAnulada>04-10-2026</sum1:FechaExpedicionFacturaAnulada></sum1:IDFactura><sum1:Encadenamiento><sum1:RegistroAnterior><sum1:Huella>${recs[2].hash}</sum1:Huella></sum1:RegistroAnterior></sum1:Encadenamiento><sum1:FechaHoraHusoGenRegistro>2026-10-04T15:00:00+02:00</sum1:FechaHoraHusoGenRegistro><sum1:Huella>HASH</sum1:Huella></sum1:RegistroAnulacion>`;
const anulHash = await sha256Hex(anulacionHashInput({ nif: 'B76543214', number: '2026-0003', date: '04-10-2026', prevHash: recs[2].hash, generatedAt: '2026-10-04T15:00:00+02:00' }));
const chainWithAnul = await verifyRecords(parseRecords(`${xml}\n${anul.replace('HASH', anulHash)}`));
expect('RegistroAnulacion is parsed, hashed and chained', chainWithAnul.length === 4 && chainWithAnul[3].hashOk && chainWithAnul[3].chainOk === true);
const link = qrLink({ nif: '89890001K', number: '12345678&G33', date: '01-01-2024', total: '241.4' });
expect('QR link encodes the series and passes every check', link.includes('numserie=12345678%26G33') && checkQrUrl(link).every((c) => c.ok));
expect('QR check flags a wrong date format', checkQrUrl(link.replace('01-01-2024', '2024-01-01')).some((c) => !c.ok));
expect('XML special characters survive the round trip', parseRecords(altaXml({ ...recs[0], number: 'A&B-1' }))[0].number === 'A&B-1' && altaHashInput(parsed[0]).includes('IDEmisorFactura=B76543214'));

// Affiliate links: only with a complete legal notice and a plain https URL.
const { affiliateHref } = await import('../public/js/affiliate.js');
const legalOk = { name: 'Titular', nif: '00000000T', address: 'Calle 1', email: 'a@b.es' };
expect('affiliate links stay off until the legal notice is complete', affiliateHref('quipu', { quipu: 'https://ref.example/q' }, { ...legalOk, nif: '' }) === null);
expect('affiliate links turn on only for https URLs with a complete legal notice', affiliateHref('quipu', { quipu: 'https://ref.example/q' }, legalOk) === 'https://ref.example/q' && affiliateHref('quipu', { quipu: 'javascript:alert(1)' }, legalOk) === null);

// Pages: SEO basics, no inline executable scripts (strict CSP) and no broken internal links.
const { readFileSync, readdirSync, existsSync } = await import('node:fs');
const pub = (p) => new URL(`../public/${p}`, import.meta.url);
const pages = ['index.html', 'aviso-legal.html', ...readdirSync(pub('guias/')).map((f) => `guias/${f}`)];
const resolveLink = (href) => {
  const clean = href.split(/[?#]/)[0].replace(/^\//, '');
  if (!clean) return 'index.html';
  return /\.[a-z0-9]+$/i.test(clean) ? clean : `${clean}.html`;
};
let pagesOk = true;
for (const p of pages) {
  const html = readFileSync(pub(p), 'utf8');
  const ok = /<title>[^<]{20,}<\/title>/.test(html) && /<meta name="description" content="[^"]{60,}"/.test(html) && /<link rel="canonical" href="https:\/\/verifactu-tools\.vercel\.app\//.test(html)
    && !/<script(?![^>]*\bsrc=)(?![^>]*application\/ld\+json)[^>]*>/i.test(html)
    && [...html.matchAll(/(?:href|src)="(\/[^"]*)"/g)].every(([, h]) => h.startsWith('/_vercel/') || existsSync(pub(resolveLink(h))));
  if (!ok) { pagesOk = false; console.log(`  page problem: ${p}`); }
}
expect(`${pages.length} pages have title, description, canonical, no inline scripts and no broken links`, pagesOk);

console.log(failed ? `${failed} check(s) failed` : 'all checks passed');
process.exit(failed ? 1 : 0);
