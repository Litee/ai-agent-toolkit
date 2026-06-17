---
name: ai-news-digest
description: Use when user says "latest AI news", "AI news digest", "what's new in AI", "fetch AI news", "get latest AI developments", or wants to see or save recent AI news/developments. Also triggers on the Korean phrases "최신 AI 뉴스", "AI 뉴스 정리", "AI 소식", "AI 업데이트".
---

# AI News Digest

Fetches latest AI news from multiple sources and presents an interactive digest. User chooses time range and categories, browses results in the terminal, then selects which items to save.

---

## Execution Algorithm

### Step 1: Acknowledge Trigger

Briefly confirm that you're starting the AI News Digest.

**Example:** "AI 뉴스를 가져오겠습니다. 먼저 몇 가지 설정을 선택해주세요."

---

### Step 2: Ask Time Range

Use AskUserQuestion to let the user choose how far back to look.

```
AskUserQuestion:
  questions:
    - question: "어떤 기간의 AI 뉴스를 볼까요?"
      header: "기간 선택"
      multiSelect: false
      options:
        - label: "오늘 (24시간)"
          description: "지난 24시간 이내 게시된 최신 뉴스"
        - label: "지난 일주일"
          description: "최근 7일간의 주요 뉴스 (Recommended)"
        - label: "지난 한달"
          description: "최근 30일간의 뉴스. 결과가 많을 수 있습니다"
```

**Map selection to --days argument:**
- "오늘 (24시간)" → `--days 1`
- "지난 일주일" → `--days 7`
- "지난 한달" → `--days 30`

---

### Step 3: Ask Category Filter

Use AskUserQuestion with multiSelect to let the user filter by source category.

```
AskUserQuestion:
  questions:
    - question: "어떤 소스의 뉴스를 볼까요?"
      header: "카테고리"
      multiSelect: true
      options:
        - label: "전체"
          description: "모든 소스에서 가져오기 (Recommended)"
        - label: "AI 도구/에이전트"
          description: "Claude Code, Copilot, LangChain, Vercel AI SDK 등 실무 도구"
        - label: "공식 블로그"
          description: "Anthropic, OpenAI, DeepMind 등 공식 발표"
        - label: "연구 논문"
          description: "ArXiv ML/AI/CL 최신 논문"
```

**Map selection to --category argument:**
- "전체" selected → `--category all` (ignore other selections)
- "AI 도구/에이전트" → `ai_tools`
- "공식 블로그" → `official`
- "연구 논문" → `research`
- "커뮤니티/뉴스" → `community,tech_news`
- Multiple selections → comma-join (e.g., `official,ai_tools`)

---

### Step 4: Check Dependencies & Fetch Data

**4-1. Check Python dependencies:**

```bash
python3 -c "import feedparser, yaml, certifi" 2>/dev/null || \
  pip3 install feedparser pyyaml certifi --quiet
```

**4-2. Inform user about fetching:**

"AI 뉴스를 가져오는 중입니다... (약 5-10초 소요됩니다)"

**Note:** The plugin now uses:
- **Parallel fetching** (much faster than before)
- **Caching** (subsequent runs within 30 min are instant)
- **Real-time progress** updates showing each feed as it completes

**4-3. Locate and run the fetch script:**

The fetch script ships alongside this skill. Resolve it via `${SKILL_DIR}`,
which the harness expands to this skill's root directory — never hardcode an
absolute path or use `find`:

```bash
python3 "${SKILL_DIR}/../../config/fetch_news.py" --days {days} --top 10 --category {category} --output json
```

The script prints real-time progress, one line per feed as it completes
(feed name, status, article count), followed by a total count.

**Error handling:**
- If script not found: inform user of the path issue
- If script fails: show error and suggest checking internet connection
- If no results: suggest expanding the time range

---

### Step 4.5: Analyze and Show Trending Topics (Optional)

After fetching data successfully, you can optionally show trending topics.
Run this from the config directory so the import resolves
(`cd "${SKILL_DIR}/../../config"`):

```python
from trend_analyzer import TrendAnalyzer

analyzer = TrendAnalyzer()
trends = analyzer.analyze_trends(all_entries, top_n=5)

if trends:
    print("\n## 이번 주 AI 뉴스 트렌드:")
    for trend in trends:
        print(f"- **{trend['term']}** ({trend['count']}개 기사)")
        if trend['example_articles']:
            example = trend['example_articles'][0]
            print(f"  예: {example['title']} ({example['source']})")
```

**Example output:**
```
## 이번 주 AI 뉴스 트렌드:
- **AI agent** (8개 기사)
  예: New autonomous agents from OpenAI (OpenAI News)
- **Claude 4** (5개 기사)
  예: Claude 4 benchmarks released (Anthropic Engineering)
- **RAG** (4개 기사)
  예: Improving RAG with vector databases (LangChain Blog)
```

---

### Step 5: Display Results in Terminal

Parse the JSON output and display results directly in the terminal. **DO NOT save to a file yet.**

Format each entry as:

```
**IMPORTANT**: Run `date '+%Y-%m-%d %H:%M'` to get the exact current date/time. Never estimate.

## AI News Top 10 — {today's date} (최근 {period})

---

**1. {Title}** (Score: {score})
{Source} | {Published date}
{Summary (first 200 chars)}
Link: {url}

---

**2. {Title}** (Score: {score})
{Source} | {Published date}
{Summary (first 200 chars)}
Link: {url}

---

... (up to 10 items)
```

**Display rules:**
- Number each item clearly (1-10)
- Show score for reference
- Keep summary concise (max ~200 chars)
- Include the link for each item
- If fewer than 10 results, show all available

After displaying all results, proceed to Step 6.

---

### Step 6: Ask What to Save

