"""
LLM client with cost tracking and statistics.
"""

import logging
import time
from typing import Dict, List, Optional
from openai import OpenAI
from anthropic import Anthropic
import google.generativeai as genai

from .models import Config, Paper
from .arxiv_client import ArxivClient

logger = logging.getLogger(__name__)


class CostTracker:
    """Track LLM API costs and statistics."""
    
    # Pricing per 1M tokens (input, output)
    # Note: Prices are estimates and may not reflect actual costs
    # Use None for models without pricing data
    PRICING = {
        'openai': {
            'gpt-4': (30.0, 60.0),
            'gpt-4-turbo': (10.0, 30.0),
            'gpt-4.1-mini': None,  # Pricing not available
            'gpt-4.1-nano': None,  # Pricing not available
            'gpt-3.5-turbo': (0.5, 1.5),
        },
        'anthropic': {
            'claude-3-5-sonnet-20241022': (3.0, 15.0),
            'claude-3-opus-20240229': (15.0, 75.0),
        },
        'google': {
            'gemini-2.0-flash-exp': (0.0, 0.0),  # Free
            'gemini-2.5-flash': None,  # Pricing not available
            'gemini-1.5-pro': (1.25, 5.0),
        }
    }
    
    def __init__(self, provider: str, model: str):
        self.provider = provider
        self.model = model
        self.operations: List[Dict] = []
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.total_time = 0.0
    
    def record(self, operation: str, input_tokens: int, output_tokens: int, duration: float):
        """Record an LLM operation."""
        cost = self._calculate_cost(input_tokens, output_tokens)
        
        self.operations.append({
            'operation': operation,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'cost': cost,
            'duration': duration
        })
        
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += cost
        self.total_time += duration
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for given tokens. Returns NaN if pricing not available."""
        pricing = self.PRICING.get(self.provider, {}).get(self.model)
        if pricing is None:
            # Model exists but pricing not available
            return float('nan')
        if not pricing:
            # Model not in pricing table
            logger.warning(f"No pricing info for {self.provider}/{self.model}")
            return float('nan')
        
        input_price, output_price = pricing
        cost = (input_tokens / 1_000_000 * input_price + 
                output_tokens / 1_000_000 * output_price)
        return cost
    
    def get_summary(self) -> str:
        """Get formatted cost summary."""
        import math
        
        # Format cost with NaN handling
        if math.isnan(self.total_cost):
            cost_str = "N/A (pricing not available)"
        else:
            cost_str = f"${self.total_cost:.4f}"
        
        lines = [
            "=" * 80,
            "LLM COST SUMMARY",
            "=" * 80,
            "",
            f"Provider: {self.provider}",
            f"Model: {self.model}",
            f"Total operations: {len(self.operations)}",
            f"Total input tokens: {self.total_input_tokens:,}",
            f"Total output tokens: {self.total_output_tokens:,}",
            f"Total cost: {cost_str}",
            f"Total time: {self.total_time:.1f}s",
            "",
            "Per-operation breakdown:",
        ]
        
        for op in self.operations:
            if math.isnan(op['cost']):
                op_cost_str = "N/A"
            else:
                op_cost_str = f"${op['cost']:.4f}"
            
            lines.append(
                f"  {op['operation']}: "
                f"{op['input_tokens']:,} in + {op['output_tokens']:,} out = "
                f"{op_cost_str} ({op['duration']:.1f}s)"
            )
        
        lines.extend(["", "=" * 80])
        return "\n".join(lines)
    
    def get_per_paper_stats(self) -> Dict:
        """Get average stats per paper."""
        if not self.operations:
            return {}
        
        # Assuming each paper has 5 operations (translate + 4 summaries)
        num_papers = len(self.operations) // 5 if len(self.operations) >= 5 else 1
        
        return {
            'avg_cost_per_paper': self.total_cost / num_papers if num_papers > 0 else 0,
            'avg_time_per_paper': self.total_time / num_papers if num_papers > 0 else 0,
            'avg_tokens_per_paper': (self.total_input_tokens + self.total_output_tokens) / num_papers if num_papers > 0 else 0,
        }


class LLMClient:
    """LLM client with cost tracking."""
    
    def __init__(self, config: Config):
        self.config = config
        self.provider = config.llm.provider
        self.model = config.llm.model
        self.temperature = config.llm.temperature
        self.language = config.language
        
        self.cost_tracker = CostTracker(self.provider, self.model)
        self.paper_cost_tracker = CostTracker(self.provider, self.model)
        self.arxiv_client = ArxivClient()
        
        # Initialize client
        if self.provider == 'openai':
            self.client = OpenAI()
        elif self.provider == 'anthropic':
            self.client = Anthropic()
        elif self.provider == 'google':
            genai.configure()
            self.client = genai.GenerativeModel(self.model)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
        
        logger.info(f"Initialized LLM client: {self.provider}/{self.model}")
    
    def process_paper_sync(self, paper: Paper) -> Paper:
        """Process a paper synchronously: translate abstract and generate summaries."""
        
        # Translate abstract
        if paper.abstract:
            paper.translated_abstract = self.translate_abstract_sync(paper.abstract)
        
        # Get paper content
        content = self.arxiv_client.get_paper_content_sync(
            paper.arxiv_html_url or paper.arxiv_url,
            arxiv_id=paper.arxiv_id
        )
        
        # Generate summaries
        for section in self.config.summary.sections:
            summary = self.generate_summary_sync(
                paper=paper,
                section_name=section.name,
                section_prompt=section.prompt,
                content=content
            )
            paper.summaries[section.name] = summary
        
        # Translate figure captions
        for figure in paper.teaser_figures:
            if figure.caption and not figure.caption.startswith('Figure '):
                figure.caption = self.translate_text_sync(figure.caption, "image caption")
        
        return paper
    
    async def process_paper(self, paper: Paper) -> Paper:
        """Process a paper: translate abstract and generate summaries."""
        
        # Translate abstract
        if paper.abstract:
            paper.translated_abstract = await self.translate_abstract(paper.abstract)
        
        # Get paper content
        content = await self.arxiv_client.get_paper_content(
            paper.arxiv_html_url or paper.arxiv_url,
            arxiv_id=paper.arxiv_id
        )
        
        # Generate summaries
        for section in self.config.summary.sections:
            summary = await self.generate_summary(
                paper=paper,
                section_name=section.name,
                section_prompt=section.prompt,
                content=content
            )
            paper.summaries[section.name] = summary
        
        # Translate figure captions
        for figure in paper.teaser_figures:
            if figure.caption and not figure.caption.startswith('Figure '):
                figure.caption = await self.translate_text(figure.caption, "image caption")
        
        return paper
    
    def translate_abstract_sync(self, abstract: str) -> str:
        """Translate abstract to target language (sync version)."""
        start_time = time.time()
        
        prompt = f"""Translate the following academic paper abstract to {self.language}.
