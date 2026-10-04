import { buildAlta, altaXml } from './js/verifactu.js';
import { parseRecords, verifyRecords, diagnose, qrLink, checkQrUrl } from './js/tools.js';

const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

document.querySelectorAll('[data-tab]').forEach((b) => b.addEventListener('click', () => {
  document.querySelectorAll('[data-tab]').forEach((x) => x.classList.toggle('tab-on', x === b));
  document.querySelectorAll('[data-pane]').forEach((p) => p.classList.toggle('hidden', p.dataset.pane !== b.dataset.tab));
}));

// Hash
const FIELDS = ['nif', 'number', 'date', 'type', 'taxTotal', 'total', 'prevHash', 'generatedAt'];
const AEAT_EXAMPLE = { nif: '89890001K', number: '12345678/G33', date: '01-01-2024', type: 'F1', taxTotal: '12.35', total: '123.45', prevHash: '', generatedAt: '2024-01-01T19:20:30+01:00', expected: '3C464DAF61ACB827C65FDA19F352A4E3BDC2C640E9E9FC4CC058073F38F12F60' };

async function runHash() {
  const f = Object.fromEntries(FIELDS.map((k) => [k, $(`#h-${k}`).value]));
  const d = await diagnose(f, $('#h-expected').value);
  let status = '';
  if (d.match === true) status = '<div class="ok">✓ Coincide con la huella esperada.</div>';
  else if (d.match === false && d.explained) {
    status = `<div class="warn">✗ No coincide, y hemos encontrado la causa:</div><ul class="mt-1 list-disc list-inside text-slate-300">${d.diffs.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>
      <div class="label mt-3">Cadena con la que se calculó la huella esperada</div><pre class="code">${esc(d.fixedInput)}</pre>
      <p class="mt-2 text-xs text-slate-400">Los valores de la huella deben ser idénticos a los del registro que envías a la AEAT.</p>`;
  } else if (d.match === false) {
    status = '<div class="bad">✗ No coincide. Revisa el orden de los campos, los espacios y los formatos: fecha dd-mm-aaaa, importes con punto decimal tal y como van en el XML, y la huella anterior completa.</div>';
  }
  $('#h-out').innerHTML = `<div class="label">Cadena de entrada, formato AEAT</div><pre class="code">${esc(d.input)}</pre>
    <div class="label mt-3">Huella SHA-256</div><pre class="code">${esc(d.hash)}</pre><div class="mt-3 text-sm">${status}</div>`;
}
$('#h-form').addEventListener('submit', (e) => { e.preventDefault(); runHash(); });
$('#h-example').addEventListener('click', () => {
  for (const k of [...FIELDS, 'expected']) $(`#h-${k}`).value = AEAT_EXAMPLE[k];
  runHash();
});

// XML
async function sampleXml() {
  const issuer = { name: 'Empresa Ejemplo SL', nif: 'B76543214' };
  const recs = [];
  for (let i = 1; i <= 3; i++) {
    recs.push(await buildAlta({ issuer, invoice: { number: `2026-000${i}`, date: '2026-10-04', recipient: { name: 'Cliente Ejemplo SL', nif: 'B12345674' }, lines: [{ description: 'Servicio', qty: i, price: 100, vat: 21 }] }, prev: recs[i - 2] || null, generatedAt: `2026-10-04T1${i}:00:00+02:00` }));
  }
  return recs.map(altaXml).join('\n\n');
}
const mark = (v) => (v === true ? '<span class="ok">✓</span>' : v === false ? '<span class="bad">✗</span>' : '<span class="text-slate-500">—</span>');
async function runXml() {
  const recs = parseRecords($('#x-in').value);
  if (!recs.length) { $('#x-out').innerHTML = '<div class="bad">No se ha encontrado ningún RegistroAlta ni RegistroAnulacion.</div>'; return; }
  const rows = await verifyRecords(recs);
  const ok = rows.every((r) => r.hashOk && r.chainOk !== false);
  $('#x-out').innerHTML = `<div class="${ok ? 'ok' : 'bad'} mb-3 text-sm">${ok ? `✓ ${rows.length} registro${rows.length === 1 ? '' : 's'} con huella correcta y bien encadenados.` : '✗ Hay registros con errores.'}</div>
    <table class="w-full text-sm"><thead class="text-left text-xs text-slate-400"><tr><th class="py-2 pr-3">#</th><th class="pr-3">Tipo</th><th class="pr-3">Número</th><th class="pr-3">Fecha</th><th class="pr-3">Huella</th><th>Encadenamiento</th></tr></thead><tbody>
    ${rows.map((r, i) => `<tr class="border-t border-white/5 align-top"><td class="py-2 pr-3">${i + 1}</td><td class="pr-3">${r.kind === 'alta' ? 'Alta' : 'Anulación'}</td><td class="pr-3 font-mono text-xs">${esc(r.number)}</td><td class="pr-3">${esc(r.date)}</td>
      <td class="pr-3">${mark(r.hashOk)}${r.hashOk ? '' : `<div class="mt-1 font-mono text-[11px] text-slate-400 break-all">Calculada: ${esc(r.computed)}<br>En el XML: ${esc(r.hash || '(vacía)')}</div>`}</td>
      <td>${mark(r.chainOk)}${r.chainOk === false ? '<div class="mt-1 text-[11px] text-slate-400">La huella anterior no es la del registro previo.</div>' : ''}</td></tr>`).join('')}
    </tbody></table>`;
}
$('#x-form').addEventListener('submit', (e) => { e.preventDefault(); runXml(); });
$('#x-example').addEventListener('click', async () => { $('#x-in').value = await sampleXml(); runXml(); });

// QR
function qrSvg(text) {
  if (typeof window.qrcode !== 'function') return '';
  const q = window.qrcode(0, 'M');
  q.addData(text);
  q.make();
  return q.createSvgTag({ cellSize: 4, margin: 2, scalable: true });
}
$('#q-form').addEventListener('submit', (e) => {
  e.preventDefault();
  const url = qrLink({ nif: $('#q-nif').value, number: $('#q-number').value, date: $('#q-date').value, total: $('#q-total').value }, $('#q-env').value, $('#q-mode').value);
  const label = $('#q-mode').value === 'verifactu' ? 'VERI*FACTU' : '';
  $('#q-out').innerHTML = `<div class="w-44 rounded-xl bg-white p-2 text-black">${qrSvg(url)}${label ? `<div class="text-center text-[10px] font-bold tracking-wider">${label}</div>` : ''}</div>
    <div class="label mt-3">URL codificada</div><pre class="code">${esc(url)}</pre>`;
  $('#q-url').value = url;
  renderChecks(url);
});
function renderChecks(url) {
  $('#q-checks').innerHTML = checkQrUrl(url).map((c) => `<div>${c.ok ? '<span class="ok">✓</span>' : '<span class="bad">✗</span>'} ${esc(c.text)}</div>`).join('');
}
$('#q-check').addEventListener('submit', (e) => { e.preventDefault(); renderChecks($('#q-url').value); });

// Local visual self-test (localhost only).
if (location.hostname === 'localhost' && location.hash === '#selftest') {
  document.querySelector('#h-expected').value = '';
  for (const [k, v] of Object.entries({ nif: '89890001K', number: '12345678/G33', date: '01-01-2024', type: 'F1', taxTotal: '12.350', total: '123.45', prevHash: '', generatedAt: '2024-01-01T19:20:30+01:00', expected: '3C464DAF61ACB827C65FDA19F352A4E3BDC2C640E9E9FC4CC058073F38F12F60' })) document.querySelector(`#h-${k}`).value = v;
  runHash();
}
