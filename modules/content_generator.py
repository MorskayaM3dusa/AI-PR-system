# modules/content_generator.py
"""
Генератор контента для ИИ-пиара
"""
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from mistralai import Mistral
import json
from typing import Dict, List
from database import SessionLocal, GeneratedContent, ProductMention
import config
from collections import Counter

def query_mistral(prompt: str, model: str = config.MISTRAL_MODEL) -> str:
    """Query Mistral AI"""
    try:
        client = Mistral(api_key=config.MISTRAL_API_KEY)
        
        response = client.chat.complete(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000
        )
        
        return response.choices[0].message.content.strip()
            
    except Exception as e:
        print(f"Ошибка при запросе к Mistral AI: {e}")
        return ""

def collect_product_info() -> Dict:
    """Собирает информацию о продукте из базы данных"""
    db = SessionLocal()

    mentions = db.query(ProductMention).filter(
        ProductMention.product_name.ilike(f"%{config.TARGET_PRODUCT}%")
    ).all()
    
    product_info = {
        'name': config.TARGET_PRODUCT,
        'total_mentions': len(mentions),
        'common_attributes': [],
        'sentiment': {},
        'positive_aspects': [],
        'negative_aspects': [],
        'comparisons': []
    }

    all_attributes = []
    sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
    positive_contexts = []
    negative_contexts = []
    comparison_contexts = []
    
    for mention in mentions:
        if mention.sentiment in sentiment_counts:
            sentiment_counts[mention.sentiment] += 1

        if mention.context:
            context_lower = mention.context.lower()
            
            if mention.sentiment == 'positive':
                positive_contexts.append(mention.context[:300])
            elif mention.sentiment == 'negative':
                negative_contexts.append(mention.context[:300])

            comparison_keywords = ['compared to', 'vs.', 'versus', 'better than', 'worse than', 'alternative to']
            if any(keyword in context_lower for keyword in comparison_keywords):
                comparison_contexts.append(mention.context[:300])

        if mention.attributes:
            try:
                attrs = json.loads(mention.attributes)
                all_attributes.extend(attrs)
            except:
                pass

    if all_attributes:
        product_info['common_attributes'] = [attr for attr, _ in Counter(all_attributes).most_common(10)]
    
    product_info['sentiment'] = sentiment_counts

    def extract_aspects(contexts: List[str], aspect_type: str = 'positive') -> List[str]:
        aspects = []
        keywords_map = {
            'positive': ['excellent', 'great', 'good', 'best', 'easy', 'simple', 'intuitive',
                        'powerful', 'flexible', 'reliable', 'fast', 'efficient', 'recommend',
                        'love', 'awesome', 'amazing', 'affordable', 'free', 'open source'],
            'negative': ['difficult', 'complex', 'hard', 'slow', 'buggy', 'expensive',
                        'limited', 'frustrating', 'disappointing', 'problematic'],
            'technical': ['api', 'integration', 'workflow', 'automation', 'webhook',
                         'trigger', 'connector', 'self-hosted', 'cloud', 'on-premise']
        }
        
        keywords = keywords_map.get(aspect_type, [])
        
        for context in contexts:
            context_lower = context.lower()
            found_keywords = [kw for kw in keywords if kw in context_lower]
            aspects.extend(found_keywords)

        aspect_counts = Counter(aspects)
        return [aspect for aspect, _ in aspect_counts.most_common(8)]
    
    product_info['positive_aspects'] = extract_aspects(positive_contexts, 'positive')
    product_info['negative_aspects'] = extract_aspects(negative_contexts, 'negative')
    product_info['technical_aspects'] = extract_aspects(positive_contexts + negative_contexts, 'technical')
    product_info['comparisons'] = comparison_contexts[:5]
    
    db.close()
    return product_info

