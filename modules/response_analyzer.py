# modules/response_analyzer.py

import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

import re
import json
from typing import List, Dict, Tuple
from database import SessionLocal, ProductMention, LLMResponse
import config
from textblob import TextBlob
from textblob.sentiments import PatternAnalyzer
from collections import defaultdict
import logging

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def normalize_product_name_fixed(name: str) -> str:
    """Исправленная нормализация имен продуктов"""
    name_lower = name.lower().strip()

    aliases_map = {
        'n8n': ['n8n', 'n8n.io', 'n8n cloud', 'n8n.io cloud'],
        'zapier': ['zapier'],
        'make': ['make', 'make.com'],
        'integromat': ['integromat'],
        'microsoft power automate': ['microsoft power automate', 'power automate'],
        'ifttt': ['ifttt']
    }

    for normalized, variants in aliases_map.items():
        if name_lower == normalized:
            return normalized
        if name_lower in variants:
            return normalized
    
    return name_lower

def extract_product_mentions_fixed(text: str) -> List[Dict]:
    """
    Извлечение упоминаний
    Учитывает только уникальные упоминания в разумных пределах
    """
    mentions = []

    all_products = [config.TARGET_PRODUCT] + config.COMPETITORS
    found_positions = defaultdict(set)
    for product in all_products:
        pattern = re.compile(rf'\b{re.escape(product)}\b', re.IGNORECASE)
        matches = list(pattern.finditer(text))
        
        if matches:
            max_mentions_per_product = 3
            matches = matches[:max_mentions_per_product]
            
            for match in matches:
                position = match.start()
                product_normalized = normalize_product_name_fixed(product)
                too_close = False
                for existing_pos in found_positions[product_normalized]:
                    if abs(position - existing_pos) < 50:
                        too_close = True
                        break
                
                if too_close:
                    continue

                found_positions[product_normalized].add(position)

                start = max(0, position - 100)
                end = min(len(text), position + 100)
                context = text[start:end]
                sentiment = analyze_sentiment_en_fixed(context)
                attributes = extract_attributes_en_fixed(context, product)
                is_comparison = is_comparison_mention_fixed(context)
                mentions.append({
                    'product_name': product_normalized,
                    'original_name': product,
                    'context': context,
                    'sentiment': sentiment['label'],
                    'sentiment_score': sentiment['score'],
                    'attributes': attributes,
                    'is_comparison': is_comparison,
                    'position': position
                })

    special_patterns = [
        (r'Make\s*\(formerly Integromat\)', 'make'),
        (r'Integromat\s*\(now Make\)', 'make'),
        (r'Power Automate\s*\(Microsoft\)', 'microsoft power automate'),
    ]
    
    for pattern, product_name in special_patterns:
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        for match in matches[:2]:
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 100)
            context = text[start:end]
            
            mentions.append({
                'product_name': product_name,
                'original_name': product_name,
                'context': context,
                'sentiment': analyze_sentiment_en_fixed(context)['label'],
                'sentiment_score': analyze_sentiment_en_fixed(context)['score'],
                'attributes': extract_attributes_en_fixed(context, product_name),
                'is_comparison': is_comparison_mention_fixed(context),
                'position': match.start()
            })
    
    return mentions

def analyze_sentiment_en_fixed(text: str) -> Dict:
    """Исправленный анализ тональности"""
    try:
        if len(text.strip()) < 10:
            return {
                'label': 'neutral',
                'score': 0.0,
                'confidence': 0.0,
                'method': 'too_short'
            }
        
        blob = TextBlob(text, analyzer=PatternAnalyzer())
        polarity = blob.sentiment.polarity
        text_length_factor = min(len(text) / 50, 1.0)
        keyword_score = analyze_sentiment_keywords_en_fixed(text)
        combined_score = (polarity * 0.6 + keyword_score * 0.4) * text_length_factor

        if combined_score > 0.3:
            label = "positive"
        elif combined_score < -0.3:
            label = "negative"
        else:
            label = "neutral"

        confidence = min(abs(combined_score) * 1.5 * text_length_factor, 1.0)
        
        return {
            'label': label,
            'score': round(combined_score, 3),
            'confidence': round(confidence, 2),
            'method': 'improved'
        }
    except Exception as e:
        logger.error(f"Error in sentiment analysis: {e}")
        return {
            'label': 'neutral',
            'score': 0.0,
            'confidence': 0.0,
            'method': 'fallback'
        }

