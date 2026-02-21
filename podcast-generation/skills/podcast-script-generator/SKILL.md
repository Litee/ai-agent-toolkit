---
name: podcast-script-generator
description: Generate AI-powered podcast scripts with natural conversation flow. Use when creating podcast scripts, multi-speaker dialogue, or conversational content for audio production.
---

# Podcast Script Generator

Generate AI-powered podcast scripts optimized for natural conversation flow using AWS Bedrock. Scripts follow strict formatting requirements for text-to-speech synthesis and incorporate educational psychology principles for maximum engagement and retention.

## When to Use This Skill

Use this skill when users need to:
- Generate podcast scripts with AI
- Create multi-speaker dialogue with distinct personalities
- Convert topics into conversational podcast format
- Produce educational or explanatory conversational content

## Required Parameters

You MUST ask for these parameters upfront in a single prompt if not provided:

1. **script_style** (required): Choose from:
   - `tech_discussion` - Two-speaker technical discussion with contrasting perspectives
   - `solo_expert` - Single speaker educational/explanatory format
   - `business_panel` - Three-speaker panel with diverse viewpoints
   - `interview` - Dynamic Q&A between host and expert
   - `system_design_interview` - 50-minute mock interview with principal-level candidate driving discussion

2. **target_duration** (required): Duration for the podcast (e.g., "5 minutes", "10 minutes", "15 minutes")
   - **Recommended Maximum**: 60 minutes
   - **Important**: The podcast-audio-generator skill does not support generating audio files longer than 60 minutes

3. **content_topic** (required): Subject matter for the podcast

4. **listener_expertise** (required): Choose from:
   - `beginner` - No prior knowledge assumed, define all terms
   - `intermediate` - Familiar with basics, focus on practical application
   - `advanced` - Strong foundation, explore edge cases and optimization
   - `expert` - Deep expertise, focus on nuanced trade-offs and internals

## Optional Parameters

5. **speech_tempo** (optional): Words per minute for speech pacing (default: 175 WPM, range: 150-200)
   - `150-165 WPM` - Moderate conversational pace, clear and measured
   - `165-175 WPM` - Brisk conversational pace, engaged discussion style (default)
   - `175-185 WPM` - Fast-paced conversation, energetic and dynamic
   - `185-200 WPM` - Very fast presentation pace, urgent or highly energetic delivery
   - Used to calculate target word count: `target_duration_minutes × speech_tempo`

## How to Use This Skill

**⚠️ MANDATORY:** You MUST read [`references/generate-podcast-script.md`](references/generate-podcast-script.md) before generating any script. This reference guide contains:
- Critical format requirements for audio generation compatibility
- Prompt patterns for each script style
- Educational psychology principles (memory, attention, cognitive load)
- Natural conversation techniques and host dynamics
- Length verification requirements (configurable speech tempo, default 175 WPM) using bundled script
- Examples of good vs. bad dialogue patterns

### Execution Steps

1. **Gather parameters** - Collect all required parameters from user
   - **CRITICAL**: `target_duration` MUST be explicitly specified by the user (no defaults, no assumptions)
   - If any required parameter is missing, ask the user to provide it
2. **Validate duration** - Check if target_duration exceeds 60 minutes
   - If duration > 60 minutes, ask for user confirmation with the following warning:
     - "⚠️ The requested duration exceeds 60 minutes. The podcast-audio-generator skill does not support generating audio files longer than 60 minutes. You can still generate the script, but you won't be able to convert it to audio using the audio generation skill. Do you want to proceed?"
   - Do NOT proceed with generation unless user explicitly confirms
3. **Read reference guide** - Study the complete generation instructions
4. **Generate script** - Create script using your own capabilities (do NOT use external APIs)
5. **Review for repetition** - Check for overused phrases (e.g., "Exactly!", "Absolutely!") and replace with varied alternatives to ensure natural, engaging dialogue
6. **Validate format** - Ensure ONLY "Speaker N:" dialogue lines (no headers, comments, or section titles)
7. **Verify length** - Confirm word count meets target duration
8. **Save and inform** - Save script as .txt file using format `<topic>-script-<timestamp>.txt` where timestamp is `YYYYMMDDHHmmss` format without separators (e.g., `lambda-best-practices-script-20250131143000.txt`) and provide next steps

After generating the script, inform the user:
- Script style and format used
- Target vs. actual duration/word count
- **Speech tempo used** (prominently displayed: "✓ Script generated with target tempo: XXX WPM")
- Listener expertise level applied
- File path where script is saved
- **Estimated audio generation time** using formula: `20 + (word_count / 125)` minutes
  - Example: 2,625 words ≈ 41 minutes (20 + 2625/125)
  - Note: "First-run with cold cache may add 5-10 minutes"
- Next steps: "When using podcast-audio-generator, remember the speech tempo used (XXX WPM) for tempo analysis"

## Bundled Resources

- **references/generate-podcast-script.md** - Complete generation guide (MUST READ before execution)
- **scripts/calculate_podcast_metrics.py** - Python script for word counting and duration calculations

## Next Steps

After generating a script:
1. Review and edit the script as needed
2. Use the **podcast-audio-generator** skill to convert script to audio
3. Or regenerate with different parameters if needed

## Related Skills

- **podcast-audio-generator** - Convert formatted scripts into high-quality audio using text-to-speech synthesis