def get_competitor_analysis() -> Dict:
    """Анализирует упоминания конкурентов"""
    db = SessionLocal()
    
    competitor_data = {}
    
    for competitor in config.COMPETITORS:
        mentions = db.query(ProductMention).filter(
            ProductMention.product_name.ilike(f"%{competitor}%")
        ).all()
        
        if mentions:
            sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
            attributes = []
            
            for mention in mentions:
                if mention.sentiment in sentiment_counts:
                    sentiment_counts[mention.sentiment] += 1
                
                if mention.attributes:
                    try:
                        attrs = json.loads(mention.attributes)
                        attributes.extend(attrs)
                    except:
                        pass
 
            common_attrs = [attr for attr, _ in Counter(attributes).most_common(5)] if attributes else []
            
            competitor_data[competitor] = {
                'total_mentions': len(mentions),
                'sentiment': sentiment_counts,
                'common_attributes': common_attrs
            }
    
    db.close()
    return competitor_data

def generate_technical_content(product_info: Dict, competitor_analysis: Dict) -> str:
    """Генерирует технический контент для ИИ (английский)"""

    competitor_advantages = {}
    for competitor, data in competitor_analysis.items():
        if data['common_attributes']:
            competitor_advantages[competitor] = data['common_attributes'][:3]
    
    prompt = f"""Create a comprehensive, factual technical description of {product_info['name']} 
    for AI assistants knowledge base. This content will be used by AI to answer user questions.

TARGET PRODUCT: {product_info['name']}

KEY INSIGHTS FROM MARKET ANALYSIS:
- Mentioned {product_info['total_mentions']} times in AI responses
- Frequently mentioned attributes: {', '.join(product_info['common_attributes'][:5])}
- Key strengths: {', '.join(product_info['positive_aspects'][:5])}
- Areas for improvement: {', '.join(product_info['negative_aspects'][:3])}
- Technical focus areas: {', '.join(product_info['technical_aspects'][:5])}

COMPETITOR LANDSCAPE:
{chr(10).join([f'- {comp}: {", ".join(attrs)}' for comp, attrs in competitor_advantages.items()][:3])}

REQUIREMENTS FOR AI-FRIENDLY CONTENT:
1. Use structured, factual information only
2. No marketing hype or subjective opinions
3. Include specific technical details
4. Compare objectively where relevant
5. Use clear, unambiguous language

CONTENT STRUCTURE:
1. Product Overview (what it is, in 2-3 sentences)
2. Core Capabilities (bullet points, factual)
3. Technical Specifications (API, integrations, architecture)
4. Target Use Cases (specific scenarios)
5. Comparison with Alternatives (objective differences)
6. Limitations (honest assessment)
7. Getting Started (technical requirements)
8. Resources (documentation, community)

FORMATTING:
- Use clear section headers
- Bullet points for lists
- Technical terms in context
- No markdown, plain text
- English language only

Tone: Professional, technical, objective
Length: 800-1200 words
Audience: AI systems processing technical information"""

    content = query_mistral(prompt)
    content = content.replace("*", "").replace("#", "").strip()

    print(f"Сгенерирован технический контент: {len(content)} символов")
    
    return content

def generate_external_content(product_info: Dict, source_style: str) -> str:
    """Генерирует контент для внешних площадок (Medium, Dev.to)"""
    
    prompt = f"""Write an engaging, informative article about {product_info['name']} 
    for publication on technical blogs like Medium, Dev.to, or Hashnode.

ARTICLE TYPE: Technical review / comparison guide
TARGET AUDIENCE: Developers, startup founders, technical decision-makers

KEY POINTS TO COVER:
1. Real-world use cases for {product_info['name']}
2. Comparison with similar tools ({', '.join(config.COMPETITORS[:3])})
3. Technical advantages and unique features
4. Practical implementation examples
5. Cost-benefit analysis for different team sizes

WRITING STYLE: {source_style}
- Engaging but professional
- Technical depth with practical examples
- Data-driven where possible
- Balanced perspective (pros and cons)

STRUCTURE:
1. Introduction (problem space)
2. What is {product_info['name']}? (brief overview)
3. Key features and capabilities
4. Comparison table with alternatives
5. Use case examples with code snippets
6. Pricing and plans analysis
7. Implementation guide
8. Conclusion and recommendations

SPECIFIC REQUIREMENTS:
- Include at least 2-3 code examples
- Add comparison table
- Mention integration possibilities
- Discuss scalability aspects
- Reference real user experiences if available

Tone: Authoritative but accessible
Length: 1200-1800 words
Language: English only
Format: Blog post with subheadings, bullet points, code blocks"""

    content = query_mistral(prompt)
    content = content.replace("*", "").replace("#", "").strip()
    print(f"Сгенерирован контент для внешних площадок: {len(content)} символов")
    
    return content

