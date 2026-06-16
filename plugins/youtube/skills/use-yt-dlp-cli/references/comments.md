# Fetching Comments

## Canonical invocation

```bash
YT=/tmp/yt-tools-venv/bin/yt-dlp

# Fetch top 100 comments (top-level parents only)
$YT --skip-download --write-comments \
    --extractor-args "youtube:comment_sort=top;max_comments=100,100,0,0,1" \
    -o "/tmp/comments/%(id)s" URL
# Writes /tmp/comments/<id>.info.json with a "comments" key
```

## max_comments tuple

`--extractor-args "youtube:max_comments=A,B,C,D,E"` where:
- A = max total comments
- B = max top-level parents
- C = max replies total
- D = max replies per thread
- E = max depth

```bash
# 200 comments, up to 50 replies per thread, depth 2
--extractor-args "youtube:max_comments=200,200,50,50,2"

# All comments (slow — can trigger rate limits)
--extractor-args "youtube:max_comments=ALL,ALL,ALL,ALL,ALL"
```

## Sort order

```bash
--extractor-args "youtube:comment_sort=top"   # default
--extractor-args "youtube:comment_sort=new"
```

## Comment object fields

```json
{
  "id": "Ugxxxxx",
  "text": "Comment text",
  "timestamp": 1700000000,
  "like_count": 42,
  "is_favorited": false,
  "author": "Username",
  "author_id": "UCxxxxxxxxx",
  "author_thumbnail": "https://...",
  "author_is_uploader": false,
  "parent": "root",
  "is_pinned": false
}
```

`"parent": "root"` = top-level comment. Otherwise `parent` is the ID of the parent comment.

## Extract comments from info.json

```python
import json
data = json.load(open("<id>.info.json"))
for c in data.get("comments", []):
    print(c["author"], ":", c["text"])
```

## Scale caveat

For >10k comments or reply-tree analytics, use YouTube Data API v3 (`commentThreads.list` + `comments.list`) via `youtube-knowledge`. yt-dlp's comment pagination breaks periodically and is slow.
