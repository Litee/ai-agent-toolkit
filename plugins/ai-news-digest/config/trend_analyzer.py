#!/usr/bin/env python3
"""
Trend Analyzer for AI News
Detects trending topics from news articles
"""

from collections import Counter
from typing import List, Dict, Any

class TrendAnalyzer:
    """Detect trending topics from news articles"""

    # Common AI terms to track
    TRACKED_TERMS = [
        'GPT-5', 'GPT-4', 'GPT-4o', 'Claude 4', 'Claude 3.5', 'Claude Code', 'Gemini', 'Gemini 2',
        'AI agent', 'autonomous agent', 'agentic', 'multi-agent',
        'multimodal', 'reasoning', 'chain-of-thought', 'CoT',
        'fine-tuning', 'RLHF', 'reinforcement learning', 'DPO',
        'LangChain', 'LangGraph', 'CrewAI', 'AutoGen',
        'RAG', 'retrieval', 'vector database', 'embedding',
        'open source', 'Llama 3', 'Llama', 'Mistral', 'Qwen',
        'breakthrough', 'SOTA', 'state-of-the-art', 'benchmark',
        'regulation', 'AI safety', 'alignment', 'AGI',
        'tool use', 'function calling', 'plugin', 'MCP',
        'Model Context Protocol', 'Anthropic', 'OpenAI', 'DeepMind',
        'diffusion', 'vision', 'image generation', 'video generation',
        'Sora', 'Stable Diffusion', 'DALL-E',
        'tokenizer', 'transformer', 'attention',
        'prompt engineering', 'few-shot', 'zero-shot',
        'inference', 'quantization', 'distillation',
    ]

    def analyze_trends(self, entries: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Analyze trending topics from articles.

        Args:
            entries: List of news entries
            top_n: Number of top trends to return

        Returns:
            List of trending topics with count and example articles
        """
        term_mentions = Counter()
        term_articles = {}  # term -> [article titles]

        for entry in entries:
            text = (entry['title'] + ' ' + entry.get('summary', '')).lower()

            for term in self.TRACKED_TERMS:
                if term.lower() in text:
                    term_mentions[term] += 1

                    if term not in term_articles:
                        term_articles[term] = []

                    # Store article info (limit to 3 per term)
                    if len(term_articles[term]) < 3:
                        term_articles[term].append({
                            'title': entry['title'],
                            'source': entry['source'],
                            'link': entry.get('link', '')
                        })

        # Get top N trending terms
        top_trends = term_mentions.most_common(top_n)

        return [
            {
                'term': term,
                'count': count,
                'example_articles': term_articles[term]
            }
            for term, count in top_trends
            if count >= 2  # Require at least 2 mentions to be considered trending
        ]

    def format_trends_text(self, trends: List[Dict[str, Any]]) -> str:
        """Format trends as readable text"""
        if not trends:
            return "No significant trends detected."

        lines = ["## Trending Topics\n"]
        for i, trend in enumerate(trends, 1):
            lines.append(f"**{i}. {trend['term']}** ({trend['count']} mentions)")

            # Show example articles
            examples = trend['example_articles']
            if examples:
                lines.append("   Examples:")
                for article in examples[:2]:  # Show max 2 examples
                    lines.append(f"   - {article['title']} ({article['source']})")

            lines.append("")  # Empty line

        return "\n".join(lines)