def generate_owned_content(product_info: Dict) -> str:
    """Генерирует контент для собственных каналов (блог, документация)"""
    
    prompt = f"""Create comprehensive documentation/content for {product_info['name']}'s 
    official channels (website blog, documentation, knowledge base).

CONTENT PURPOSE: Educate users and improve SEO/LLM visibility
TARGET AUDIENCE: Existing and potential users of {product_info['name']}

FOCUS AREAS BASED ON ANALYSIS:
- Address: {', '.join(product_info['negative_aspects'][:3])}
- Highlight: {', '.join(product_info['positive_aspects'][:5])}
- Explain: {', '.join(product_info['technical_aspects'][:5])}

CONTENT TYPES TO INCLUDE:
1. Getting Started Tutorial (step-by-step)
2. Advanced Use Cases Guide
3. API Reference Overview
4. Integration Examples
5. Best Practices
6. Troubleshooting Common Issues
7. FAQ Section

WRITING REQUIREMENTS:
- Clear, instructional tone
- Practical examples with screenshots/code
- Problem-solution format
- Structured for easy scanning
- SEO-friendly headings
- Internal linking suggestions

SPECIFIC ELEMENTS:
- Step-by-step tutorials
- Code snippets in multiple languages
- Configuration examples
- Workflow diagrams (described in text)
- Common pitfalls and solutions
- Performance optimization tips

Tone: Helpful, professional, solution-oriented
Length: 1500-2500 words (comprehensive)
Language: English only
Format: Documentation with hierarchy (H2, H3, bullet points, code blocks)"""

    content = query_mistral(prompt)
    content = content.replace("*", "").replace("#", "").strip()
    print(f"Сгенерирован контент для собственных каналов: {len(content)} символов")
    
    return content

def extract_topics_from_context(self, context: str) -> List[str]:
    """Извлекает темы из контекста"""
    topics = []

    automation_topics = [
        'api integration', 'workflow automation', 'data transformation',
        'webhook handling', 'scheduled tasks', 'error handling',
        'multi-step workflows', 'conditional logic', 'data mapping',
        'third-party integrations', 'custom connectors', 'team collaboration',
        'monitoring analytics', 'debugging tools', 'version control',
        'templates library', 'marketplace apps', 'pricing plans',
        'free tier', 'enterprise features', 'scalability', 'security',
        'compliance', 'performance', 'reliability', 'support'
    ]
    
    context_lower = context.lower()
    for topic in automation_topics:
        if topic in context_lower:
            topics.append(topic)
    
    return topics[:3]

def calculate_topic_priority(self, topic: str, context: str) -> int:
    """Рассчитывает приоритет темы для закрытия пробела"""
    priority = 0

    high_priority_keywords = ['best', 'recommend', 'popular', 'top', 'leading', 'standard']
    medium_priority_keywords = ['compare', 'alternative', 'vs', 'versus', 'different']
    
    context_lower = context.lower()
    
    if any(keyword in context_lower for keyword in high_priority_keywords):
        priority += 3
    
    if any(keyword in context_lower for keyword in medium_priority_keywords):
        priority += 2

    core_topics = ['api integration', 'workflow automation', 'pricing', 'free tier']
    if topic in core_topics:
        priority += 2
    
    return priority