After displaying the list, ask the user in plain text:

**Output this exact message:**

"저장할 뉴스가 있다면 번호로 알려주세요. (예: 1, 3, 7)"
"없으면 '없음'이라고 해주세요."

**Wait for user response.** The user may respond in various formats:
- "2, 5번 저장해줘" → save items 2 and 5
- "1,3,7" → save items 1, 3, 7
- "전부 저장" or "all" → save all items
- "없음" or "없어" or "no" → skip saving, go to Step 7 with no-save path

**Parse the numbers from the response.** Extract all digits that correspond to displayed item numbers.

---

### Step 7: Save Selected Items (or Skip)

**If user said "없음" / no save:**
- Output: "알겠습니다. 저장 없이 마무리합니다. 다음에 또 AI 뉴스가 필요하면 말씀해주세요!"
- End execution.

**If user selected specific items:**

**7-1. Determine save location:**
- Save to the current working directory as `./ai-news-digest-YYYY-MM-DD.md`.
- If the user specifies a different directory, save there instead.

**7-2. Generate markdown for selected items only:**

```markdown
# AI News Digest - YYYY-MM-DD

> **Generated**: YYYY-MM-DD HH:MM
> **Period**: Last {N} days
> **Categories**: {selected categories}
> **Saved items**: {count} of {total}

---

## 1. {Title}

**Source**: {Source} | **Published**: YYYY-MM-DD | **Score**: {Score}

{Full summary}

**Key Points**:
- {Extracted key point 1}
- {Extracted key point 2}

**Why It Matters**: {Brief significance analysis}

**Read More**: {Link}

---

## 2. {Title}
...
```

**7-3. Save using Write tool.**

**7-4. Confirm to user:**

```
Saved {N}개 뉴스를 저장했습니다: {file_path}

저장된 항목:
- 1. {Title}
- 2. {Title}

다음에 또 AI 뉴스가 필요하면 말씀해주세요!
```

---

## Trigger Phrases

**English:**
- "latest AI news"
- "AI news digest"
- "what's new in AI"
- "fetch AI news"
- "get latest AI developments"

**Korean:**
- "최신 AI 뉴스"
- "AI 뉴스 정리"
- "AI 소식"
- "AI 업데이트"

---

## Configuration

### RSS Feed Sources (config/feeds.yaml)

**Official Blogs** (weight: 9-10):
- OpenAI, DeepMind, Anthropic (community feed)

**Research Papers** (weight: 8):
- ArXiv (ML, AI, CL)

**Community** (weight: 6):
- Hacker News, Reddit (MachineLearning, LocalLLaMA)

**Tech News** (weight: 5):
- The Verge, TechCrunch

### Scoring System

**Final Score** = Base Weight + Keyword Boost + Recency Boost

### User Preferences (config/user_preferences.yaml - Optional)

Power users can create a `user_preferences.yaml` file to customize defaults:

```yaml
default_time_range: 7  # Skip time range question
default_categories: "all"  # Skip category question
default_top_n: 10

favorite_sources:  # Get +2 weight boost
  - "OpenAI News"
  - "Anthropic Engineering (Community)"

excluded_sources: []  # Skip these feeds entirely

performance:
  max_workers: 5  # Parallel fetch workers
  cache_ttl_minutes: 30  # Cache duration
```

**Benefits:**
- Skip repetitive questions for frequent users
- Boost favorite sources automatically
- Control caching and performance settings

---

## Quick Reference

### When to Use

**Use when:**
- Catching up on AI news
- Daily/weekly briefing
- Browsing and selectively saving interesting news

**Skip when:**
- Asking about a specific article (follow its link and analyze the page directly instead)
- Very old news (> 1 month)

---

## Error Handling

| Scenario | Response |
|----------|----------|
| Python missing | Install or inform user |
| No internet | Show error message |
| No results | Suggest expanding time range |
| Script not found | Check plugin installation path |
| User gives invalid numbers | Ask again with valid range |

---

## Examples

### Example 1: Default Flow

```
User: "최신 AI 뉴스"
→ AskUserQuestion: 기간 선택
User: "지난 일주일"
→ AskUserQuestion: 카테고리 선택
User: "전체"
→ Fetch & display Top 10 in terminal
→ "저장할 뉴스 번호를 알려주세요"
User: "2, 5번 저장해줘"
→ Save items 2, 5 as markdown
→ Confirm saved path
```

### Example 2: Filtered + No Save

```
User: "AI 뉴스 보여줘"
→ AskUserQuestion: 기간 선택
User: "오늘 (24시간)"
→ AskUserQuestion: 카테고리 선택
User: "공식 블로그"
→ Fetch & display results (official only, last 24h)
→ "저장할 뉴스 번호를 알려주세요"
User: "없음"
→ End without saving
```

### Example 3: Save All

```
User: "AI news digest"
→ AskUserQuestion: 기간
User: "지난 한달"
→ AskUserQuestion: 카테고리
User: "연구 논문", "공식 블로그"
→ Fetch & display (research + official, last 30 days)
→ "저장할 뉴스 번호를 알려주세요"
User: "전부 저장"
→ Save all items as markdown
```

---

## Performance

The script fetches feeds in parallel and caches results, so a first run
completes in a few seconds and subsequent runs within the cache TTL
(default 30 min) return almost instantly. Scoring, deduplication
(fuzzy duplicate detection), and keyword scoring add negligible time.

---

## Dependencies

```bash
pip3 install feedparser pyyaml certifi
```

**certifi** provides Mozilla's CA certificate bundle for secure SSL/TLS verification.

---

## Related Skills

This skill is self-contained. For a deep-dive analysis of a single article
after browsing the digest, follow its link and analyze the page directly.
