#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');

const SETTINGS_PATH = path.join(os.homedir(), '.claude', 'settings.json');

const pluginRoot = process.env.CLAUDE_PLUGIN_ROOT;
if (!pluginRoot) {
  // Not running inside a CC hook context — skip silently
  process.exit(0);
}

const scriptPath = path.join(pluginRoot, 'references', 'status-line-script.js');

// Use the node binary that's running this script
const nodeBin = process.execPath;

// Quote paths to handle spaces in node binary or script path
const expectedCommand = `"${nodeBin}" "${scriptPath}"`;

// Read existing settings
let settings = {};
let rawSettings = null;
if (fs.existsSync(SETTINGS_PATH)) {
  try {
    rawSettings = fs.readFileSync(SETTINGS_PATH, 'utf8');
    settings = JSON.parse(rawSettings);
  } catch (_) {
    // Corrupt settings — preserve raw file, only patch statusLine key below
    rawSettings = null;
    settings = {};
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

// Configure statusLine, preserving all other settings
settings.statusLine = { type: 'command', command: expectedCommand };

// Ensure parent directory exists
fs.mkdirSync(path.dirname(SETTINGS_PATH), { recursive: true });
fs.writeFileSync(SETTINGS_PATH, JSON.stringify(settings, null, 2) + '\n', 'utf8');
process.stdout.write(`status-line configured: ${expectedCommand}\n`);