def analyze_sentiment_keywords_en_fixed(text: str) -> float:
    """Улучшенный анализ по ключевым словам"""
    positive_keywords = {
        'excellent': 2.0,
        'best': 2.0,
        'great': 1.5,
        'good': 1.0,
        'recommend': 1.5,
        'easy': 1.0,
        'powerful': 1.0,
        'reliable': 1.0
    }
    
    negative_keywords = {
        'bad': 1.0,
        'worst': 2.0,
        'terrible': 2.0,
        'difficult': 1.0,
        'slow': 1.0,
        'buggy': 1.5,
        'expensive': 1.0,
        'limited': 1.0
    }
    
    text_lower = text.lower()
    
    positive_score = 0
    negative_score = 0
    
    for word, weight in positive_keywords.items():
        if word in text_lower:
            count = min(text_lower.count(word), 3)
            positive_score += count * weight
    
    for word, weight in negative_keywords.items():
        if word in text_lower:
            count = min(text_lower.count(word), 3)
            negative_score += count * weight

    total_score = positive_score + negative_score
    if total_score == 0:
        return 0.0
    
    normalized = (positive_score - negative_score) / total_score
    return max(min(normalized, 1.0), -1.0)

def extract_attributes_en_fixed(context: str, product: str) -> List[str]:
    """Улучшенное извлечение атрибутов"""
    attributes = []
    context_lower = context.lower()
    
    attribute_checks = {
        'price': ['$', 'price', 'cost', 'pricing', 'expensive', 'cheap', 'affordable', 'free', 'paid'],
        'ease_of_use': ['easy', 'simple', 'intuitive', 'user-friendly', 'difficult', 'complex', 'steep'],
        'features': ['api', 'integration', 'automation', 'workflow', 'trigger', 'webhook'],
        'comparison': ['vs', 'versus', 'compared to', 'alternative', 'better than', 'worse than'],
        'reliability': ['reliable', 'stable', 'unreliable', 'buggy', 'crash'],
        'support': ['support', 'documentation', 'community', 'forum'],
        'scalability': ['scalable', 'enterprise', 'large scale', 'small business']
    }
    
    for attr_type, keywords in attribute_checks.items():
        for keyword in keywords:
            if keyword in context_lower:
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, context_lower):
                    attributes.append(attr_type)
                    break
    
    return list(set(attributes))[:5]

def is_comparison_mention_fixed(context: str) -> bool:
    """Проверка на сравнение"""
    comparison_words = ['vs', 'versus', 'compared to', 'alternative to', 'instead of']
    context_lower = context.lower()
    
    for word in comparison_words:
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, context_lower):
            return True
    
    return False

def process_all_responses():
    """Обработка всех ответов"""
    db = SessionLocal()
    responses = db.query(LLMResponse).order_by(LLMResponse.id).all()
    deleted_count = db.query(ProductMention).delete()
    if deleted_count > 0:
        logger.info(f"Cleared {deleted_count} old mentions")
    
    total_mentions_count = 0
    total_responses = len(responses)
    
    for idx, response in enumerate(responses, 1):
        logger.info(f"Processing response {idx}/{total_responses} (ID: {response.id})")
        
        try:
            mentions = extract_product_mentions_fixed(response.response_text)
            logger.debug(f"Response {response.id}: found {len(mentions)} mentions")
            for mention in mentions:
                attributes = mention['attributes']
                if len(attributes) > 5:
                    attributes = attributes[:5]
                
                mention_record = ProductMention(
                    response_id=response.id,
                    product_name=mention['product_name'],
                    context=mention['context'][:500],
                    sentiment=mention['sentiment'],
                    attributes=json.dumps(attributes, ensure_ascii=False)
                )
                db.add(mention_record)
                total_mentions_count += 1
            
            db.commit()

            if idx % 5 == 0:
                logger.info(f"Processed {idx}/{total_responses} responses, total mentions: {total_mentions_count}")
            
        except Exception as e:
            logger.error(f"Error processing response {response.id}: {e}")
            db.rollback()
            continue
    
    db.close()

    logger.info(f"Processing completed!")
    logger.info(f"Total responses processed: {total_responses}")
    logger.info(f"Total mentions extracted: {total_mentions_count}")

    if total_mentions_count > total_responses * 10:
        logger.warning(f"WARNING: High mentions per response ratio: {total_mentions_count/total_responses:.2f}")
        logger.warning("This may indicate duplicate counting or overly aggressive extraction.")