Keep technical terms and proper nouns in English with explanations in {self.language}.
Use formal academic tone.

Abstract:
{abstract}

Translation:"""
        
        try:
            result = self._call_llm_sync(prompt, max_tokens=1000)
            duration = time.time() - start_time
            
            # Estimate tokens (rough approximation)
            input_tokens = len(prompt.split()) * 1.3
            output_tokens = len(result.split()) * 1.3
            
            self.paper_cost_tracker.record('translate_abstract', int(input_tokens), int(output_tokens), duration)
            self.cost_tracker.record('translate_abstract', int(input_tokens), int(output_tokens), duration)
            
            return result
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return abstract
    
    async def translate_abstract(self, abstract: str) -> str:
        """Translate abstract to target language."""
        start_time = time.time()
        
        prompt = f"""Translate the following academic paper abstract to {self.language}.
Keep technical terms and proper nouns in English with explanations in {self.language}.
Use formal academic tone.

Abstract:
{abstract}

Translation:"""
        
        try:
            result = await self._call_llm(prompt, max_tokens=1000)
            duration = time.time() - start_time
            
            # Estimate tokens (rough approximation)
            input_tokens = len(prompt.split()) * 1.3
            output_tokens = len(result.split()) * 1.3
            
            self.cost_tracker.record('translate_abstract', int(input_tokens), int(output_tokens), duration)
            
            return result
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return abstract
    
    def generate_summary_sync(self, paper: Paper, section_name: str, section_prompt: str, content: str) -> str:
        """Generate summary for a specific section (sync version)."""
        start_time = time.time()
        
        # Prepare context
        context = f"""Paper Title: {paper.title}
Authors: {', '.join(paper.authors[:5])}
Abstract: {paper.abstract[:500]}...

"""
        
        if content:
            context += f"Full Content (excerpt):\n{content[:3000]}...\n\n"
        
        prompt = f"""{context}

{section_prompt}

Answer in {self.language}. {self.config.summary.custom_instructions}

Maximum length: {self.config.summary.max_length} characters.

Answer:"""
        
        try:
            result = self._call_llm_sync(prompt, max_tokens=500)
            duration = time.time() - start_time
            
            # Estimate tokens
            input_tokens = len(prompt.split()) * 1.3
            output_tokens = len(result.split()) * 1.3
            
            self.paper_cost_tracker.record(f'summary_{section_name}', int(input_tokens), int(output_tokens), duration)
            self.cost_tracker.record(f'summary_{section_name}', int(input_tokens), int(output_tokens), duration)
            
            return result
        except Exception as e:
            logger.error(f"Summary generation failed for {section_name}: {e}")
            return f"[Error generating summary: {str(e)}]"
    
    async def generate_summary(self, paper: Paper, section_name: str, section_prompt: str, content: str) -> str:
        """Generate summary for a specific section."""
        start_time = time.time()
        
        # Prepare context
        context = f"""Paper Title: {paper.title}
