// Runs circup against the board over web workflow, so no USB drive is needed:
//   npm run circup -- install -r requirements.txt
// The host and password come from board.js / settings.toml, so they never get
// typed into a task or the shell history. Install circup with `pipx install circup`.

import { spawnSync } from 'node:child_process';
import { HOST, readSettings } from './board.js';

const password = readSettings().CIRCUITPY_WEB_API_PASSWORD;
if (!password) {
  throw new Error('CIRCUITPY_WEB_API_PASSWORD is missing from settings.toml');
}

const result = spawnSync(
  'circup',
  ['--host', HOST, '--password', password, ...process.argv.slice(2)],
  {
    stdio: 'inherit',
    // pipx puts circup here, and VS Code doesn't always have it on PATH
    env: { ...process.env, PATH: `${process.env.HOME}/.local/bin:${process.env.PATH}` }
  }
);
process.exit(result.status ?? 1);
