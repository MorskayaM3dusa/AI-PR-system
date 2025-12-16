# modules/style_analyzer_simple.py

import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

import json
import re
from typing import List, Dict
from collections import Counter
from database import SessionLocal, AuthoritativeSource
import config

class SimpleStyleAnalyzer:
    def __init__(self):
        print("🧠 Initializing English style analyzer...")

        self.formal_words = [
            'however', 'therefore', 'thus', 'consequently', 'furthermore',
            'moreover', 'nevertheless', 'accordingly', 'subsequently',
            'henceforth', 'notwithstanding', 'conversely', 'specifically'
        ]
        
        self.informal_words = [
            'cool', 'awesome', 'amazing', 'great', 'nice', 'btw', 'imo',
            'actually', 'basically', 'literally', 'seriously', 'guess',
            'maybe', 'probably', 'kinda', 'sorta', 'gonna', 'wanna'
        ]

        self.contractions = [
            "don't", "doesn't", "isn't", "aren't", "wasn't", "weren't",
            "haven't", "hasn't", "hadn't", "won't", "wouldn't", "shouldn't",
            "couldn't", "can't", "mustn't", "mightn't", "needn't",
            "I'm", "you're", "he's", "she's", "it's", "we're", "they're"
        ]
        
        self.tech_terms = {
            'general': ['api', 'integration', 'automation', 'workflow', 'trigger',
                       'webhook', 'database', 'server', 'client', 'interface'],
            'specific': ['zapier', 'make', 'n8n', 'slack', 'trello', 'github',
                        'json', 'xml', 'rest', 'graphql', 'oauth', 'jwt']
        }

        self.structure_indicators = {
            'lists': ['bullet points', 'numbered lists', '- ', '* ', '• '],
            'tables': ['|', 'table:', 'comparison table'],
            'headings': ['## ', '### ', 'h2', 'h3', 'section:'],
            'code': ['```', 'code block', 'example code']
        }
    
    def is_english_text(self, text: str, threshold: float = 0.9) -> bool:
        """Checks if text is primarily English"""
        if not text:
            return False

        english_chars = len(re.findall(r'[a-zA-Z]', text))
        total_chars = len(re.findall(r'[^\s]', text))
        
        if total_chars == 0:
            return False
        
        return (english_chars / total_chars) >= threshold
    
    def analyze_text_complexity(self, text: str) -> Dict:
        """Analyzes complexity of English text"""
        if len(text) < 50:
            return {'error': 'Text is too short for analysis'}

        if not self.is_english_text(text):
            return {'error': 'Text is not primarily English'}

        words = re.findall(r'\b\w+\b', text.lower())
        sentences = re.split(r'[.!?]+', text)

        words = [w for w in words if w]
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not words or not sentences:
            return {'error': 'Could not extract words/sentences'}

        metrics = {
            'word_count': len(words),
            'sentence_count': len(sentences),
            'avg_sentence_length': len(words) / len(sentences),
            'avg_word_length': sum(len(w) for w in words) / len(words),
            'unique_words': len(set(words)),
            'lexical_diversity': len(set(words)) / len(words)
        }

        formal_count = sum(1 for w in words if w in self.formal_words)
        informal_count = sum(1 for w in words if w in self.informal_words)

        contraction_count = sum(1 for w in words if w in self.contractions)
        metrics['contraction_density'] = contraction_count / (len(words) / 100)
        
        metrics['formality_ratio'] = formal_count / max(formal_count + informal_count, 1)
 
        all_tech_terms = self.tech_terms['general'] + self.tech_terms['specific']
        tech_count = sum(1 for w in words if w in all_tech_terms)
        metrics['tech_density'] = tech_count / (len(words) / 100)

        list_patterns = len(re.findall(r'\n\s*[-•*]\s+', text)) + \
                       len(re.findall(r'\n\s*\d+\.\s+', text))
        metrics['list_usage'] = list_patterns

        table_patterns = len(re.findall(r'\+[-]+\+', text)) + \
                        len(re.findall(r'\|.*\|', text))
        metrics['table_usage'] = table_patterns

        code_patterns = len(re.findall(r'```', text))
        metrics['code_usage'] = code_patterns

        style_components = []
        
        if metrics['formality_ratio'] > 0.7:
            style_components.append("formal")
        elif metrics['formality_ratio'] < 0.3:
            style_components.append("informal")
        
        if metrics['tech_density'] > 2.0:
            style_components.append("technical")
        
        if metrics['list_usage'] > 3:
            style_components.append("structured")
        
        if metrics['table_usage'] > 0:
            style_components.append("comparative")
        
        if metrics['code_usage'] > 0:
            style_components.append("practical")
        
        style = "neutral" if not style_components else " ".join(style_components)
        metrics['style_type'] = style
        
        # LLM-friendliness score (0-100)
        llm_friendliness = (
            min(metrics['list_usage'] * 15, 30) +        # Lists are good for LLMs
            min(metrics['table_usage'] * 20, 30) +       # Tables are excellent
            min(metrics['tech_density'] * 5, 20) +       # Technical terms
            min((1 - metrics['lexical_diversity']) * 20, 20)  # Consistent vocabulary
        )
        
        metrics['llm_friendliness_score'] = min(llm_friendliness, 100)
        metrics['llm_friendliness'] = self.get_llm_friendliness_level(llm_friendliness)
        
        # Complexity score (0-100)
        complexity = (
            min(metrics['avg_sentence_length'] * 2, 30) +  # Sentence length
            min(metrics['avg_word_length'] * 5, 20) +      # Word length
            min(metrics['tech_density'] * 10, 25) +        # Technical terms
            (1 - metrics['lexical_diversity']) * 25        # Vocabulary diversity
        )
        
        metrics['complexity_score'] = min(complexity, 100)
        metrics['complexity_level'] = self.get_complexity_level(complexity)
        
        return metrics
    
    def get_complexity_level(self, score: float) -> str:
        """Determines text complexity level"""
        if score > 80:
            return "very complex"
        elif score > 60:
            return "complex"
        elif score > 40:
            return "medium complexity"
        elif score > 20:
            return "simple"
        else:
            return "very simple"
    
    def get_llm_friendliness_level(self, score: float) -> str:
        """Determines how LLM-friendly the text is"""
        if score > 80:
            return "excellent"
        elif score > 60:
            return "good"
        elif score > 40:
            return "average"
        elif score > 20:
            return "poor"
        else:
            return "very poor"
    
    def compare_texts_similarity(self, text1: str, text2: str) -> float:
        """
        Compares two English texts for lexical similarity
        Returns score from 0 to 1
        """
        # Check if texts are English
        if not self.is_english_text(text1) or not self.is_english_text(text2):
            return 0.0
        
        words1 = set(re.findall(r'\b\w+\b', text1.lower()))
        words2 = set(re.findall(r'\b\w+\b', text2.lower()))
        
        if not words1 or not words2:
            return 0.0

        common_words = words1.intersection(words2)
 
        similarity = len(common_words) / len(words1.union(words2))
        
        all_tech_terms = self.tech_terms['general'] + self.tech_terms['specific']
        tech_words1 = [w for w in words1 if w in all_tech_terms]
        tech_words2 = [w for w in words2 if w in all_tech_terms]
        
        tech_overlap = 0
        if tech_words1 and tech_words2:
            tech_overlap = len(set(tech_words1).intersection(set(tech_words2))) / max(len(set(tech_words1).union(set(tech_words2))), 1)
        
        final_score = (similarity * 0.6 + tech_overlap * 0.4)
        
        return round(final_score, 3)
    
    def analyze_source_style(self, source_name: str, texts: List[str]) -> Dict:
        """Analyzes style of a specific source"""
        if not texts:
            return {}

        english_texts = [t for t in texts if self.is_english_text(t)]
        
        if not english_texts:
            return {}
        
        all_metrics = []
        for text in english_texts[:3]:  # Limit to 3 texts per source
            metrics = self.analyze_text_complexity(text)
            if 'error' not in metrics:
                all_metrics.append(metrics)
        
        if not all_metrics:
            return {}

        avg_metrics = {}
        numeric_keys = ['word_count', 'sentence_count', 'avg_sentence_length', 
                       'avg_word_length', 'unique_words', 'lexical_diversity',
                       'formality_ratio', 'contraction_density', 'tech_density',
                       'list_usage', 'table_usage', 'code_usage',
                       'llm_friendliness_score', 'complexity_score']
        
        for key in numeric_keys:
            values = [m.get(key, 0) for m in all_metrics if key in m]
            if values:
                avg_metrics[f'avg_{key}'] = sum(values) / len(values)

        style_counts = Counter(m.get('style_type', 'neutral') for m in all_metrics)
        dominant_style = style_counts.most_common(1)[0][0] if style_counts else 'neutral'

        avg_complexity = sum(m.get('complexity_score', 0) for m in all_metrics) / len(all_metrics)
        avg_llm_friendliness = sum(m.get('llm_friendliness_score', 0) for m in all_metrics) / len(all_metrics)
        
        return {
            'source_name': source_name,
            'style_type': dominant_style,
            'complexity_score': round(avg_complexity, 1),
            'complexity_level': self.get_complexity_level(avg_complexity),
            'llm_friendliness_score': round(avg_llm_friendliness, 1),
            'llm_friendliness': self.get_llm_friendliness_level(avg_llm_friendliness),
            'metrics': avg_metrics,
            'texts_analyzed': len(all_metrics)
        }
    
    def analyze_all_sources(self, target_content: str = "") -> Dict:
        """
        Analyzes style of all authoritative sources (English only)
        """
        db = SessionLocal()

        top_sources = db.query(AuthoritativeSource).order_by(
            AuthoritativeSource.mention_count.desc()
        ).limit(15).all()
        
        print(f"\n🎨 Analyzing style of {len(top_sources)} English sources...")
        
        source_styles = []
        
        for source in top_sources:
            example_texts = []
            if source.example_quote and self.is_english_text(source.example_quote):
                example_texts.append(source.example_quote)

            if example_texts:
                style_analysis = self.analyze_source_style(source.source_name, example_texts)
                if style_analysis:
                    style_analysis['mention_count'] = source.mention_count
                    style_analysis['example_preview'] = example_texts[0][:200] + "..." if len(example_texts[0]) > 200 else example_texts[0]

                    if target_content and self.is_english_text(target_content):
                        similarity = self.compare_texts_similarity(
                            example_texts[0],
                            target_content[:1000]
                        )
                        style_analysis['similarity'] = similarity
                        style_analysis['recommendation'] = self.generate_recommendation(
                            similarity, style_analysis['style_type'],
                            style_analysis['llm_friendliness']
                        )
                    
                    source_styles.append(style_analysis)

        report = {
            'sources_analyzed': len(source_styles),
            'target_product': config.TARGET_PRODUCT,
            'style_analysis': source_styles,
            'overall_stats': self.calculate_overall_stats(source_styles)
        }

        report_filename = f'english_style_analysis_{config.TARGET_PRODUCT}.json'
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\nEnglish style analysis completed.")
        print(f"   Sources analyzed: {len(source_styles)}")
        print(f"   Report saved to: {report_filename}")
        
        db.close()
        return report
    
    def calculate_overall_stats(self, source_styles: List[Dict]) -> Dict:
        """Calculates overall statistics for all English sources"""
        if not source_styles:
            return {}

        style_distribution = Counter()
        llm_friendliness_counts = Counter()
        complexity_scores = []
        llm_friendliness_scores = []
        
        for style in source_styles:
            style_type = style.get('style_type', 'neutral')
            style_distribution[style_type] += style.get('mention_count', 1)
            
            llm_friendliness = style.get('llm_friendliness', 'average')
            llm_friendliness_counts[llm_friendliness] += 1
            
            complexity_scores.append(style.get('complexity_score', 0))
            llm_friendliness_scores.append(style.get('llm_friendliness_score', 0))

        most_common = style_distribution.most_common(1)
        most_common_style = most_common[0][0] if most_common else "neutral"

        most_common_llm_friendliness = llm_friendliness_counts.most_common(1)
        dominant_llm_friendliness = most_common_llm_friendliness[0][0] if most_common_llm_friendliness else "average"

        avg_complexity = sum(complexity_scores) / len(complexity_scores) if complexity_scores else 0
        avg_llm_friendliness = sum(llm_friendliness_scores) / len(llm_friendliness_scores) if llm_friendliness_scores else 0

        recommendations = []
        
        if most_common_style == "formal technical":
            recommendations.append("Use structured format with clear technical terminology")
            recommendations.append("Include API examples and integration scenarios")
        elif most_common_style == "informal":
            recommendations.append("Add practical examples and use cases")
            recommendations.append("Use conversational tone but maintain professionalism")
        elif "structured" in most_common_style:
            recommendations.append("Continue using bullet points and clear organization")
            recommendations.append("Add comparison tables where relevant")
        
        if avg_llm_friendliness < 60:
            recommendations.append("Improve LLM-friendliness: add more structure (lists, tables)")
            recommendations.append("Use consistent terminology for better AI processing")
        
        if avg_complexity > 70:
            recommendations.append("Simplify language while maintaining technical accuracy")
        elif avg_complexity < 40:
            recommendations.append("Add more technical depth for expert audience")
        
        return {
            'total_sources': len(source_styles),
            'most_common_style': most_common_style,
            'dominant_llm_friendliness': dominant_llm_friendliness,
            'style_distribution': dict(style_distribution),
            'llm_friendliness_distribution': dict(llm_friendliness_counts),
            'avg_complexity': round(avg_complexity, 1),
            'avg_llm_friendliness': round(avg_llm_friendliness, 1),
            'recommendations': recommendations
        }
    
    def generate_recommendation(self, similarity: float, style_type: str, llm_friendliness: str) -> str:
        """Generates recommendations based on style similarity and LLM friendliness"""
        if similarity > 0.7:
            base = f"Strong match with {style_type} sources"
        elif similarity > 0.5:
            base = f"Good alignment with {style_type} sources"
        elif similarity > 0.3:
            base = f"Partial match with {style_type} sources"
        else:
            base = f"Different from {style_type} sources"
        
        if llm_friendliness in ["excellent", "good"]:
            return f"{base} (LLM-friendly)"
        elif llm_friendliness == "average":
            return f"{base} (moderate LLM-friendliness)"
        else:
            return f"{base} (needs LLM optimization)"
    
    def print_report_summary(self, report: Dict):
        """Prints a summary English style report"""
        if not report:
            print("No English sources found for analysis")
            return
        
        print("\n" + "="*70)
        print("ENGLISH STYLE ANALYSIS SUMMARY REPORT")
        print("="*70)
        
        stats = report.get('overall_stats', {})
        print(f"\nOVERALL STATISTICS:")
        print(f"   Sources analyzed: {stats.get('total_sources', 0)}")
        print(f"   Most common style: {stats.get('most_common_style', 'not defined')}")
        print(f"   Dominant LLM friendliness: {stats.get('dominant_llm_friendliness', 'average')}")
        print(f"   Average complexity: {stats.get('avg_complexity', 0):.1f}/100")
        print(f"   Average LLM friendliness: {stats.get('avg_llm_friendliness', 0):.1f}/100")
        
        print(f"\nSTYLE DISTRIBUTION:")
        for style, count in stats.get('style_distribution', {}).items():
            percentage = (count / stats['total_sources']) * 100 if stats['total_sources'] > 0 else 0
            print(f"   • {style}: {count} sources ({percentage:.1f}%)")
        
        print(f"\nLLM FRIENDLINESS DISTRIBUTION:")
        for level, count in stats.get('llm_friendliness_distribution', {}).items():
            percentage = (count / stats['total_sources']) * 100 if stats['total_sources'] > 0 else 0
            print(f"   • {level}: {count} sources ({percentage:.1f}%)")
        
        if stats.get('recommendations'):
            print(f"\nAI CONTENT RECOMMENDATIONS:")
            for i, rec in enumerate(stats['recommendations'], 1):
                print(f"   {i}. {rec}")
        
        print(f"\nTOP 3 SOURCES BY MENTIONS:")
        sorted_styles = sorted(
            report.get('style_analysis', []), 
            key=lambda x: x.get('mention_count', 0), 
            reverse=True
        )
        
        for i, source in enumerate(sorted_styles[:3], 1):
            name = source.get('source_name', 'Unknown')
            style = source.get('style_type', 'unknown')
            llm_friendliness = source.get('llm_friendliness', 'average')
            mentions = source.get('mention_count', 0)
            
            similarity_indicator = ""
            if 'similarity' in source:
                similarity = source['similarity']
                if similarity > 0.7:
                    similarity_indicator = ""
                elif similarity > 0.5:
                    similarity_indicator = ""
                else:
                    similarity_indicator = ""
            
            print(f"   {i}. {similarity_indicator}{name}")
            print(f"      Style: {style} | LLM Friendliness: {llm_friendliness}")
            print(f"      Mentions: {mentions}")
            
            if 'recommendation' in source:
                print(f"      Note: {source['recommendation']}")
        
        print("="*70)

def main():
    """Main execution function"""
    analyzer = SimpleStyleAnalyzer()
    
    # Load target content for comparison
    target_content = ""
    try:
        target_file = f'technical_content_{config.TARGET_PRODUCT}.txt'
        if os.path.exists(target_file):
            with open(target_file, 'r', encoding='utf-8') as f:
                target_content = f.read()
            print(f"Loaded target content from: {target_file}")
            
            # Verify it's English
            if not analyzer.is_english_text(target_content):
                print("Warning: Target content is not primarily English")
                target_content = ""
    except Exception as e:
        print(f"Could not load target content: {e}")
    
    # Run analysis
    report = analyzer.analyze_all_sources(target_content)
    
    # Print report
    analyzer.print_report_summary(report)

if __name__ == "__main__":
    main()