Authors: {', '.join(paper.authors[:5])}
Abstract: {paper.abstract[:500]}...

"""
        
        if content:
            context += f"Full Content (excerpt):\n{content[:3000]}...\n\n"
        
        prompt = f"""{context}

{section_prompt}

Answer in {self.language}. {self.config.summary.custom_instructions}

Maximum length: {self.config.summary.max_length} characters.

Answer:"""
        
        try:
            result = await self._call_llm(prompt, max_tokens=500)
            duration = time.time() - start_time
            
            # Estimate tokens
            input_tokens = len(prompt.split()) * 1.3
            output_tokens = len(result.split()) * 1.3
            
            self.cost_tracker.record(f'summary_{section_name}', int(input_tokens), int(output_tokens), duration)
            
            return result
        except Exception as e:
            logger.error(f"Summary generation failed for {section_name}: {e}")
            return f"[Error generating summary: {str(e)}]"
    
    def translate_text_sync(self, text: str, context: str = "") -> str:
        """Translate any text to target language (sync version)."""
        start_time = time.time()
        
        prompt = f"""Translate the following {context} to {self.language}.
Keep technical terms in English with explanations.

Text: {text}

Translation:"""
        
        try:
            result = self._call_llm_sync(prompt, max_tokens=300)
            duration = time.time() - start_time
            
            input_tokens = len(prompt.split()) * 1.3
            output_tokens = len(result.split()) * 1.3
            
            self.paper_cost_tracker.record(f'translate_{context}', int(input_tokens), int(output_tokens), duration)
            self.cost_tracker.record(f'translate_{context}', int(input_tokens), int(output_tokens), duration)
            
            return result
        except Exception as e:
            logger.warning(f"Translation failed: {e}")
            return text
    
    async def translate_text(self, text: str, context: str = "") -> str:
        """Translate any text to target language."""
        start_time = time.time()
        
        prompt = f"""Translate the following {context} to {self.language}.
Keep technical terms in English with explanations.

Text: {text}

Translation:"""
        
        try:
            result = await self._call_llm(prompt, max_tokens=300)
            duration = time.time() - start_time
            
            input_tokens = len(prompt.split()) * 1.3
            output_tokens = len(result.split()) * 1.3
            
            self.cost_tracker.record(f'translate_{context}', int(input_tokens), int(output_tokens), duration)
            
            return result
        except Exception as e:
            logger.warning(f"Translation failed: {e}")
            return text
    
    def _call_llm_sync(self, prompt: str, max_tokens: int = 1000) -> str:
        """Call LLM API (synchronous version)."""
        
        if self.provider == 'openai':
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content.strip()
        
        elif self.provider == 'anthropic':
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        
        elif self.provider == 'google':
            response = self.client.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=max_tokens
                )
            )
            return response.text.strip()
        
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def reset_cost_tracker(self):
        """Reset cost tracker for a new paper."""
        self.paper_cost_tracker = CostTracker(self.provider, self.model)
    
    def print_paper_cost(self):
        """Print cost for the current paper."""
        import math
        
        if not hasattr(self, 'paper_cost_tracker') or not self.paper_cost_tracker.operations:
            print("No cost data for this paper")
            return
        
        # Format cost with NaN handling
        if math.isnan(self.paper_cost_tracker.total_cost):
            cost_str = "N/A (pricing not available)"
        else:
            cost_str = f"${self.paper_cost_tracker.total_cost:.4f}"
        
        print(f"Provider: {self.provider} | Model: {self.model}")
        print(f"Operations: {len(self.paper_cost_tracker.operations)}")
        print(f"Input tokens: {self.paper_cost_tracker.total_input_tokens:,}")
        print(f"Output tokens: {self.paper_cost_tracker.total_output_tokens:,}")
        print(f"Cost: {cost_str}")
        print(f"Time: {self.paper_cost_tracker.total_time:.1f}s")
    
    def print_total_cost_summary(self):
        """Print total cost summary for all papers."""
        import math
        
        print("\n" + self.cost_tracker.get_summary())
        
        stats = self.cost_tracker.get_per_paper_stats()
        if stats:
            # Format average cost with NaN handling
            if math.isnan(stats['avg_cost_per_paper']):
                avg_cost_str = "N/A (pricing not available)"
            else:
                avg_cost_str = f"${stats['avg_cost_per_paper']:.4f}"
            
            print("\nPer-paper statistics:")
            print(f"  Average cost: {avg_cost_str}")
            print(f"  Average time: {stats['avg_time_per_paper']:.1f}s")
            print(f"  Average tokens: {stats['avg_tokens_per_paper']:.0f}")
            print()
