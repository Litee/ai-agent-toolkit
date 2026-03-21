const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// ══════════════════ Feature Flags ══════════════════
const SHOW_CONTEXT_TEXT = true;   // "X/Y (Z%)" colored by usage level
const SHOW_TOKEN_COUNTS = true;   // "Xm in / Ym out"
const SHOW_COST         = true;   // "$X.XX" from pre-calculated cost
const SHOW_MODEL        = true;   // Model ID
const SHOW_GIT_BRANCH   = true;   // Current git branch
const SHOW_CWD          = true;   // Working directory path
// ═══════════════════════════════════════════════════

const RESET     = '\x1b[0m';
const GREEN     = '\x1b[32m';
const YELLOW    = '\x1b[33m';
const ORANGE    = '\x1b[38;5;208m';
const RED_BLINK = '\x1b[5;31m';

function buildContextText(data) {
  if (!SHOW_CONTEXT_TEXT) return '';
  const totalInput  = data.context_window?.total_input_tokens  || 0;
  const totalOutput = data.context_window?.total_output_tokens || 0;
  const contextSize = data.context_window?.context_window_size || 0;
  const total = totalInput + totalOutput;

  const remaining = data.context_window?.remaining_percentage;
  const pct = remaining != null
    ? (100 - remaining).toFixed(1)
    : (contextSize > 0 ? ((total * 100) / contextSize).toFixed(1) : '0.0');
  const usedTokens = remaining != null
    ? Math.round(contextSize * (100 - remaining) / 100)
    : total;
  const text = `${usedTokens}/${contextSize} (${pct}%)`;

  if (remaining == null) return text;
  const scaled = Math.min(Math.round(((100 - remaining) / 80) * 100), 100);

  if (scaled >= 95) return `${RED_BLINK}${text}${RESET}`;
  if (scaled >= 81) return `${ORANGE}${text}${RESET}`;
  if (scaled >= 63) return `${YELLOW}${text}${RESET}`;
  return `${GREEN}${text}${RESET}`;
}

function buildTokenCounts(data) {
  if (!SHOW_TOKEN_COUNTS) return '';
  const inM  = ((data.context_window?.total_input_tokens  || 0) / 1_000_000).toFixed(2);
  const outM = ((data.context_window?.total_output_tokens || 0) / 1_000_000).toFixed(2);
  return `${inM}M in / ${outM}M out`;
}

function buildCost(data) {
  if (!SHOW_COST) return '';
  const cost = data.cost?.total_cost_usd;
  if (cost == null) return '';
  return `$${cost.toFixed(2)}`;
}

function buildModel(data) {
  if (!SHOW_MODEL) return '';
  const id = data.model?.id || 'unknown';
  return id.startsWith('global.anthropic.') ? id.slice('global.anthropic.'.length) : id;
}

function buildGitBranch(data) {
  if (!SHOW_GIT_BRANCH) return '';
  const cwd = data.workspace?.current_dir || process.cwd();
  try {
    if (fs.existsSync(path.join(cwd, '.git'))) {
      const branch = execSync(
        'git symbolic-ref --short HEAD 2>/dev/null || git rev-parse --short HEAD 2>/dev/null',
        { cwd, encoding: 'utf8' }
      ).trim();
      return branch || '';
    }
    return 'no git';
  } catch (e) {
    return 'no git';
  }
}

function buildCwd(data) {
  if (!SHOW_CWD) return '';
  const cwd = data.workspace?.current_dir || process.cwd();
  const parts = cwd.split('/');
  if (parts.length <= 4) return cwd;
  return parts.map((p, i) => i < parts.length - 3 ? (p === '' ? '' : p[0]) : p).join('/');
}


let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  try {
    const data = JSON.parse(input);
    const segments = [
      buildContextText(data),
      buildTokenCounts(data),
      buildCost(data),
      buildModel(data),
      buildGitBranch(data),
      buildCwd(data),
    ].filter(s => s !== '');
    process.stdout.write(segments.join(' │ '));
  } catch (e) {
    // Silent failure — statusline output must not contain error text
  }
});
