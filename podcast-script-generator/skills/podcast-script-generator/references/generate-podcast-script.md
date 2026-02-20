# Generate Podcast Script

## Overview

Generate AI-powered podcast scripts optimized for natural conversation flow using AWS Bedrock. The generated scripts can be used as input for podcast audio generation workflows.

## Parameters

### Script Generation Parameters
- **script_style** (required): "tech_discussion", "solo_expert", "business_panel", or "interview"
  - Determines default speaker configuration and audio style
- **target_duration** (required): Duration (e.g., "5 minutes", "10 minutes", "00:15:00")
  - Used for script generation word count calculation (~175 words per minute default, configurable via speech_tempo)
- **content_topic** (required): Subject matter for script generation
  - Provides context and focus for AI-generated script
- **listener_expertise** (required): "beginner", "intermediate", "advanced", or "expert"
  - **beginner**: Assumes no prior knowledge, includes basic concepts and definitions, uses simple analogies
  - **intermediate**: Assumes familiarity with basics, focuses on practical application and common patterns
  - **advanced**: Assumes strong foundation, explores edge cases, performance optimization, architectural decisions
  - **expert**: Assumes deep expertise, focuses on nuanced trade-offs, advanced internals, cutting-edge approaches
  - This parameter determines the starting point and depth of technical content
- **speaker_configuration** (optional): Speaker names and voice characteristics
  - Default configurations provided based on `script_style`:
    - **tech_discussion**: Dr. Alex Chen (analytical) and Jamie Rodriguez (practical)
    - **solo_expert**: Professor Sarah Kim (teaching style)
    - **business_panel**: Marcus Thompson (strategist), Elena Vasquez (entrepreneur), Johnny Bing (contrarian)
    - **interview**: Dynamic Q&A between host and expert
    - **system_design_interview**: Dr. Maya Patel (interviewer) and Jordan Chen (principal engineer candidate)
  - Override with custom configuration if desired
- **speech_tempo** (optional): Words per minute for speech pacing (default: 175)
  - **165-175 WPM**: Brisk conversational pace, engaged discussion style
  - **175-185 WPM**: Fast-paced conversation, energetic and dynamic
  - **185-205 WPM**: Very fast presentation pace, urgent or highly energetic delivery
  - Used to calculate target word count from duration: `target_duration_minutes × speech_tempo`
  - Based on empirical testing with TTS audio generation (aligns with generate-podcast-audio.md)
  - **Note:** Word counts exclude "Speaker N:" prefixes (only actual spoken dialogue counted)
- **speaker_role_references** (optional): Additional guidance documents or context for speaker roles
  - Provide file paths, URLs, or text describing specific expertise, personality traits, or speaking style
  - Examples: "Speaker 1 has 10 years healthcare industry experience", "Use casual Gen-Z communication style", "Speaker 2 is skeptical of cloud-native approaches"
  - These references will be incorporated into script generation to enhance speaker authenticity and consistency

**Constraints:**
- You MUST ask for all required parameters upfront in a single prompt
- You MUST use default speaker configurations when speaker_configuration not provided
- You MUST map script_style to appropriate default speaker_configuration and audio parameters
- You MUST tailor content depth and starting assumptions to match listener_expertise level

## ⚠️ CRITICAL: Script Format Requirements ⚠️

**🚨 PODCAST GENERATION WILL FAIL IF SCRIPT IS NOT IN EXACT FORMAT 🚨**

The script file MUST be in this EXACT format or podcast generation will fail:

### **MANDATORY FORMAT RULES:**

