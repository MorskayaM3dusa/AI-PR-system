# modules/source_finder.py
"""
Модуль для выявления авторитетных источников, на которые ссылаются LLM
"""
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

import re
import time
import json
from collections import Counter
from typing import List, Dict
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from database import SessionLocal, AuthoritativeSource, LLMResponse, BlindSpot
import config

def extract_cited_sources(text: str) -> List[Dict]:
    """
    Извлекает упоминания источников из английского текста ответов LLM
    Возвращает список словарей с информацией об источниках
    """
    sources = []

    patterns = [
        (r'https?://(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(?:/[^\s]*)?', 'url'),

        (r'(?:on|in|according to|based on|from) (?:website|platform|resource) ([A-Za-z0-9\s.-]+)', 'site'),
        (r'(?:on|at) ([A-Za-z0-9\s.-]+\.(?:com|org|net|io))', 'site'),

        (r'in (?:article|research|study|review) "([^"]+)"', 'article'),
        (r'according to the ([A-Za-z0-9\s.-]+) (?:article|study)', 'article'),

        (r'in the ([A-Za-z0-9\s.-]+) blog', 'blog'),
        (r'on ([A-Za-z0-9\s.-]+)\'s blog', 'blog'),
        
        (r'on (?:forum|platform|community) ([A-Za-z0-9\s.-]+)', 'forum'),
        (r'at ([A-Za-z0-9\s.-]+) forums', 'forum'),

        (r'GitHub(?: repository)? ([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)', 'github'),
        (r'on GitHub: ([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)', 'github'),

        (r'in the ([A-Za-z0-9\s.-]+) documentation', 'docs'),
        (r'according to ([A-Za-z0-9\s.-]+) docs', 'docs'),
    ]

    for pattern, source_type in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            source_name = match.group(1).strip()

            if source_type == 'url':
                try:
                    parsed = urlparse(f"http://{source_name}" if '://' not in source_name else source_name)
                    source_name = parsed.netloc or parsed.path.split('/')[0]
                except:
                    pass

            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 100)
            context = text[start:end]

            quote_start = match.end()
            quote_end = min(len(text), quote_start + 300)
            quote = text[quote_start:quote_end].split('.')[0] + '.'
            
            sources.append({
                'source_name': source_name,
                'source_type': source_type,
                'context': context,
                'quote': quote.strip(),
                'full_match': match.group(0)
            })

    known_platforms = {
        'medium.com': 'Medium',
        'dev.to': 'DEV Community',
        'github.com': 'GitHub',
        'stackoverflow.com': 'Stack Overflow',
        'reddit.com': 'Reddit',
        'wikipedia.org': 'Wikipedia',
        'arxiv.org': 'arXiv',
        'towardsdatascience.com': 'Towards Data Science',
        'techcrunch.com': 'TechCrunch',
        'producthunt.com': 'Product Hunt',
        'hackernews.com': 'Hacker News',
        'g2.com': 'G2',
        'capterra.com': 'Capterra',
        'youtube.com': 'Youtube',
    }
    
    text_lower = text.lower()
    for url_keyword, platform_name in known_platforms.items():
        if url_keyword in text_lower:
            idx = text_lower.find(url_keyword)
            start = max(0, idx - 100)
            end = min(len(text), idx + len(url_keyword) + 100)
            context = text[start:end]
            
            sources.append({
                'source_name': platform_name,
                'source_type': 'known_platform',
                'context': context,
                'quote': context[:150] + '...',
                'full_match': url_keyword
            })
    
    return sources

def analyze_all_responses() -> Dict:
    """
    Анализирует все ответы в базе данных и выявляет источники
    """
    db = SessionLocal()

    responses = db.query(LLMResponse).all()
    
    all_sources = []
    source_counter = Counter()
    
    print(f"Анализирую источники в {len(responses)} ответах LLM...")
    
    for response in responses:
        if len(response.response_text) > 100:
            sources = extract_cited_sources(response.response_text)
            all_sources.extend(sources)
            for source in sources:
                source_counter[source['source_name']] += 1

    for source_name, count in source_counter.most_common(20):
        example_quote = ""
        for source in all_sources:
            if source['source_name'] == source_name:
                example_quote = source['quote']
                break

        existing = db.query(AuthoritativeSource).filter_by(source_name=source_name).first()
        
        if existing:
            existing.mention_count = count
            if example_quote and not existing.example_quote:
                existing.example_quote = example_quote
        else:
            source_record = AuthoritativeSource(
                source_name=source_name,
                mention_count=count,
                example_quote=example_quote
            )
            db.add(source_record)
    
    db.commit()
    report = {
        'total_sources_found': len(set([s['source_name'] for s in all_sources])),
        'top_sources': [(name, count) for name, count in source_counter.most_common(10)],
        'sources_by_type': {},
        'blind_spots': find_blind_spots(db, source_counter)
    }

    for source in all_sources:
        source_type = source['source_type']
        if source_type not in report['sources_by_type']:
            report['sources_by_type'][source_type] = []
        report['sources_by_type'][source_type].append(source['source_name'])
    
    db.close()
    return report

