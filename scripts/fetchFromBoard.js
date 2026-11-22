import fetch from 'node-fetch';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { ROOT, authHeader, boardUrl } from './board.js';

console.log('fetching from board...');

const Authorization = authHeader();

// these are things we don't want to bring down from the board
// (lib/ is managed with circup, and its .mpy files are binary)
// there are other files we may bring down but gitignore (settings.toml)
const IGNORE = [
  'boot_out.txt',
  'lib'
];

/*
  Workflow:
    - edit code in the browser with "web workflow"
    - execute this script to copy code to this directory (`npm run fetch-from-board`)
    - use normal git workflow to commit and push upstream
*/

async function fetchFS (path = '') {
  const url = boardUrl(path);
  console.log(`fetching filesystem from ${url}`);
  const resp = await fetch(url, {
    headers: {
      Accept: 'application/json',
      Authorization
    }
  });
  const data = await resp.json();
  // newer CircuitPython wraps the listing in an object, older versions return the array itself
  return Array.isArray(data) ? data : data.files;
}

async function fetchFile (file = '') {
  const resp = await fetch(boardUrl(file), {
    headers: {
      Accept: '*/*',
      Authorization
    }
  });
  return Buffer.from(await resp.arrayBuffer());
}

function shouldIgnore (name) {
  // special handling for . files
  return IGNORE.includes(name) || name.startsWith('.');
}

async function processFiles (path = '') {
  const data = await fetchFS(path);

  for (const entry of data) {
    if (!shouldIgnore(entry.name)) {
      const newPath = `${path}${entry.name}`;
      if (entry.directory) {
        if (!existsSync(join(ROOT, newPath))) {
          mkdirSync(join(ROOT, newPath));
        }
        // recursively call this function with the new path
        console.log(`recursively calling processFiles with ${newPath}/`);
        await processFiles(`${newPath}/`);
      } else {
        // fetch the file and write it to the file system
        console.log(`writing ${newPath}`);
        writeFileSync(join(ROOT, newPath), await fetchFile(newPath));
      }
    }
  }
}

await processFiles();
