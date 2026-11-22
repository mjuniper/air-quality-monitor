import fetch from 'node-fetch';
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { HOST, ROOT, authHeader, boardUrl } from './board.js';

/*
  Copies the code and settings to the board over web workflow, so the board
  never has to be unplugged or mounted over USB.

  Workflow:
    - edit code here
    - run this script (`npm run deploy`, or the "deploy" VS Code task)
    - commit and push with normal git

  CircuitPython reloads when files change, and the board's web server goes away
  for a moment each time, so requests are retried. code.py goes last so
  everything it imports is already in place when it restarts.
*/

const Authorization = authHeader();

// Only what the board runs. Scripts, lib/ (circup manages that) and the old
// secrets.py stay off the board.
const reporters = readdirSync(join(ROOT, 'reporters'))
  .filter(name => name.endsWith('.py'))
  .sort()
  .map(name => `reporters/${name}`);
const FILES = ['settings.toml', 'thresholds.py', 'boot.py', ...reporters, 'code.py'];

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

async function put (path, body) {
  for (let attempt = 1; ; attempt++) {
    let response;
    try {
      response = await fetch(boardUrl(path), { method: 'PUT', headers: { Authorization }, body });
    } catch (error) {
      if (attempt >= 5) throw error;
      await sleep(2000);
      continue;
    }
    if (response.ok) return response.status;
    if (response.status === 401) {
      throw new Error('401 unauthorized: check CIRCUITPY_WEB_API_PASSWORD in settings.toml');
    }
    if (response.status === 409) {
      throw new Error("409 conflict: the board's USB drive is mounted on a computer, so web workflow can't write. Unplug it, or reset the board without holding the button.");
    }
    throw new Error(`${response.status} ${response.statusText}`);
  }
}

console.log(`deploying to ${HOST}`);
await put('reporters/'); // a trailing slash creates a directory (fine if it exists)
for (const file of FILES) {
  process.stdout.write(`  ${file} ... `);
  console.log(await put(file, readFileSync(join(ROOT, file))));
}
console.log('done. CircuitPython reloads on its own; boot.py only takes effect after a reset.');
