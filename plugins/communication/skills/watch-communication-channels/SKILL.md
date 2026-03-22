---
name: watch-communication-channels
description: "This skill should be used when monitoring any communication channel for responses — chat threads, tickets, code review approvals, or similar async channels. Use when setting up background watchers, spawning team agent watchers, polling for replies, configuring adaptive backoff, setting nudge reminders, or deciding how long to wait before giving up. Triggers on 'watch for replies', 'monitor ticket', 'poll for updates', 'background watcher', 'team agent watcher', 'wait for response', 'check for new comments', 'nudge reviewer', 'adaptive backoff', 'stop watching after timeout', or any request to wait for a reply or action on an async channel."
---

# watch-communication-channels

Framework for monitoring async communication channels for responses. Use a dedicated team agent per channel — one for chat, one for tickets, one for a code review — to keep the main session focused on the actual task.

---

## Team Agent Architecture (required)

**Never poll in the primary session.** Every cron tick interrupts the main session and burns context window. Use a dedicated team agent instead.

### How it works

1. **Main session** spawns a named team agent via the `Agent` tool (e.g., `name: "slack-watcher"`, `name: "ticket-watcher"`)
2. **Watcher agent** sets up its own CronCreate polling loop
3. **Watcher agent contacts the main session via `SendMessage` ONLY when:**
   - A meaningful event is detected (new reply, status change, new comment, new approval)
   - An error prevents continued watching
   - The watch expires (7-day limit reached)
4. **Watcher agent MUST NOT:**
   - Report "no changes this tick" messages
   - Perform complex analysis or take consequential actions
   - Send heartbeat or alive confirmations
   - Reply to unrelated messages in the channel it's watching
5. **Main session** receives the notification, decides what to do, and re-launches the watcher if needed

The watcher is a **thin event detector**, not a worker. When it detects an event, it passes the raw event to the main agent for handling.

### One watcher per channel

When a task requires watching multiple channels simultaneously (e.g., both a chat thread and a ticket), spawn **separate** watcher agents — one per channel. This keeps each watcher simple, independently manageable, and easy to shut down.

```
# Example: spawning separate watchers
Agent(name="chat-watcher", team_name="my-team", prompt="Watch chat thread ...")
Agent(name="ticket-watcher", team_name="my-team", prompt="Watch ticket #12345 ...")
```

---

## Backoff Algorithm

Exponential backoff with a cap. Each tick doubles the interval up to the channel's maximum.

```
interval = BASE
loop:
    wait(interval)
    check for changes
    if changes detected:
        notify main agent via SendMessage
        reset interval to BASE
    else:
        interval = min(interval * 2, MAX)
```

**Session-resume backoff** — when re-registering a watcher after a session restart, choose the initial interval based on time since last activity:

| Time since last activity | Use interval |
|---|---|
| < 30 min | BASE |
| 30 min – 2h | BASE * 10 |
| 2h – 4h | BASE * 30 |
| > 4h | BASE * 60 (or MAX, whichever is smaller) |

---

## Channel Parameters

| Parameter | Chat (e.g. Slack) | Ticket system | Code review |
|---|---|---|---|
| Base interval | 1 min | 5 min | 5 min |
| Max interval | 480 min (8h) | 1440 min (24h) | 1440 min (24h) |
| Change detection | reply count delta in thread AND new top-level messages in channel | comment count + status delta | new comments, new approvals |
| Nudge mechanism | tag person in thread | comment mentioning action owner | direct message to comment author (for responses); ping non-approvers for approvals |
| Channel scope | watch both thread AND full channel (all threads) | N/A | N/A |

### Chat: watch thread + channel

When watching a chat channel, monitor:
1. **Thread replies** on the specific thread
2. **New top-level messages in the channel** that may be relevant (filtered by timestamp)

Never reply to messages unrelated to the task being watched.

---

## Watch Duration and Nudge Rules

### Maximum watch duration: 7 days

Stop polling after 7 days with no resolution. Post a stop-report to the configured notification channel when stopping.

### Nudge after 48 hours (business days)

If waiting for a specific person and no reply after 48 hours:
- Post one polite follow-up mentioning them
- Do this **once only**
- **Account for weekends:** if the 48-hour mark falls on Saturday or Sunday, nudge on the next business day (Monday)

### Stop-report format

When abandoning a watch (timeout, issue resolved, or task abandoned), post to the configured notification channel:

```
Watch stopped — [channel/ticket/CR identifier]
Reason: [7-day timeout | resolved | abandoned]
Last known state: [brief description]
```

Never silently abandon an active watch.

---

## CronCreate Template

Use this template for each channel type. Fill in values at creation time; embed current state in the prompt text so the watcher is resume-safe across session restarts.

```
Check [CHANNEL_TYPE] [IDENTIFIER] for new activity.
Baseline: [COUNT/STATE]. Current interval: [INTERVAL_MIN] min.
Last activity: [LAST_ACTIVITY_ISO]. Last check: [LAST_CHECK_ISO].

Print elapsed time:
  python3 -c "
from datetime import datetime, timezone
last = datetime.fromisoformat('[LAST_CHECK_ISO]').replace(tzinfo=timezone.utc)
now = datetime.now(timezone.utc)
mins = int((now - last).total_seconds() / 60)
print(f'[Watcher tick] {mins} min since last check')
"

Run the channel-specific check command (use the appropriate API or tool for the channel type).

If change detected (count increased or state changed):
  - Send summary to main agent via SendMessage
  - Delete this cron (CronDelete [job_id])
  - Re-create at BASE interval with updated count/state and LAST_CHECK_ISO=now

If no change:
  - Delete this cron (CronDelete [job_id])
  - Re-create at min([INTERVAL_MIN]*2, MAX) with LAST_CHECK_ISO=now

ALWAYS embed current state and UTC time when re-creating the cron.
Stop after 7 days total. Post stop-report to configured notification channel.
```

---

## Approval Nudge Rules

When nudging for code review approvals, be targeted:

1. **Replying to a comment on your review** — nudge the comment author directly (track the communication)
2. **Nudging for approvals:**
   - Target only reviewers who have NOT yet approved
   - Ping just enough people to reach the required approval count
   - Prioritize reviewers who were active contributors to the modified areas
   - Do this once only; don't mass-ping the entire reviewer list

---

## Related Skills

- **communicate-well** — communication principles and message style guidelines; load before posting any nudge or status update
