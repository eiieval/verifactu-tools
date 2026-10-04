import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

// Static dev server with the same security headers as production (read from vercel.json).
const PUBLIC = fileURLToPath(new URL('./public/', import.meta.url));
const cfg = JSON.parse(await readFile(new URL('./vercel.json', import.meta.url), 'utf8'));
const SECURITY = Object.fromEntries((cfg.headers?.[0]?.headers || []).map((x) => [x.key, x.value]));
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png' };
const port = Number(process.env.PORT) || 3000;

http.createServer(async (req, res) => {
  const path = decodeURIComponent(req.url.split('?')[0]).replace(/^\/+/, '') || 'index.html';
  if (path.includes('..')) { res.writeHead(400); return res.end(); }
  // Same clean URLs as production: /guias/x serves /guias/x.html.
  const file = extname(path) ? path : `${path}.html`;
  try {
    const buf = await readFile(join(PUBLIC, file));
    res.writeHead(200, { ...SECURITY, 'content-type': TYPES[extname(file)] || 'application/octet-stream' });
    res.end(buf);
  } catch {
    res.writeHead(404);
    res.end('not found');
  }
}).listen(port, () => console.log(`VeriFactu tools on http://localhost:${port}`));
