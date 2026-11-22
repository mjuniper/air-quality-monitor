// Shared bits for the scripts that talk to the board over web workflow: where the
// board is and how to authenticate. Nothing secret lives in the scripts. The web
// workflow password comes from the local, gitignored settings.toml
// (CIRCUITPY_WEB_API_PASSWORD), the same file the board reads.

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');

// mDNS name of the board. code.py advertises CIRCUITPY_WIFI_HOSTNAME as
// <hostname>.local. Override with BOARD_HOST=... if code.py isn't running (say it
// crashed), when the board only answers to its default cpy-<board>-<mac>.local.
function boardHost () {
  const hostname = readSettings().CIRCUITPY_WIFI_HOSTNAME;
  if (!hostname) {
    throw new Error('CIRCUITPY_WIFI_HOSTNAME is missing from settings.toml (or set BOARD_HOST)');
  }
  return `${hostname}.local`;
}
export const HOST = process.env.BOARD_HOST || boardHost();

// A minimal settings.toml reader: handles `key = "string"` and `key = 123`,
// which is all CircuitPython's settings.toml supports anyway.
export function readSettings () {
  const text = readFileSync(join(ROOT, 'settings.toml'), 'utf8');
  const settings = {};
  for (const line of text.split('\n')) {
    const match = line.match(/^\s*([A-Za-z0-9_]+)\s*=\s*(.*?)\s*$/);
    if (!match) continue; // blank lines and comments
    const quoted = match[2].match(/^"(.*)"/);
    settings[match[1]] = quoted ? quoted[1] : match[2].replace(/\s*#.*$/, '');
  }
  return settings;
}

// Web workflow uses basic auth with an empty username.
export function authHeader () {
  const password = readSettings().CIRCUITPY_WEB_API_PASSWORD;
  if (!password) {
    throw new Error('CIRCUITPY_WEB_API_PASSWORD is missing from settings.toml');
  }
  return 'Basic ' + Buffer.from(':' + password).toString('base64');
}

export function boardUrl (path = '') {
  return `http://${HOST}/fs/${path}`;
}