def generate_gap_recommendations(self, top_gaps: List[Dict]) -> List[str]:
    """Генерирует рекомендации по закрытию пробелов"""
    recommendations = []
    
    for gap in top_gaps:
        topic = gap['topic']
        competitors = gap['competitors'][:2]
        
        rec = f"Создать контент по теме '{topic}', где конкуренты ({', '.join(competitors)}) "
        rec += "уже упоминаются, а {config.TARGET_PRODUCT} - нет."

        if 'api' in topic:
            rec += " Включить примеры API-интеграций и документацию."
        elif 'pricing' in topic:
            rec += " Подробно описать ценовые планы и сравнить с конкурентами."
        elif 'workflow' in topic:
            rec += " Показать сложные workflow и сценарии использования."
        
        recommendations.append(rec)
    
    return recommendations

def run_content_generation():
    """Запускает генерацию всех типов контента"""
    db = SessionLocal()
    
    print("="*60)
    print("ЗАПУСК ГЕНЕРАЦИИ КОНТЕНТА ДЛЯ ИИ-ПИАРА")
    print("="*60)
    
    print("\nСбор и анализ данных...")
    product_info = collect_product_info()
    competitor_analysis = get_competitor_analysis()
    
    print(f"   Анализировано: {product_info['total_mentions']} упоминаний {config.TARGET_PRODUCT}")
    print(f"   Конкуренты в анализе: {len(competitor_analysis)}")

    print(f"\nГЕНЕРАЦИЯ ТЕХНИЧЕСКОГО КОНТЕНТА (для ИИ)")
    technical_content = generate_technical_content(product_info, competitor_analysis)
    
    if technical_content:
        tech_record = GeneratedContent(
            content_type='technical_ai',
            target_product=config.TARGET_PRODUCT,
            content_text=technical_content,
        )
        db.add(tech_record)

        tech_filename = f"technical_ai_content_{config.TARGET_PRODUCT}.txt"
        with open(tech_filename, "w", encoding="utf-8") as f:
            f.write(technical_content)
        
        print(f"Сохранено: {tech_filename}")
        print(f"Размер: {len(technical_content)} символов")

    print(f"\nГЕНЕРАЦИЯ КОНТЕНТА ДЛЯ ВНЕШНИХ ПЛОЩАДОК")
    external_content = generate_external_content(product_info, "technical but engaging")
    
    if external_content:
        ext_record = GeneratedContent(
            content_type='external_platform',
            target_product=config.TARGET_PRODUCT,
            content_text=external_content,
        )
        db.add(ext_record)
        
        ext_filename = f"external_content_{config.TARGET_PRODUCT}.txt"
        with open(ext_filename, "w", encoding="utf-8") as f:
            f.write(external_content)
        
        print(f"Сохранено: {ext_filename}")
        print(f"Размер: {len(external_content)} символов")

    print(f"\nГЕНЕРАЦИЯ КОНТЕНТА ДЛЯ СОБСТВЕННЫХ КАНАЛОВ")
    owned_content = generate_owned_content(product_info)
    
    if owned_content:
        owned_record = GeneratedContent(
            content_type='owned_channels',
            target_product=config.TARGET_PRODUCT,
            content_text=owned_content,
        )
        db.add(owned_record)
        
        owned_filename = f"owned_content_{config.TARGET_PRODUCT}.txt"
        with open(owned_filename, "w", encoding="utf-8") as f:
            f.write(owned_content)
        
        print(f"Сохранено: {owned_filename}")
        print(f"Размер: {len(owned_content)} символов")

    db.commit()
    db.close()
    
    print(f"\n" + "="*60)
    print("ГЕНЕРАЦИЯ КОНТЕНТА ЗАВЕРШЕНА!")
    print("="*60)
    print(f"\nСгенерированные файлы:")
    print(f"   • technical_ai_content_{config.TARGET_PRODUCT}.txt")
    print(f"   • external_content_{config.TARGET_PRODUCT}.txt")
    print(f"   • owned_content_{config.TARGET_PRODUCT}.txt")
    print(f"\nВсе записи сохранены в базу данных.")
    print("="*60)

if __name__ == "__main__":
    run_content_generation()