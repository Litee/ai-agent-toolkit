# Creating Effective Anki Cards

This guide captures established best practices for creating effective flashcards based on cognitive science research, particularly the "20 Rules of Formulating Knowledge" and spaced repetition literature.

## Core Principles

### 1. Understand Before You Memorize
- **DO**: Build comprehension before creating cards. Read full chapters/docs first.
- **DON'T**: Create cards for material you don't understand - this yields negligible value.
- **Why**: Individual facts without context are like "scattered words" - disconnected and fragile.

### 2. Minimum Information Principle
- **DO**: Keep each card focused on ONE atomic piece of information
- **DO**: Make answers brief and specific
- **DON'T**: Create multi-part questions or lengthy answers
- **Why**: Simple items are neurologically easier to process consistently and schedule efficiently

**Bad Example:**
```
Q: What are the characteristics of the Dead Sea?
A: Salt lake, borders Israel/Jordan, 420m below sea level, 67km long, 18km wide, 377m deep, 33.7% salinity
```

**Good Example (split into separate cards):**
```
Q: What type of body of water is the Dead Sea?
A: Salt lake

Q: What countries border the Dead Sea?
A: Israel and Jordan

Q: What is the Dead Sea's elevation?
A: 420m below sea level
```

### 3. Use Cloze Deletions Effectively
- **DO**: Convert complex sentences into cloze format: `{{c1::answer}}`
- **DO**: Create multiple cloze cards from one sentence for different facts
- **Example**: "Bill {{c1::Clinton}} was the {{c2::second}} US president to go through impeachment"

### 4. Avoid Sets and Unordered Lists
- **DON'T**: Ask "What are the EU countries?" or "List the AWS compute services"
- **DO**: Convert sets into ordered sequences, relationships, or contextual items
- **Why**: Unordered sets overload memory because each recall uses different mental sequencing

### 5. Combat Interference
- **DO**: Add distinguishing context for similar items
- **DO**: Use examples, emotional content, or personal references
- **DON'T**: Create cards that look nearly identical
- **Why**: Interference is "probably the single greatest cause of forgetting"

### 6. Include Sufficient Context for Future Recall
- **DO**: Ensure the question is self-contained and makes sense months later
- **DO**: Include domain/topic context in the question itself (e.g., language name for programming cards)
- **DON'T**: Assume you'll remember the context when reviewing
- **Why**: Cards are reviewed in random order across topics; without context, similar questions become confusing

**Bad Example:**
```
Q: What method converts a string to uppercase?
A: upper()
```

**Good Example:**
```
Q: In Python, what string method converts text to uppercase?
A: upper()
```

### 7. Avoid Revealing the Answer in the Question
- **DO**: Write questions that test recall, not recognition
- **DON'T**: Include the answer or strong hints in the question text
- **DON'T**: Ask "What does X do?" while mentioning X by name when X is the answer
- **Why**: Questions that hint at answers test pattern matching, not true recall

**Bad Example:**
```
Q: What Python method splits strings? How does split() work?
A: split()
```

**Good Example:**
```
Q: In Python, what string method divides a string into a list using a delimiter?
A: split()
```

## Card Formulation Techniques

### Use Imagery
- Visual memory is stronger than verbal memory
- Include diagrams, charts, maps for spatial/relational concepts
- "One picture is worth a thousand words"

### Personalize and Add Examples
- Connect items to personal experiences
- Use specific, concrete examples rather than abstract definitions
- Personal references create distinctive neural pathways

### Provide Context Cues
- Use category labels, prefixes, or tags (e.g., `bioch: GRE`, `aws: ec2`)
- Context reduces necessary wording and prevents interference

### Strategic Redundancy
- Create complementary cards from different angles (e.g., term→definition AND definition→term)
- Different viewpoints strengthen recall probability

## Common Mistakes to Avoid

| Mistake | Problem | Solution |
|---------|---------|----------|
| Cards too complex | Multiple neural pathways cause interference | Split into atomic cards |
| Learning without understanding | Creates "useless material" | Read/understand first |
| Memorizing unordered lists | Each recall uses different sequencing | Convert to ordered sequences or relationships |
| Identical-looking cards | Causes chronic interference | Add distinguishing context |
| Skipping basics | Forgetting basics creates cascading problems | Start with fundamentals |
| Verbose answers | Hard to recall consistently | Keep answers brief (ideally 1-5 words) |
| Missing context | Question becomes ambiguous over time | Include topic/domain in the question |
| Answer in question | Tests recognition instead of recall | Describe functionality without naming the answer |

## Effective Note Types

| Note Type | Best For | Field Structure |
|-----------|----------|-----------------|
| Basic | Simple Q&A facts | Front, Back |
| Basic (reversed) | Bidirectional learning (vocabulary) | Front, Back |
| Cloze | Sentences with fill-in-blank | Text with {{c1::deletions}} |
| Image Occlusion | Diagrams, anatomy, maps | Image with masked regions |

## Tags Strategy
- Use hierarchical tags: `programming::python::syntax`
- Tag by topic, source, and difficulty
- Tag volatile information with dates: `2024-data`
- Use tags to filter review sessions

## When to Use Different Card Types

**Use Basic cards for:**
- Definitions and terminology
- Simple factual associations
- Command syntax and shortcuts

**Use Cloze cards for:**
- Converting textbook sentences
- Learning sequences/processes
- Fill-in-the-blank from documentation

**Use Image Occlusion for:**
- Architecture diagrams
- Flowcharts and processes
- Geographic/spatial information
