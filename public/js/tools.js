// Developer tools on top of the VeriFactu engine: hash debugging, XML record parsing and chain checks, QR links.
// Pure functions, no network: runs in the browser and in Node tests.
import { sha256Hex, altaHashInput, validNif } from './verifactu.js';

// Exact field order of the AEAT hash specification for RegistroAnulacion.
export function anulacionHashInput(r) {
  return [
    ['IDEmisorFacturaAnulada', r.nif], ['NumSerieFacturaAnulada', r.number], ['FechaExpedicionFacturaAnulada', r.date],
    ['Huella', r.prevHash || ''], ['FechaHoraHusoGenRegistro', r.generatedAt],
  ].map(([k, v]) => `${k}=${String(v ?? '').trim()}`).join('&');
}

const QR = {
  verifactu: { prod: 'https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQR', test: 'https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQR' },
  noverifactu: { prod: 'https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQRNoVerifactu', test: 'https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQRNoVerifactu' },
};

export function qrLink(f, env = 'prod', mode = 'verifactu') {
  const u = new URL(QR[mode][env]);
  u.searchParams.set('nif', String(f.nif).trim().toUpperCase());
  u.searchParams.set('numserie', String(f.number).trim());
  u.searchParams.set('fecha', String(f.date).trim());
  u.searchParams.set('importe', String(f.total).trim());
  return u.toString();
}

export function checkQrUrl(s) {
  let u;
  try { u = new URL(String(s).trim()); } catch { return [{ ok: false, text: 'No es una URL válida' }]; }
  const known = Object.values(QR).flatMap((m) => Object.values(m));
  const p = u.searchParams;
  const checks = [
    { ok: known.includes(`${u.origin}${u.pathname}`), text: `Servicio de cotejo de la AEAT: ${u.origin}${u.pathname}` },
    { ok: validNif(p.get('nif')), text: `nif = ${p.get('nif') || '(vacío)'}` },
    { ok: Boolean(p.get('numserie')) && p.get('numserie').length <= 60, text: `numserie = ${p.get('numserie') || '(vacío)'}` },
    { ok: /^\d{2}-\d{2}-\d{4}$/.test(p.get('fecha') || ''), text: `fecha = ${p.get('fecha') || '(vacío)'}, formato dd-mm-aaaa` },
    { ok: /^-?\d{1,12}(\.\d{1,2})?$/.test(p.get('importe') || ''), text: `importe = ${p.get('importe') || '(vacío)'}, punto decimal y máximo 2 decimales` },
  ];
  const extra = [...p.keys()].filter((k) => !['nif', 'numserie', 'fecha', 'importe'].includes(k));
  if (extra.length) checks.push({ ok: false, text: `Parámetros no esperados: ${extra.join(', ')}` });
  return checks;
}

// --- XML records --------------------------------------------------------------
const decode = (s) => s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&amp;/g, '&');
const rx = (name, flags = '') => new RegExp(`<(?:[\\w-]+:)?${name}\\b[^>]*>([\\s\\S]*?)<\\/(?:[\\w-]+:)?${name}>`, flags);
const raw = (block, name) => (block.match(rx(name)) || [])[1] || '';
const val = (block, name) => decode(raw(block, name).trim());

export function parseRecords(xml) {
  const out = [];
  const re = /<(?:[\w-]+:)?(RegistroAlta|RegistroAnulacion)\b[^>]*>([\s\S]*?)<\/(?:[\w-]+:)?\1>/g;
  let m;
  while ((m = re.exec(String(xml || '')))) {
    const [, kind, body] = m;
    const id = raw(body, 'IDFactura');
    const own = body.replace(rx('Encadenamiento'), '');
    const common = {
      prevHash: val(raw(body, 'RegistroAnterior'), 'Huella'),
      first: /PrimerRegistro>\s*S\s*</.test(body),
      generatedAt: val(body, 'FechaHoraHusoGenRegistro'),
      hash: val(own, 'Huella'),
    };
    if (kind === 'RegistroAlta') {
      out.push({ kind: 'alta', nif: val(id, 'IDEmisorFactura'), number: val(id, 'NumSerieFactura'), date: val(id, 'FechaExpedicionFactura'), type: val(body, 'TipoFactura'), taxTotal: val(body, 'CuotaTotal'), total: val(body, 'ImporteTotal'), ...common });
    } else {
      out.push({ kind: 'anulacion', nif: val(id, 'IDEmisorFacturaAnulada'), number: val(id, 'NumSerieFacturaAnulada'), date: val(id, 'FechaExpedicionFacturaAnulada'), ...common });
    }
  }
  return out;
}

