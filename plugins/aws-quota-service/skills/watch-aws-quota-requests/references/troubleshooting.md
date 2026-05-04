# Troubleshooting

The watcher uses `GetRequestedServiceQuotaChange` under the hood. Common failures:

| Error | Cause | Handling |
|-------|-------|----------|
| `NoSuchResourceException` / `ResourceNotFoundException` | Request ID does not exist, was deleted, or belongs to a different account/region | The watcher logs the bad ID, drops it from the watch list, and continues polling the remaining IDs. Fix by re-running with a valid `--request-ids` set or use `--all-pending` to seed the list from the account's live state. |
| `AccessDeniedException` / `UnrecognizedClientException` | `--profile` lacks `servicequotas:GetRequestedServiceQuotaChange` or the profile's credentials expired mid-poll | The watcher logs the failure and applies linear backoff (5s, 10s, 20s, max 120s) before the next poll — it does NOT exit. Refresh credentials in the profile and the next poll recovers automatically. |
| `ThrottlingException` / `TooManyRequestsException` | Service Quotas API rate limit | Linear backoff up to 120s then normal polling resumes. Raise `--poll-interval-seconds` (default 600) if throttling is persistent. |
| `ExpiredTokenException` | SSO / STS session ended while watcher was running | Same linear-backoff recovery as `AccessDeniedException` — re-run `aws sso login --profile <p>` to refresh the session; the watcher picks up the refreshed creds on the next poll. |
| Keystroke delivery fails (cmux/tmux mode) | Target surface/pane was closed after the watcher started | The watcher logs and retries once; if the target is still gone, it exits cleanly. Re-launch with a current surface ref from `cmux identify --json` or `tmux list-panes`. |

**Escalation path:** if the watcher exits with a non-zero code, read `~/.claude/plugin-data/aws-quota-service/watch-aws-quota-requests/watcher-<id>.json` — the final `error` field documents why. Re-launch uses the same `--watcher-id` to resume from the last-seen state.
