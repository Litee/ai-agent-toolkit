#!/usr/bin/env node
// PreToolUse hook: block edits to the main git repo, require worktrees.

const path = require('path');
const fs = require('fs');
const { execFileSync } = require('child_process');

const DENY_MSG =
  "BLOCKED: Direct edits to the main git repo are not allowed while " +
  "CC_HOOK_BLOCK_WRITING_TO_MAIN_REPO is set. Create a git worktree " +
  "(e.g. 'git worktree add .claude/worktrees/<task-name> -b <task-name>') " +
  "and make your changes there. To temporarily disable, unset CC_HOOK_BLOCK_WRITING_TO_MAIN_REPO.";

function resolvePath(filePath) {
  try {
    return fs.realpathSync(filePath);
  } catch {
    return path.resolve(filePath);
  }
}

function gitRevParse(dir) {
  try {
    const out = execFileSync('git', ['rev-parse', '--git-dir', '--git-common-dir'], {
      cwd: dir,
      stdio: ['ignore', 'pipe', 'ignore'],
      timeout: 2000,
    });
    const [gitDir, commonDir] = out.toString().trim().split('\n');
    return { gitDir, commonDir };
  } catch {
    return null;
  }
}

let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => (input += chunk));
process.stdin.on('end', () => {
  let filePath;
  try {
    const data = JSON.parse(input);
    filePath = data?.tool_input?.file_path || data?.tool_input?.notebook_path;
  } catch {
    process.exit(0);
  }

  if (!filePath) process.exit(0);

  const resolved = resolvePath(filePath);
  const dir = fs.existsSync(resolved) ? path.dirname(resolved) : path.dirname(path.resolve(filePath));

  const result = gitRevParse(dir);
  if (!result) process.exit(0); // not inside a git repo — nothing to protect

  const { gitDir, commonDir } = result;

  // Resolve both paths relative to the cwd used for git, then to absolute.
  const absGitDir = path.resolve(dir, gitDir);
  const absCommonDir = path.resolve(dir, commonDir);

  if (absGitDir === absCommonDir) {
    // Main working tree: gitDir and commonDir are the same.
    process.stderr.write(DENY_MSG + '\n');
    process.exit(2);
  }

  // Linked worktree: gitDir points to a per-worktree dir, commonDir to the shared .git.
  process.exit(0);
});
