/**
 * Zero-dependency local development server for Windows & local testing.
 *
 * Runs locally without needing Vercel CLI installed:
 *   node scripts/local_server.js
 *
 * Serves web/ statically and delegates /api/chat to web/api/chat.js.
 */

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import handler from '../web/api/chat.js';

const WEB_DIR = fileURLToPath(new URL('../web', import.meta.url));

const PORT = process.env.PORT || 3000;

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
};

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  const pathname = url.pathname;

  // API route
  if (pathname === '/api/chat') {
    let body = '';
    req.on('data', (chunk) => { body += chunk; });
    req.on('end', async () => {
      try {
        req.body = body ? JSON.parse(body) : {};
      } catch (e) {
        req.body = {};
      }
      await handler(req, res);
    });
    return;
  }

  // Static file serving
  let relPath = pathname === '/' ? 'index.html' : pathname.replace(/^\//, '');
  const filePath = path.join(WEB_DIR, relPath);

  // Security check: ensure within WEB_DIR
  if (!filePath.startsWith(WEB_DIR)) {
    res.statusCode = 403;
    res.end('Forbidden');
    return;
  }

  if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
    const ext = path.extname(filePath).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';
    res.setHeader('Content-Type', contentType);
    fs.createReadStream(filePath).pipe(res);
  } else {
    res.statusCode = 404;
    res.setHeader('Content-Type', 'text/plain');
    res.end('Not Found');
  }
});

server.listen(PORT, () => {
  console.log(`Groww SIP Retention Dashboard running at http://localhost:${PORT}`);
});