1. **NO HEADERS** - Do not include ANY markdown headers (# ## ###)
2. **NO COMMENTS** - Do not include ANY comments or notes
3. **NO SECTION TITLES** - Do not include ANY section dividers or titles
4. **ONLY DIALOG LINES** - Each line MUST start with "Speaker <N>: " where N is a number (1, 2, 3, etc.)

### **✅ CORRECT FORMAT EXAMPLE:**

```
Speaker 1: Welcome to today's discussion about AWS Lambda optimization.
Speaker 2: Thanks for having me. I'm excited to dive into this topic.
Speaker 1: Let's start with cold starts. What's the biggest misconception?
Speaker 2: Many developers think cold starts are inevitable, but there are several strategies to minimize them.
Speaker 1: Can you walk us through those strategies?
Speaker 2: Absolutely. First, let's talk about provisioned concurrency.
```

### **❌ INCORRECT FORMAT EXAMPLES:**

**WRONG - Contains headers:**
```
# AWS Lambda Discussion

Speaker 1: Welcome to today's discussion.
```

**WRONG - Contains section titles:**
```
## Introduction

Speaker 1: Welcome to today's discussion.

## Main Discussion

Speaker 2: Thanks for having me.
```

**WRONG - Contains comments:**
```
Speaker 1: Welcome to today's discussion.
// This is where we discuss cold starts
Speaker 2: Thanks for having me.
```

**WRONG - Missing "Speaker N:" prefix:**
```
Alex: Welcome to today's discussion.
Jamie: Thanks for having me.
```

**WRONG - Inconsistent speaker numbering:**
```
Speaker A: Welcome to today's discussion.
Speaker B: Thanks for having me.
```

### **VALIDATION CHECKLIST:**

Before running podcast generation, verify:
- [ ] Every single line starts with "Speaker <N>: " (where N is 1, 2, 3, etc.)
- [ ] There are NO headers anywhere in the file
- [ ] There are NO comments anywhere in the file
- [ ] There are NO section titles or dividers anywhere in the file
- [ ] File contains ONLY dialog lines in "Speaker <N>: " format

**⚠️ IF ANY OF THESE RULES ARE VIOLATED, PODCAST GENERATION WILL FAIL ⚠️**

## Step 1: Generate Podcast Script Content

**🚨 CRITICAL FORMAT REQUIREMENT 🚨**
Generated scripts MUST follow the exact format specified above:
- **NO HEADERS, NO COMMENTS, NO SECTION TITLES**
- **ONLY "Speaker <N>: " dialog lines**
- Failure to follow this format will cause podcast generation to fail

**Constraints:**
- You MUST use AI to generate script when input_file_path not provided
- You MUST incorporate script_style into generation prompt
- You MUST target specified duration using speech_tempo (default: 175 words per minute)
- You MUST include clear briefing, duration target, content topic, listener expertise, speaker configuration, and any speaker_role_references in prompt
- You MUST tailor content depth to listener_expertise level:
  - **beginner**: Define terms, explain concepts from first principles, avoid jargon or explain it when used
  - **intermediate**: Skip basic definitions, focus on practical patterns and real-world application
  - **advanced**: Assume strong foundation, dive into optimization, edge cases, and architectural trade-offs
  - **expert**: Focus on nuanced debates, cutting-edge techniques, internal implementation details
- You MUST save generated script to file with .txt extension in the EXACT format required (Speaker N: dialog only)
- You MUST use the filename format: `<topic>-script-<timestamp>.txt` where timestamp is `YYYYMMDDHHmmss` format without separators (e.g., `lambda-best-practices-script-20250131143000.txt`)
- You MUST validate script meets length requirements AND format requirements
- **Script Length Verification:**
  - **CRITICAL: Count ONLY spoken dialogue** - Use the bundled Python script to exclude "Speaker N:" prefixes:
    ```bash
    python scripts/calculate_podcast_metrics.py count-words --file script.txt
    ```
  - **You MUST count the actual spoken words** in the generated script after creation (excluding "Speaker N:" prefixes)
  - **You MUST verify** the word count matches the target duration calculation: `target_duration_minutes × 175 words per minute`
  - **Example targets**: 5 min = 875 words minimum, 10 min = 1,750 words minimum, 15 min = 2,625 words minimum, 20 min = 3,500 words minimum
  - **If the script is too short** (less than 90% of target word count), you MUST extend it by adding more details:
    - Add deeper explanations of concepts
    - Include additional examples or use cases
    - Expand on technical details or business implications
    - Add more conversational elements (follow-ups, elaborations, tangents that enhance understanding)
    - Incorporate additional practical insights or real-world scenarios
  - **You MUST report** the final word count and confirm it meets the target duration before completing
- You MUST NOT include ANY markdown headers, comments, or section titles in generated script
- You SHOULD structure with clear speaker indicators using "Speaker 1:", "Speaker 2:", etc.
- You SHOULD include natural transitions for multi-speaker formats

**🚨 CRITICAL: Post-Generation Speaker Assignment Review 🚨**

After generating the script, you MUST perform a thorough review to ensure speaker assignments match their personas:

**Primary Issue to Detect: Speaker Number/Persona Misalignment**
- **Problem**: Speaker numbers get mixed up with personas mid-script (e.g., Speaker 1 is "Dr. Alex Chen (analytical)" but suddenly speaks like "Jamie Rodriguez (practical)")
- **Why it matters**: Breaks continuity, confuses listeners, makes voices/personalities inconsistent

**Validation Steps:**

1. **Create Speaker Persona Reference Table** from speaker_configuration:
   - Speaker 1: [Name] - [Personality traits] - [Expertise domain] - [Communication style]
   - Speaker 2: [Name] - [Personality traits] - [Expertise domain] - [Communication style]
   - (Continue for all speakers)

2. **Review Every "Speaker N:" Line**:
   - Read the dialogue content
   - Ask: "Does this match Speaker N's assigned persona?"
   - Check for personality consistency (analytical vs. practical vs. contrarian vs. teaching)
   - Check for expertise alignment (technical depth, business focus, educational approach)
   - Check for style consistency (formal vs. casual, skeptical vs. enthusiastic, cautious vs. risk-taking)

3. **Flag Misalignments**:
   - If Speaker 1 (analytical) suddenly makes impulsive/practical statements → **PERSONA SWITCH DETECTED**
   - If Speaker 2 (practical) suddenly delivers theoretical analysis → **PERSONA SWITCH DETECTED**
   - If a contrarian suddenly agrees without challenge → **PERSONA SWITCH DETECTED**

4. **Fix Detected Issues**:
   - **Option A**: Swap speaker numbers to match content (change "Speaker 1:" to "Speaker 2:" and vice versa)
   - **Option B**: Rewrite dialogue to match assigned speaker's persona
   - **Option C**: If widespread misalignment, regenerate the affected section

5. **Additional Checks**:
   - Verify no speaker responds to themselves consecutively
   - Ensure dialogue flows logically between speakers
   - Confirm all speakers maintain their assigned expertise domains

**Example Issue:**
```
Speaker 1: We need to carefully analyze the performance implications before proceeding. [✅ ANALYTICAL - CORRECT]
Speaker 2: Let's just ship it and see what happens! [✅ PRACTICAL - CORRECT]
Speaker 1: Yeah, I love moving fast and breaking things! [❌ PERSONA SWITCH - Should be Speaker 2]
Speaker 2: Actually, we should run comprehensive benchmarks first. [❌ PERSONA SWITCH - Should be Speaker 1]
```

**After fixing:**
```
Speaker 1: We need to carefully analyze the performance implications before proceeding. [✅]
Speaker 2: Let's just ship it and see what happens! [✅]
Speaker 2: Yeah, I love moving fast and breaking things! [✅]
Speaker 1: Actually, we should run comprehensive benchmarks first. [✅]
```
- **CRITICAL for multi-speaker formats (tech_discussion, business_panel, interview)**: You MUST create distinct personalities for each speaker to avoid monotonous dialogue
- **CRITICAL for all formats**: You MUST include natural conversation elements to avoid robotic delivery
- **CRITICAL for multi-speaker formats**: You MUST ensure gender diversity in speaker selection - avoid all-men or all-women speaker setups unless using solo_expert mode

**Universal Human-Like Dialogue Requirements (APPLIES TO ALL STYLES):**

**🚨 CRITICAL TTS WARNING: Script Content Restrictions 🚨**

- **MUST NOT include stage directions or TTS directives**: Words like "pause", "[pause]", "*pause*", "[music]", "[sound effect]", "[laughter]" will be read aloud by TTS
- **MUST NOT include action descriptions**: Phrases like "[takes a breath]", "[sighs]", "[chuckles]" will be spoken literally
- **Use natural language instead**: Instead of writing "[pause]", write "Well..." or "Let me think about that..." or "Hmm..."
- **Use ellipses for pauses**: "..." represents natural pauses without being spoken
- **MUST convert mathematical notation to spoken equivalents**: TTS engines cannot properly vocalize formulas or symbols
  - Greek letters: α → "alpha", β → "beta", θ → "theta", λ → "lambda", σ → "sigma", μ → "mu", π → "pi", Σ → "sum", Δ → "delta"
  - Mathematical operators: × → "times" or "multiplied by", ÷ → "divided by", ≈ → "approximately", ≤ → "less than or equal to", ≥ → "greater than or equal to", ≠ → "not equal to", √ → "square root of"
  - Formulas: E=mc² → "E equals m c squared", O(n log n) → "O of n log n", x² → "x squared", 2ⁿ → "two to the n"
  - Fractions: ½ → "one half", ¾ → "three quarters", a/b → "a over b" or "a divided by b"

**🚨 CRITICAL: Review for Repetitive Phrases 🚨**

After generating the script, you MUST search for repeated phrases and replace with varied alternatives:

- **Check for overused responses**: Common culprits include "Exactly!", "Absolutely!", "That's a great point!", "I see what you mean"
- **Use diverse alternatives**:
  - Agreement: "That's right", "Fair enough", "You're onto something", "That resonates", "I'm with you on that"
  - Acknowledgment: "Good point", "I hadn't thought of that", "That's worth considering", "Hmm, tell me more"
  - Skepticism: "I'm not so sure", "That's debatable", "I see it differently"
  - Excitement: "That's fascinating!", "Wow!", "I love that example", "That's compelling"
- **Limit filler phrases**: No phrase ("You know", "I mean", "At the end of the day") should appear more than 2-3 times total

These requirements MUST be incorporated into ALL podcast scripts regardless of format:

- **MUST include natural pauses and verbal thinking**: "...", "Hmm...", "Right...", "Well...", "Let me think about that...", "Interesting..."
- **MUST include emotional responses**: Show excitement, skepticism, surprise, enthusiasm, concern, curiosity, thoughtfulness, passion
- **MUST include light humor**: Occasional jokes, witty observations, self-deprecating comments, relatable analogies
- **MUST include conversational transitions**: "Before we move on...", "Let me give you another example...", "Here's where it gets interesting...", "Now, let's think about this..."
- **MUST include verbal acknowledgments**: "That's a great point", "I see what you mean", "Actually...", "That's a fair point", "I'm not so sure about that", "Building on that..."
- **SHOULD include personal elements**: Anecdotes, relatable examples, business/technical experiences when relevant
- **SHOULD vary delivery patterns**: Mix sentence lengths, speech patterns, pacing (slow for complex ideas, faster for reviews)
- **SHOULD show genuine engagement**: Demonstrate passion for subject, empathy with challenges, authentic curiosity

**Educational Psychology and Attention Optimization:**

To maximize learning retention and maintain listener engagement throughout:

**Memory and Retention (CRITICAL for Educational Impact):**
- **MUST use Spaced Repetition**: Introduce key concepts early, revisit with examples mid-podcast, recap at end
- **MUST sequence Concrete-to-Abstract**: Start with relatable examples or scenarios before diving into technical theory
- **MUST include Memorable Anchors**: Vivid analogies, surprising statistics, or mnemonic devices for complex concepts
  - Examples: "Think of Lambda functions like restaurant kitchens...", "95% of developers make this one mistake...", "Remember it as C-A-R: Caching, Async, Retry"
- **MUST leverage Primacy/Recency**: Strongest hooks in first 60 seconds, clearest takeaways in last 60 seconds
  - Opening should grab attention with most compelling insight or intriguing question
  - Closing should recap 2-3 key takeaways (not everything) for maximum retention

**Attention Management (CRITICAL for Engagement):**
- **MUST create Curiosity Gaps**: Pose intriguing questions before answering them
  - Examples: "Here's what's surprising...", "Wait until you hear...", "The most common mistake is..."
  - Let tension build briefly before revealing answers - avoid immediate resolution
- **MUST vary Emotional Energy**: Match enthusiasm level to content importance
  - High energy for exciting breakthroughs, surprising insights, compelling revelations
  - Quieter, thoughtful moments for complex explanations requiring concentration
  - Build-ups before important points: "Now here's the really important part..."
- **SHOULD include Pattern Interrupts**: Break monotony with strategic disruptions
  - Sudden agreement after disagreement: "You know what? You're absolutely right."
  - Change of topic with acknowledgment: "Let's shift gears completely..."
  - Meta-commentary: "I just realized we've been talking about X, but the real issue is Y..."
  - Unexpected humor or surprising facts that jolt attention back
- **SHOULD use Strategic Teasing**: Preview interesting content: "We'll get to [surprising fact] in a few minutes, but first..."

**Active Learning Elements:**
- **SHOULD include Listener Pause Points**: Invite mental participation without expecting verbal response
  - Examples: "Think about your own codebase - where would this apply?", "Pause for a second and guess what happened next...", "If you were designing this, what would you do?"
- **MUST challenge Misconceptions Explicitly**: Create productive cognitive dissonance
  - Examples: "Most people think X, but actually Y...", "I used to believe this until I discovered...", "Here's where everyone gets it wrong..."
  - This enhances retention by disrupting existing mental models
- **SHOULD use Callbacks**: Reference earlier points to create narrative coherence and reinforce concepts
  - Examples: "Remember when you mentioned cold starts earlier? This connects to that...", "This is exactly what Elena was warning us about..."

**Cognitive Load Management:**
- **MUST apply Chunking**: Break complex topics into 3-5 distinct sub-concepts per segment (aligns with working memory capacity of 4±1 items)
  - Don't overwhelm with 10 different strategies at once - group into digestible chunks
- **MUST provide Advance Organizers**: Preview structure to help listeners build mental frameworks
  - Examples: "We're going to cover three main strategies...", "There are two types of cold starts...", "By the end of this, you'll understand..."
- **SHOULD include Clear Signposting**: Number items explicitly, mark transitions clearly
  - Examples: "First...", "Second...", "The key takeaway is...", "Let's summarize where we are..."
- **SHOULD use Progressive Disclosure**: Layer complexity for different knowledge levels
  - Level 1: Simple explanation anyone can understand
  - Level 2: Add nuance and edge cases for intermediate listeners
  - Level 3: Technical depth for experts who want internals
  - Signal these layers: "At the basic level..." → "Now if we dig deeper..." → "For those who really want to understand the internals..."

**Social Proof and Authority (Use Sparingly but Strategically):**
- **SHOULD reference External Validation**: Build credibility while maintaining conversational flow
  - Examples: "The AWS documentation actually recommends...", "I was skeptical until I saw three different teams...", "Netflix solved this by...", "This pattern comes from the Gang of Four..."
- **SHOULD include Personal Stakes**: Make concepts concrete with real consequences
  - Examples: "This cost our team three days of debugging...", "When I first encountered this, I was completely confused...", "This one change reduced our AWS bill by 40%..."

**The Von Restorff Effect (Making Critical Points Stand Out):**
- **MUST make Critical Points Distinctive**: Use verbal emphasis to ensure key concepts are memorable
  - Examples: "This is crucial...", "This is the thing that trips everyone up...", "If you remember nothing else from this podcast...", "Everything else is negotiable, but THIS you must get right..."
  - Create contrast to make important information stand out from surrounding content

**Content Freshness and Topic Repetition:**
- **MUST avoid unintentional topic repetition**: Each substantive point should appear once in its primary location
  - If a concept is explained in detail in one segment, do not re-explain it in another segment
  - Cross-reference instead: "As we discussed earlier..." or "Building on what we covered..."
- **Intentional repetition IS appropriate** for:
  - **Agenda/preview statements** (beginning): "Today we'll cover X, Y, and Z"
  - **Summary/recap statements** (end): "To wrap up, we discussed X, Y, and Z"
  - **Spaced repetition callbacks**: Brief references to reinforce key concepts (not full re-explanations)
- **Distinguish between**:
  - ❌ Redundant coverage: Same information presented twice at similar depth
  - ✅ Strategic callbacks: Brief references that reinforce without re-teaching

**Format-Specific Additions:**

**Multi-Speaker Formats (tech_discussion, business_panel, interview):**
- **MUST include speaker interactions**: Interruptions, building on each other's ideas, interjections when strongly agreeing/disagreeing
- See "Host Dynamics and Role Variation" section below for detailed requirements on avoiding fixed roles and creating engaging debates

**Solo Expert Format (solo_expert):**
- **MUST include rhetorical questions**: "You might be wondering...", "What does this mean for us?", "How does this work?"
- **MUST include teaching empathy**: "I know this can seem confusing at first...", recognize learning challenges
- **SHOULD include verbal signposts**: "This is really important...", "The key takeaway here is..."

**Interview Format (interview):**
- **MUST include natural follow-ups**: Host reacts with surprise, curiosity ("Wow, that's fascinating!", "Can you elaborate?")
- **MUST include expert conversational responses**: Not formal lectures, but engaging explanations
- **SHOULD include clarifying exchanges**: Expert asks host for clarification, natural tangents steered back on topic

**Host Dynamics and Role Variation (Multi-Speaker Formats):**

To avoid monotonous dialogue patterns, scripts MUST incorporate dynamic host interactions:

**✅ GOOD DYNAMICS - Varied Roles:**
- Speaker 1 asks a question → Speaker 2 answers → Speaker 1 challenges the answer → Speaker 2 acknowledges and refines
- Speaker 2 makes a statement → Speaker 1 builds on it with an example → Speaker 2 expresses agreement but adds a caveat
- Speaker 1 introduces topic → Speaker 2 shares opinion → Speaker 1 offers contrasting view → They find middle ground
- Speakers interrupt each other naturally when excited or disagreeing (in moderation)
- Both speakers contribute ideas, questions, and insights throughout

**❌ BAD DYNAMICS - Fixed Roles:**
- Speaker 1 only asks questions for entire podcast while Speaker 2 only provides answers
- Speaker 1 dominates with long monologues while Speaker 2 only interjects with "That's interesting" or "Tell me more"
- Speakers always agree with each other without any intellectual tension
- One speaker is passive throughout with minimal contribution

**Implementing Intellectual Tension (Respectfully):**
- **Mild disagreement**: "I see your point, but I think there's another way to look at this..."
- **Challenging assumptions**: "Wait, are we sure that's always true? What about edge cases?"
- **Alternative perspectives**: "That works for large organizations, but smaller teams might struggle with..."
- **Constructive pushback**: "I'm not entirely convinced. Can you walk me through why you think that?"
- **Evolving positions**: Speakers can change their minds when presented with compelling arguments

**Balancing Clarity with Dynamism:**
- Disagreements should be substantive but not confusing - maintain topic coherence
- Arguments should advance the conversation, not derail it
- After debate, synthesize insights so listeners understand key takeaways
- Use phrases like "Let me summarize where we've landed..." or "So we agree that... but differ on..."

**Script Generation Prompt Patterns:**

**tech_discussion:**
```
Create engaging technical discussion about [TOPIC] for [DURATION] podcast.

REQUIREMENTS:
- Format: Dr. Alex Chen (analytical) and Jamie Rodriguez (practical)
- Duration: [DURATION] (~[WORD_COUNT] words)
- Focus: Practical insights, real-world applications, technical depth
- Audience: [EXPERTISE_LEVEL] developers and technical professionals
- Structure: [SEGMENT_COUNT] natural segments

EXPERTISE LEVEL ADAPTATION (CRITICAL):
- Listener expertise: [EXPERTISE_LEVEL]
- beginner: Define all terms, explain "what is X", use simple analogies, avoid assuming prior knowledge
- intermediate: Skip basic definitions, focus on "how to use X", common patterns, practical trade-offs
- advanced: Assume strong foundation, explore "why X over Y", performance tuning, architectural decisions
- expert: Focus on "when X fails", internal implementation, cutting-edge techniques, nuanced debates

PERSONALITY REQUIREMENTS (CRITICAL):
- Speaker 1 (Dr. Alex Chen): Analytical, methodical, detail-oriented, tends to be cautious and thorough
- Speaker 2 (Jamie Rodriguez): Practical, hands-on, solution-focused, optimistic about new approaches
- Speakers MUST have contrasting personalities and perspectives to create engaging dialogue
- Include natural disagreements, different viewpoints, and personality-driven reactions
- Apply all requirements from "Host Dynamics and Role Variation" section (avoid fixed roles, include intellectual tension, balance participation)

CONSTRAINTS:
- MUST include speaker names before each turn
- MUST maintain conversational tone
- MUST incorporate technical depth appropriate to expertise level
- MUST NOT waste time on concepts below listener's expertise level
- SHOULD include practical examples and code references appropriate to audience
```

**solo_expert:**
```
Create educational explanation of [TOPIC] for [DURATION] podcast.

REQUIREMENTS:
- Format: Professor Sarah Kim (teaching style)
- Duration: [DURATION] (~[WORD_COUNT] words)
- Focus: Breaking down complex concepts
- Audience: [EXPERTISE_LEVEL] learners seeking comprehensive understanding
- Structure: [SEGMENT_COUNT] clear chapters

EXPERTISE LEVEL ADAPTATION (CRITICAL):
- Listener expertise: [EXPERTISE_LEVEL]
- beginner: Start from zero, define everything, use everyday analogies, explain why topic matters
- intermediate: Build on assumed basics, focus on deeper understanding and practical application
- advanced: Explore sophisticated implications, compare approaches, discuss optimization strategies
- expert: Analyze cutting-edge research, debate controversial design decisions, examine internals

PERSONALITY REQUIREMENTS (CRITICAL):
- Speaker (Professor Sarah Kim): Patient educator, encouraging, enthusiastic about teaching, uses relatable examples
- Personality should come through in teaching style - warm, accessible, genuinely excited about the subject
- Teaching style should match expertise level (more foundational for beginners, more exploratory for experts)

CONSTRAINTS:
- MUST use teaching methodology with clear explanations
- MUST include analogies and examples appropriate to expertise level
- MUST maintain engaging, patient tone
- MUST NOT waste time on concepts significantly below listener's expertise level
- SHOULD build concepts progressively from listener's assumed knowledge baseline
```

**business_panel:**
```
Create business analysis of [TOPIC] for [DURATION] panel discussion.

REQUIREMENTS:
- Format: Marcus Thompson (strategist), Elena Vasquez (entrepreneur), Johnny Bing (contrarian)
- Duration: [DURATION] (~[WORD_COUNT] words)
- Focus: Market implications, strategic insights, competitive analysis
- Audience: [EXPERTISE_LEVEL] business professionals
- Structure: [SEGMENT_COUNT] discussion segments

EXPERTISE LEVEL ADAPTATION (CRITICAL):
- Listener expertise: [EXPERTISE_LEVEL]
- beginner: Explain business fundamentals, define industry terms, focus on "what is happening and why"
- intermediate: Assume business literacy, focus on strategic implications and practical applications
- advanced: Analyze complex market dynamics, competitive positioning, sophisticated strategy
- expert: Debate nuanced trade-offs, emerging trends, unconventional approaches, executive-level decisions

PERSONALITY REQUIREMENTS (CRITICAL):
- Speaker 1 (Marcus Thompson): Strategic, analytical, focused on long-term planning, measured and diplomatic
- Speaker 2 (Elena Vasquez): Entrepreneurial, risk-taking, optimistic, passionate about innovation
- Speaker 3 (Johnny Bing): Contrarian, skeptical, plays devil's advocate, questions conventional wisdom
- Speakers MUST have distinctly different viewpoints and personalities creating dynamic debate
- Include healthy disagreements, rebuttals, and challenging of each other's assumptions
- Apply all requirements from "Host Dynamics and Role Variation" section with special attention to alliance shifts and balancing three voices

CONSTRAINTS:
- MUST include speaker names before each contribution
- MUST provide different perspectives at appropriate sophistication level
- MUST focus on actionable business intelligence
- MUST NOT waste time on business concepts below listener's expertise level
- SHOULD include market data and competitive insights appropriate to audience
```

**interview:**
```
Create interview about [TOPIC] for [DURATION] podcast.

REQUIREMENTS:
- Format: Dynamic Q&A between host and expert
- Duration: [DURATION] (~[WORD_COUNT] words)
- Focus: Question-and-answer with deep exploration
- Audience: [EXPERTISE_LEVEL] interested listeners
- Structure: [SEGMENT_COUNT] major question areas

EXPERTISE LEVEL ADAPTATION (CRITICAL):
- Listener expertise: [EXPERTISE_LEVEL]
- beginner: Host asks foundational questions, expert explains from basics with clear examples
- intermediate: Host assumes foundational understanding, focuses on practical "how-to" and common challenges
- advanced: Host asks sophisticated questions about edge cases, optimization, and design decisions
- expert: Host poses challenging questions about implementation details, trade-offs, and cutting-edge approaches

PERSONALITY REQUIREMENTS (CRITICAL):
- Speaker 1 (Host): Curious, engaging interviewer who asks probing questions, genuinely interested in learning
- Speaker 2 (Expert): Knowledgeable but approachable, passionate about subject, good storyteller
- Dynamic should feel like genuine conversation, not scripted Q&A
- Host should react naturally to expert's answers (surprise, interest, follow-up questions)
- Apply all requirements from "Host Dynamics and Role Variation" section, especially breaking Q&A loops and balancing power dynamics

CONSTRAINTS:
- MUST include speaker names before each turn
- MUST structure as engaging Q&A at appropriate expertise level
- MUST allow natural clarifications
- MUST NOT ask questions that are too basic for listener's expertise level
- SHOULD vary question types and depth based on audience sophistication
```

**system_design_interview:**
```
Create realistic principal-level system design interview for [TOPIC] with 50-minute duration.

REQUIREMENTS:
- Format: Dr. Maya Patel (interviewer) and Jordan Chen (principal engineer candidate)
- Duration: 50 minutes (~8,750 words at 175 WPM)
- Focus: Candidate-driven system design discussion demonstrating principal-level expertise
- Audience: Expert/principal-level technical professionals learning from example
- Interview Level: ALWAYS principal-level (this format does not adapt to different expertise levels)
- Structure: Minimal intro (2 min), candidate-led design (38 min), deep questions (8 min), feedback (2 min)

TIME ALLOCATION (CRITICAL):
- 0-2 min: Brief intro and problem statement (no lengthy pleasantries)
- 2-40 min: Candidate drives discussion, covering all aspects systematically
- 40-48 min: Interviewer asks 3-4 deep technical questions on specific topics
- 48-50 min: Brief constructive feedback (2-3 key strengths, 1-2 areas for growth)

CANDIDATE BEHAVIOR (CRITICAL - PRINCIPAL LEVEL):
- Candidate speaks 85-90% of the time, driving the conversation
- Demonstrates time management: "I have 40 minutes, so I'll spend 5 on requirements..."
- Covers all essential aspects without prompting
- Clusters all clarifying questions upfront (first 2-4 min): asks 3-5 questions about scale, constraints, objectives before diving into design
- Discusses trade-offs explicitly: "We could use X which gives us Y benefit but Z drawback, or we could..."
- Explains reasoning for every major design decision: not just WHAT to build but WHY ("The reason this matters is...", "This ensures...")
- Shows principal-level depth: anticipates bottlenecks, discusses real-world operational concerns, references industry patterns, includes concrete numbers (scale, latency SLAs, dimensions)
- Uses clear transition language:
  - "Now let me talk about [topic]" for major topic changes
  - "Let me walk through [X] in detail" for deep dives
  - Explicit enumeration: "First..., Second..., Third..." for complex explanations
- Maintains narrative flow with periodic engagement checks:
  - Permission-seeking at natural breakpoints (every 5-8 min): "Should I continue with [topic]?"
  - Understanding checks after complex concepts: "Does that make sense?" or "Are you following so far?"
  - Self-correction when recognizing gaps: "Before I continue with X, let me dive deeper into Y, which is foundational"

INTERVIEWER BEHAVIOR (CRITICAL):
- Minimal interruption during candidate-led portion with varied brief acknowledgments:
  - Agreement: "That makes sense", "Yes, that's solid", "That's correct", "Good"
  - Encouragement: "Continue", "Go ahead", "Please continue", "Yes, please"
  - Validation: "Good question", "That's exactly right", "Excellent"
  - Active listening: "I'm following", "I see", "Yes"
- Takes notes silently (implied, not spoken)
- Asks follow-up questions only if candidate misses critical aspects
- Deep-dive questions (40-48 min) should probe specific topics from the interview: edge cases, failure scenarios, optimization, specific technology choices, operational concerns
- Candidate response to deep-dive should demonstrate multi-faceted breakdown: multiple dimensions or aspects (2-3), specific techniques per dimension (3-5), acknowledgment of trade-offs, context-dependent recommendations
- Structured feedback pattern (48-50 min):
  - Overall assessment: "Overall, this was a [strong/solid] performance"
  - Specific strengths (3-4 points): "You demonstrated X", "I liked that you Y", "Your discussion of Z was excellent" - reference actual decisions from interview
  - Areas for improvement (2-3 points): "First, you could have...", "Second, while you mentioned X..." - be specific and constructive
  - Optional: Hiring signal if appropriate: "If I were making a hiring decision, I'd be inclined to move you forward"

TECHNICAL DEPTH AND SPECIFICITY (PRINCIPAL LEVEL):
- Include concrete numbers: scale ("100 million daily active users", "thousands of QPS"), latency ("P95 under 50ms", "P99 under 150ms"), dimensions ("128 or 256 dimensions"), thresholds ("1,000 to 5,000 candidates")
- Reference specific technologies and algorithms: name actual tools, frameworks, algorithms rather than generic descriptions
- Include relevant formulas or calculations where appropriate
- This level of specificity distinguishes principal from senior candidates

PERSONALITY REQUIREMENTS (CRITICAL):
- Speaker 1 (Dr. Maya Patel): Professional senior engineering manager, observant, takes notes, asks thoughtful probing questions, provides balanced feedback
- Speaker 2 (Jordan Chen): Confident principal engineer, systematic thinker, strong communicator, demonstrates deep technical knowledge and production experience
- Both speakers are professional role models - respectful, constructive, collaborative
- No unnecessary small talk or time-wasting - maximizes learning value

REALISM REQUIREMENTS (CRITICAL):
- Interview should feel authentic, not rehearsed
- Candidate may pause to think: "Let me think about that for a moment..."
- Interviewer should ask natural follow-ups based on candidate's statements
- Include realistic moments: candidate drawing on whiteboard (implied: "Let me sketch this out..."), thinking through edge cases, catching their own mistakes

CONTENT OPTIMIZATION:
- Consider using related skills to enhance system design topic depth (e.g., if designing ML system, reference ML system design patterns; if designing distributed system, reference distributed systems principles)
- This ensures technical accuracy and principal-level depth

CONSTRAINTS:
- MUST demonstrate principal-level system design competency
- MUST cover: requirements, scale, APIs, data model, architecture, trade-offs, scalability, fault tolerance, monitoring
```

## Examples of Good vs. Bad Host Dynamics

### ❌ BAD: Fixed Roles Pattern (Tech Discussion)

```
Speaker 1: Welcome everyone. Let's talk about Kubernetes. What is it?
Speaker 2: Kubernetes is a container orchestration platform that automates deployment, scaling, and management.
Speaker 1: Interesting. What are the main benefits?
Speaker 2: The main benefits include automated rollouts, self-healing, and horizontal scaling capabilities.
Speaker 1: I see. How does it compare to Docker Swarm?
Speaker 2: Kubernetes is more feature-rich and has better community support compared to Docker Swarm.
Speaker 1: Good to know. What about the learning curve?
Speaker 2: The learning curve is steep initially, but it's worth the investment for large-scale deployments.
```

**Problems:**
- Speaker 1 only asks questions (interviewer role)
- Speaker 2 only provides answers (expert role)
- No debate or differing perspectives
- Monotonous pattern throughout
- No personality differences showing through

### ✅ GOOD: Dynamic Interaction Pattern (Tech Discussion)

```
Speaker 1: So we need to talk about Kubernetes. I've been using it for two years now, and honestly, I still think the learning curve is brutal.
Speaker 2: You know what? I actually disagree. I think people overstate how hard Kubernetes is. If you start with the basics and don't try to be a cluster admin on day one...
Speaker 1: Wait, hold on. Are you saying it's easy? Because I've seen entire teams struggle with it.
Speaker 2: Not easy, but manageable. What were they struggling with specifically?
Speaker 1: Configuration complexity, mainly. YAML files everywhere, and one wrong indentation breaks everything.
Speaker 2: Okay, that's fair. The YAML situation is... not ideal. But there are tools now that help with that. Have you tried Helm?
Speaker 1: I have, and Helm has its own learning curve! Now you're managing Helm charts on top of Kubernetes configs.
Speaker 2: True, true. But think about it this way - would you rather manage individual YAML files for 50 microservices, or template them with Helm?
Speaker 1: When you put it that way... yeah, Helm makes sense. Though I still wish there was a simpler approach for smaller teams.
Speaker 2: Actually, that's where I think k3s or even Docker Compose might be better fits. Not everything needs full Kubernetes.
Speaker 1: Now that's something I can agree with. We've been forcing Kubernetes on projects that don't need it.
```

**Strengths:**
- Both speakers share opinions and experiences
- Natural disagreement creates engagement
- Speakers ask each other questions
- Roles trade throughout (questioner, explainer, skeptic)
- Personalities shine through (Speaker 1 more cautious, Speaker 2 more optimistic)
- They reach common ground after debating

### ❌ BAD: No Intellectual Tension (Business Panel)

```
Speaker 1: Let's discuss the new AI regulation. I think it's necessary for safety.
Speaker 2: I completely agree. Safety is paramount.
Speaker 3: Yes, I agree with both of you. This is definitely needed.
Speaker 1: The compliance costs will be worth it.
Speaker 2: Absolutely, compliance is a small price to pay.
Speaker 3: I couldn't agree more. This is great regulation.
```

**Problems:**
- Everyone agrees on everything
- No debate or alternative perspectives
- Listener learns nothing from lack of tension
- No personality distinction
- Boring and predictable

### ✅ GOOD: Substantive Debate (Business Panel)

```
Speaker 1: I think this AI regulation is necessary. We can't have unchecked AI systems making critical decisions.
Speaker 2: Marcus, I hear you on safety, but have you looked at the compliance costs? For startups, this could be a death sentence.
Speaker 3: Elena, I'm going to push back on both of you. The regulation doesn't go far enough. We need algorithmic transparency requirements.
Speaker 1: Johnny, transparency sounds great in theory, but proprietary algorithms are how companies maintain competitive advantage.
Speaker 2: Exactly! If we force full transparency, we're basically handing our IP to competitors.
Speaker 3: But without transparency, how do we prevent discriminatory AI? We've already seen biased hiring algorithms.
Speaker 1: That's... actually a fair point. Maybe we need transparency specifically for high-risk applications like hiring or lending.
Speaker 2: Okay, I could support that. Targeted transparency for high-risk use cases, lighter requirements for low-risk applications.
Speaker 3: Now we're getting somewhere. Tiered regulation based on risk level.
Speaker 1: That could work. It addresses Elena's startup concerns while maintaining Johnny's transparency requirements.
```

**Strengths:**
- Clear disagreements on multiple dimensions
- Each speaker challenges others' assumptions
- Positions evolve through discussion
- Personalities distinct (strategic, entrepreneurial, contrarian)
- Reaches nuanced conclusion through debate

## Example - Script Generation

### Example Input

```
I need a 15-minute technical discussion about AWS Lambda best practices.

Script Style: tech_discussion
Target Duration: 15 minutes
Content Topic: AWS Lambda best practices - cold starts, memory optimization, cost management
Listener Expertise: intermediate
```

### Example Output

```
✅ Script Generation Complete

**Generated Script:**
- Style: Technical Discussion (Dr. Alex Chen & Jamie Rodriguez)
- Duration Target: 15 minutes
- Speech Tempo: 175 WPM (default conversational pace)
- Expected Word Count: 2,625 words minimum (15 min × 175 words/min)
- Actual Word Count: 2,730 words ✅ (104% of target - meets duration requirement)
- Word Count Method: Excluded "Speaker N:" prefixes (counted only spoken dialogue)
- Expertise Level: Intermediate (assumes AWS basics, focuses on practical optimization)
- Segments: 5 discussion points
- Saved to: ~/generated-scripts/lambda-best-practices-script-20250106.txt

**Length Verification:**
✅ Script length verified - 2,730 words meets the 15-minute target duration (2,625 words minimum)

**Speaker Assignment Verification:**
✅ Reviewed all speaker lines - personas consistent throughout:
   - Speaker 1 (Dr. Alex Chen): Maintains analytical, methodical approach
   - Speaker 2 (Jamie Rodriguez): Maintains practical, solution-focused approach
✅ No persona switches detected

**Estimated Audio Generation Time:**
Using formula: Execution time ≈ 20 + (word_count / 125) minutes
- Calculation: 20 + (2,730 / 125) ≈ 42 minutes
- Note: First-run with cold cache may add 5-10 minutes

Next Steps:
1. Review/edit script before audio generation
2. When using podcast-audio-generator, remember the speech tempo used (175 WPM) for tempo analysis
3. Regenerate with different focus or expertise level if needed

## Self-Improvement: Documenting Execution Lessons

**IMPORTANT:** At the end of your execution, output a "Lessons from This Execution" section that documents what could make this skill better.

**Format:** For each problem encountered, write a concise problem-solution pair:
- **What went wrong or caused confusion** (1 sentence describing the actual issue you hit)
- **How the skill should be updated** (1 sentence describing the specific instruction/clarification to add)

**When to document:**
- You encountered an ambiguity in the instructions
- A parameter or requirement was unclear
- An edge case wasn't handled by the current instructions
- You had to make an assumption that should be explicit
- The user asked a question that indicates missing documentation
- Something failed or required workarounds

**Example output:**
```
## Lessons from This Execution

1. **Issue:** User provided target duration of "5 minutes" but script only generated 400 words (2.7 minutes at 150 WPM).
   **Fix:** Add explicit word count targets in Step 1: "5 min = 750 words, 10 min = 1,500 words, 15 min = 2,250 words minimum."

2. **Issue:** Generated script had Speaker 1 responding to themselves in lines 45-46, breaking conversation flow.
   **Fix:** Add validation step: "Verify no speaker speaks twice consecutively - alternate speakers naturally."

3. **Issue:** Unclear whether business_panel style should have structured segments or free-flowing debate.
   **Fix:** In script_style descriptions, specify: "business_panel includes structured opening, 3 viewpoints, then open debate."
```

**Note:** This output helps evolve the skill over time. Don't edit the skill file directly - these lessons can be reviewed and incorporated in a separate improvement cycle.