def save_blind_spots_to_db(blind_spots):
    db = SessionLocal()
    for spot in blind_spots:
        blind_spot = BlindSpot(
            source_name=spot['source_name'],
            source_type=spot['source_type'],
            competitors=json.dumps(spot['competitors_mentioned']),
            context=spot['context_en'][:500]
        )
        db.add(blind_spot)
    db.commit()
    db.close()

def find_blind_spots(db: Session, source_counter: Counter) -> List[Dict]:
    """
    Находит "слепые пятна" - источники, где упоминаются конкуренты,
    но не упоминается целевой продукт
    """
    blind_spots = []

    competitor_patterns = '|'.join([re.escape(comp) for comp in config.COMPETITORS])
    
    responses_with_competitors = db.query(LLMResponse).filter(
        LLMResponse.response_text.regexp_match(f'.*({competitor_patterns}).*')
    ).all()
    
    for response in responses_with_competitors:
        target_lower = config.TARGET_PRODUCT.lower()
        response_lower = response.response_text.lower()
        
        if target_lower not in response_lower:
            sources = extract_cited_sources(response.response_text)
            competitors_mentioned = []
            for comp in config.COMPETITORS:
                if comp.lower() in response_lower:
                    competitors_mentioned.append(comp)
            
            for source in sources:
                blind_spots.append({
                    'response_id': response.id,
                    'source_name': source['source_name'],
                    'source_type': source['source_type'],
                    'context_en': source['context'],
                    'context_ru': f"Упоминаются {', '.join(competitors_mentioned[:3])}...",
                    'competitors_mentioned': competitors_mentioned,
                    'example_quote_en': source['quote']
                })
    
    save_blind_spots_to_db(blind_spots)
    return blind_spots

def generate_sources_report():
    """
    Генерирует отчёт об авторитетных источниках
    """
    report = analyze_all_responses()
    
    print("\n" + "="*60)
    print("📚 ОТЧЁТ ОБ АВТОРИТЕТНЫХ ИСТОЧНИКАХ")
    print("="*60)
    
    print(f"\n📊 Общая статистика:")
    print(f"   Всего найдено уникальных источников: {report['total_sources_found']}")
    print(f"   Проанализировано ответов LLM: {report.get('total_responses', 'N/A')}")
    
    print(f"\n🏆 Топ-10 самых упоминаемых источников (в ответах LLM):")
    for i, (source, count) in enumerate(report['top_sources'], 1):
        print(f"   {i}. {source}: {count} упоминаний")
    
    print(f"\n🔧 Распределение по типам источников:")
    for source_type, sources in report['sources_by_type'].items():
        unique_count = len(set(sources))
        print(f"   • {source_type}: {unique_count} уникальных источников")
    
    if report['blind_spots']:
        print(f"\n⚠️  ОБНАРУЖЕНЫ СЛЕПЫЕ ПЯТНА ({len(report['blind_spots'])}):")
        print(f"   (Источники, где упоминаются конкуренты, но не {config.TARGET_PRODUCT})")
        
        for i, spot in enumerate(report['blind_spots'][:5], 1):  # Показываем первые 5
            print(f"\n   {i}. Источник: {spot['source_name']}")
            print(f"      Тип источника: {spot['source_type']}")
            competitors = spot['competitors_mentioned'][:3]
            if len(competitors) > 0:
                print(f"      Упоминаются конкуренты: {', '.join(competitors)}")
                if len(spot['competitors_mentioned']) > 3:
                    print(f"      (+ еще {len(spot['competitors_mentioned']) - 3} конкурентов)")
            print(f"      Контекст: {spot['context_ru']}")
    else:
        print(f"\n✅ Слепых пятен не обнаружено")
    
    # Сохраняем отчёт в файл (данные на английском, но метаданные на русском)
    report_with_metadata = {
        'report_title': 'Анализ авторитетных источников для ИИ-ассистентов',
        'target_product': config.TARGET_PRODUCT,
        'generated_date': time.strftime('%Y-%m-%d %H:%M:%S'),
        'data': report
    }
    
    with open('sources_report.json', 'w', encoding='utf-8') as f:
        json.dump(report_with_metadata, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Отчёт сохранён в файл: sources_report.json")
    print("="*60)

if __name__ == "__main__":
    generate_sources_report()