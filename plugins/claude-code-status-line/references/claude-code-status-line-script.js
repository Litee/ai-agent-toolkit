const { execSync } = require('child_process');
const path = require('path');

// ══════════════════ Feature Flags ══════════════════
const SHOW_CONTEXT_TEXT = true;   // "X/Y (Z%)" colored by usage level
const SHOW_TOKEN_COUNTS = true;   // "Xm in / Ym out"
const SHOW_COST         = true;   // "$X.XX" from pre-calculated cost
const SHOW_MODEL        = true;   // Model display name
const SHOW_THINKING     = true;   // "thinking: off|low|medium|high|xhigh|max"
const SHOW_GIT_BRANCH   = true;   // Current git branch
const SHOW_CWD          = true;   // Working directory path
// ═══════════════════════════════════════════════════

const RESET     = '\x1b[0m';
const GREEN     = '\x1b[32m';
const YELLOW    = '\x1b[33m';
const ORANGE    = '\x1b[38;5;208m';
const RED       = '\x1b[31m';
const RED_BLINK = '\x1b[5;31m';

function buildContextText(data) {
  if (!SHOW_CONTEXT_TEXT) return '';
  const contextSize = data.context_window?.context_window_size || 0;
  const usedPct     = data.context_window?.used_percentage;
  if (usedPct == null || contextSize === 0) return '';
  const usedTokens  = Math.round(contextSize * usedPct / 100);
  const toK = n => `${Math.round(n / 1000)}K`;
  const text        = `${toK(usedTokens)}/${toK(contextSize)} (${usedPct.toFixed(1)}%)`;
  const scaled      = Math.min(Math.round((usedPct / 80) * 100), 100);
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
  const display = data.model?.display_name;
  if (display) return display;
  const id = data.model?.id || 'unknown';
  return id.startsWith('global.anthropic.') ? id.slice('global.anthropic.'.length) : id;
}

function buildThinking(data) {
  if (!SHOW_THINKING) return '';
  const enabled = data.thinking?.enabled;
  if (enabled == null) return '';
  if (!enabled) return 'thinking: off';
  const level = data.effort?.level;
  const tier  = level ? String(level).toLowerCase() : '';
  const text  = `thinking: ${tier || 'on'}`;
  if (tier === 'max')    return `${RED_BLINK}${text}${RESET}`;
  if (tier === 'xhigh')  return `${RED}${text}${RESET}`;
  if (tier === 'high')   return `${ORANGE}${text}${RESET}`;
  if (tier === 'medium') return `${YELLOW}${text}${RESET}`;
  if (tier === 'low')    return `${GREEN}${text}${RESET}`;
  return `${GREEN}${text}${RESET}`;
}

function buildGitBranch(data) {
  if (!SHOW_GIT_BRANCH) return '';
  const cwd = data.workspace?.current_dir || process.cwd();
  try {
    // Run git directly — it traverses up to find the repo root from any subdirectory.
    // execSync timeout prevents hanging if git is slow (e.g. network mounts).
    const branch = execSync(
      'git symbolic-ref --short HEAD 2>/dev/null || git rev-parse --short HEAD 2>/dev/null',
      { cwd, encoding: 'utf8', timeout: 3000 }
    ).trim();
    return branch || '';
  } catch (e) {
    return 'no git';
  }
}

function buildCwd(data) {
  if (!SHOW_CWD) return '';
  const cwd = data.workspace?.current_dir || process.cwd();
  const sep = path.sep;
  const parts = cwd.split(sep);
  if (parts.length <= 3) return cwd;
  return parts.map((p, i) => i < parts.length - 2 ? (p === '' ? '' : p[0]) : p).join(sep);
}

function buildDuration(data) {
  const ms = data.cost?.total_duration_ms;
  if (ms == null) return '';
  const totalSec = Math.floor(ms / 1000);
  if (totalSec < 60) return `${totalSec}s`;
  const hours = Math.floor(totalSec / 3600);
  const minutes = Math.floor((totalSec % 3600) / 60);
  const seconds = totalSec % 60;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m ${seconds}s`;
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
      buildDuration(data),
      buildModel(data),
      buildThinking(data),
      buildGitBranch(data),
      buildCwd(data),
    ].filter(s => s !== '');
    process.stdout.write(segments.join(' · '));
  } catch (e) {
    // Silent failure — statusline output must not contain error text
  }
});
