#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const SETTINGS_PATH = path.join(process.env.HOME, '.claude', 'settings.json');

const pluginRoot = process.env.CLAUDE_PLUGIN_ROOT;
if (!pluginRoot) {
  // Not running inside a CC hook context — skip silently
  process.exit(0);
}

const scriptPath = path.join(pluginRoot, 'references', 'status-line-script.js');

// Use the node binary that's running this script
const nodeBin = process.execPath;

const expectedCommand = `${nodeBin} ${scriptPath}`;

// Read existing settings
let settings = {};
if (fs.existsSync(SETTINGS_PATH)) {
  try {
    settings = JSON.parse(fs.readFileSync(SETTINGS_PATH, 'utf8'));
  } catch (_) {
    // Corrupt settings — treat as empty and overwrite statusLine only
  }
}

// Check if already configured correctly
if (
  settings.statusLine &&
  settings.statusLine.type === 'command' &&
  settings.statusLine.command === expectedCommand
) {
  process.exit(0);
}

// Configure statusLine
settings.statusLine = { type: 'command', command: expectedCommand };

fs.writeFileSync(SETTINGS_PATH, JSON.stringify(settings, null, 2) + '\n', 'utf8');
process.stdout.write(`status-line configured: ${expectedCommand}\n`);
