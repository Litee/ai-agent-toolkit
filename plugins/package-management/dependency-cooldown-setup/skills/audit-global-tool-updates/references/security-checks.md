# Security Checklist for Global Tool Updates

When auditing a package update, examine the diff between the currently installed version and the latest version. Use this checklist to identify suspicious or potentially malicious changes.

## Critical Checks (BLOCK)

### 1. New or Changed Executable Scripts

- New files in `bin/` or changes to existing `bin` entries
- New `preinstall`, `postinstall`, `prepublish`, `postpublish` scripts
- Changes to existing lifecycle scripts that add network calls or file writes
- New shell scripts, batch files, or compiled binaries

### 2. Changed Entry Points

- Changes to `main`, `module`, `exports`, or `browser` fields in `package.json`
- New entry points that point to previously non-existent files
- Changes to `types` or `typings` fields that could load untrusted code

### 3. Obfuscated or Dangerous Code

- `eval()`, `exec()`, `Function()` calls in new code
- Base64-encoded payloads being decoded and executed
- Dynamic code generation (`new Function(...)`)
- `child_process.exec` / `spawn` calls with user-controlled input
- `require()` or `import` of dynamically constructed paths

### 4. Network Activity

- New HTTP/HTTPS requests in lifecycle scripts
- DNS lookups or socket connections in pre/post-install hooks
- Data exfiltration patterns (sending local file contents to remote servers)

## Warning Checks (REVIEW)

### 5. New Dependencies

- New dependencies added to `dependencies` (not just `devDependencies`)
- New dependencies with no published source code (e.g., git URLs, tarballs)
- Dependencies that are popular targets for supply-chain attacks (lodash, minimist, node-fetch, etc.)
- Dependency version bumps to pre-release versions (alpha, beta, rc)

### 6. Changed Build Configuration

- New or changed `build` scripts
- Changes to `webpack`, `rollup`, `esbuild`, or other bundler configs
- New post-build steps that modify output files

### 7. File System Changes

- New files added outside `src/` or `lib/` (especially in root)
- Changes to `.npmignore` or `files` field that change what gets published
- New `.npmrc` or `.npmrc` changes that point to private registries

### 8. Permission or Environment Changes

- Scripts that modify system files, permissions, or environment variables
- Changes that require `sudo` or elevated privileges
- Scripts that modify PATH, NODE_PATH, or other environment variables

## Safe Patterns (typically SAFE)

- Bug fixes in source code without changing entry points
- Documentation updates
- Test additions or improvements
- Dependency updates in `devDependencies` only
- Minor API additions that don't change behavior
- Type definition updates

## How to Examine a Diff

1. **Fetch both versions** — Download tarballs for both the installed and latest versions.
2. **Extract side by side** — Use `tar -xzf` to extract both to separate directories.
3. **Diff `package.json`** — Check for field changes, new scripts, new dependencies.
4. **Diff `bin/`** — Check for new or changed executable scripts.
5. **Diff lifecycle scripts** — Check `preinstall`, `postinstall`, etc.
6. **Diff source files** — Look for obfuscated code, network calls, dynamic execution.
7. **Check new files** — List all files added in the new version.