def generate_reputation_report() -> Tuple[Dict, int]:
    """Исправленный отчет с проверкой данных"""
    db = SessionLocal()

    all_mentions = db.query(ProductMention).all()
    total_mentions = len(all_mentions)

    if total_mentions > 1000:
        logger.warning(f"WARNING: Total mentions ({total_mentions}) seems too high")
        logger.warning("Checking for duplicates...")

        unique_check = {}
        for mention in all_mentions:
            key = f"{mention.response_id}_{mention.product_name}_{mention.context[:50]}"
            unique_check[key] = unique_check.get(key, 0) + 1
        
        duplicates = sum(1 for count in unique_check.values() if count > 1)
        if duplicates > 0:
            logger.warning(f"Found {duplicates} potential duplicate mentions")
    
    report = {}
    all_products = [config.TARGET_PRODUCT] + config.COMPETITORS
    
    for product in all_products:
        product_mentions = []
        for mention in all_mentions:
            if product.lower() in mention.product_name.lower():
                product_mentions.append(mention)
        
        if product_mentions:
            total = len(product_mentions)

            sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
            for mention in product_mentions:
                if mention.sentiment in sentiment_counts:
                    sentiment_counts[mention.sentiment] += 1

            if total > 0:
                positive_pct = round(sentiment_counts['positive'] / total * 100, 1)
                neutral_pct = round(sentiment_counts['neutral'] / total * 100, 1)
                negative_pct = round(sentiment_counts['negative'] / total * 100, 1)
            else:
                positive_pct = neutral_pct = negative_pct = 0

            market_share = round(total / total_mentions * 100, 1) if total_mentions > 0 else 0
            
            report[product] = {
                'total_mentions': total,
                'market_share': market_share,
                'sentiment': sentiment_counts,
                'percentages': {
                    'positive': positive_pct,
                    'neutral': neutral_pct,
                    'negative': negative_pct
                }
            }
    
    db.close()

    sorted_report = dict(sorted(report.items(), key=lambda x: x[1]['total_mentions'], reverse=True))
    
    return sorted_report, total_mentions

def print_detailed_report(report: Dict, total_mentions: int):
    """Вывод реалистичного отчета"""
    print("\n" + "="*70)
    print("РЕАЛИСТИЧНЫЙ АНАЛИЗ РЕПУТАЦИИ")
    print("="*70)
    
    print(f"\nОБЩАЯ СТАТИСТИКА:")
    print(f"  Всего упоминаний: {total_mentions}")
    
    if total_mentions > 500:
        print(f"ВНИМАНИЕ: Количество упоминаний ({total_mentions}) кажется завышенным")
        print(f"Нормальный диапазон: 100-300 упоминаний для 20-30 запросов")
    
    print(f"  Продуктов проанализировано: {len(report)}")
    
    print(f"\nТАБЛИЦА ЛИДЕРОВ:")
    print("-"*70)
    print(f"{'Продукт':<25} {'Упоминания':<12} {'Доля рынка':<12} {'Позитивные':<12}")
    print("-"*70)
    
    for product, data in report.items():
        print(f"{product:<25} {data['total_mentions']:<12} "
              f"{data['market_share']}%{'':<8} "
              f"{data['percentages']['positive']}%")
    
    print(f"\nАНАЛИЗ ЦЕЛЕВОГО ПРОДУКТА ({config.TARGET_PRODUCT}):")
    if config.TARGET_PRODUCT in report:
        data = report[config.TARGET_PRODUCT]
        print(f"  • Всего упоминаний: {data['total_mentions']}")
        print(f"  • Доля рынка: {data['market_share']}%")
        print(f"  • Позитивных: {data['sentiment']['positive']} ({data['percentages']['positive']}%)")
        print(f"  • Нейтральных: {data['sentiment']['neutral']} ({data['percentages']['neutral']}%)")
        print(f"  • Негативных: {data['sentiment']['negative']} ({data['percentages']['negative']}%)")
        
        if data['total_mentions'] == 0:
            print(f"КРИТИЧЕСКИ: {config.TARGET_PRODUCT} не упоминается!")
        elif data['total_mentions'] < 10:
            print(f"ВНИМАНИЕ: Мало упоминаний ({data['total_mentions']})")
        elif data['percentages']['positive'] > 50:
            print(f"ОТЛИЧНО: Высокий процент позитивных упоминаний")
        elif data['percentages']['negative'] > 30:
            print(f"ПРОБЛЕМА: Много негативных упоминаний")
    else:
        print(f"{config.TARGET_PRODUCT} не найден в упоминаниях")

def main():
    """Основная функция"""
    try:
        logger.info("Starting improved reputation analysis...")
        process_all_responses()
        report, total_mentions = generate_reputation_report()
        print_detailed_report(report, total_mentions)
        logger.info("Improved reputation analysis completed successfully")

    except Exception as e:
        logger.error(f"Error in main execution: {e}", exc_info=True)
        print(f"\nError occurred: {e}")

if __name__ == "__main__":
    main()