export async function verifyRecords(recs) {
  const rows = [];
  for (let i = 0; i < recs.length; i++) {
    const r = recs[i];
    const computed = await sha256Hex(r.kind === 'alta' ? altaHashInput(r) : anulacionHashInput(r));
    let chainOk = null;
    if (r.first) chainOk = !r.prevHash;
    else if (i > 0) chainOk = r.prevHash.toUpperCase() === recs[i - 1].hash.toUpperCase();
    rows.push({ ...r, computed, hashOk: computed === r.hash.toUpperCase(), chainOk });
  }
  return rows;
}

// --- Hash debugging -------------------------------------------------------------
// Tries the formatting mistakes we see most often and explains which one produced the expected hash.
const amounts = (v) => {
  const s = String(v ?? '').trim();
  const n = Number(s.replace(',', '.'));
  const out = new Set([s]);
  if (s && Number.isFinite(n)) { out.add(n.toFixed(2)); out.add(String(n)); out.add(n.toFixed(2).replace('.', ',')); }
  return [...out];
};
const dates = (v) => {
  const s = String(v ?? '').trim();
  const out = new Set([s]);
  let m;
  if ((m = s.match(/^(\d{4})-(\d{2})-(\d{2})$/))) out.add(`${m[3]}-${m[2]}-${m[1]}`);
  if ((m = s.match(/^(\d{2})\/(\d{2})\/(\d{4})$/))) out.add(`${m[1]}-${m[2]}-${m[3]}`);
  if ((m = s.match(/^(\d{2})-(\d{2})-(\d{4})$/))) { out.add(`${m[3]}-${m[2]}-${m[1]}`); out.add(`${m[1]}/${m[2]}/${m[3]}`); }
  return [...out];
};
const stamps = (v) => {
  const s = String(v ?? '').trim();
  const out = new Set([s]);
  if (s.endsWith('Z')) out.add(s.replace(/Z$/, '+00:00'));
  if (/[+-]\d{4}$/.test(s)) out.add(s.replace(/([+-]\d{2})(\d{2})$/, '$1:$2'));
  if (/[+-]\d{2}:\d{2}$/.test(s)) out.add(s.replace(/([+-]\d{2}):(\d{2})$/, '$1$2'));
  out.add(s.replace(/\.\d+(?=(Z|[+-]\d{2}:?\d{2})$)/, ''));
  return [...out];
};
const prevs = (v) => { const s = String(v ?? '').trim(); return [...new Set([s, s.toUpperCase(), s.toLowerCase()])]; };

export async function diagnose(f, expected) {
  const input = altaHashInput(f);
  const hash = await sha256Hex(input);
  const want = String(expected || '').trim().toUpperCase();
  if (!want) return { input, hash, match: null };
  if (hash === want) return { input, hash, match: true };
  const label = { taxTotal: 'CuotaTotal', total: 'ImporteTotal', date: 'FechaExpedicionFactura', generatedAt: 'FechaHoraHusoGenRegistro', prevHash: 'Huella anterior' };
  for (const taxTotal of amounts(f.taxTotal)) for (const total of amounts(f.total)) for (const date of dates(f.date)) {
    for (const generatedAt of stamps(f.generatedAt)) for (const prevHash of prevs(f.prevHash)) {
      const g = { ...f, taxTotal, total, date, generatedAt, prevHash };
      if ((await sha256Hex(altaHashInput(g))) === want) {
        const diffs = Object.keys(label).filter((k) => String(g[k]) !== String(f[k] ?? '').trim())
          .map((k) => `${label[k]}: la huella esperada se calculó con "${g[k]}", pero aquí figura "${String(f[k] ?? '').trim()}"`);
        return { input, hash, match: false, explained: true, diffs, fixedInput: altaHashInput(g) };
      }
    }
  }
  return { input, hash, match: false, explained: false };
}
