# modules/roi_calculator.py
"""
Расчет ROI
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime, timedelta
from typing import Dict
from database import SessionLocal, ProductMention, LLMResponse, GeneratedContent
import config

class ROICalculator:
    def __init__(self):
        self.db = SessionLocal()
        self.CONTENT_COST = 150
        self.MENTION_VALUE = {
            'positive': 20,
            'neutral': 4,
            'negative': -50,
        }
    
    def calculate_simple_roi(self) -> Dict:
        """
        Простой, но реалистичный расчет ROI
        """
        comparison_data = self.check_comparison_possible()
        
        if not comparison_data['has_comparison']:
            return self.calculate_baseline_metrics()

        content_cost = self.calculate_content_cost()
        
        before_stats = self.get_mentions_stats(comparison_data['before_start'], 
                                              comparison_data['before_end'])
        after_stats = self.get_mentions_stats(comparison_data['after_start'], 
                                             comparison_data['after_end'])

        before_value = self.calculate_mentions_value(before_stats)
        after_value = self.calculate_mentions_value(after_stats)

        value_increase = after_value - before_value
        roi_percentage = (value_increase / content_cost * 100) if content_cost > 0 else 0

        growth_metrics = self.calculate_growth_metrics(before_stats, after_stats)
        
        return {
            'has_comparison': True,
            'content_date': comparison_data['content_date'],
            'content_cost': content_cost,
            'before_period': {
                'start': comparison_data['before_start'],
                'end': comparison_data['before_end'],
                'stats': before_stats,
                'value': before_value
            },
            'after_period': {
                'start': comparison_data['after_start'],
                'end': comparison_data['after_end'],
                'stats': after_stats,
                'value': after_value
            },
            'roi': {
                'value_increase': value_increase,
                'percentage': round(roi_percentage, 1),
                'net_profit': round(value_increase - content_cost, 2),
                'interpretation': self.interpret_roi(roi_percentage)
            },
            'growth': growth_metrics
        }
    
    def check_comparison_possible(self) -> Dict:
        """
        Проверяет, возможно ли сравнение до/после
        """
        first_content = self.db.query(GeneratedContent).order_by(
            GeneratedContent.generated_at.asc()
        ).first()
        
        if not first_content:
            return {'has_comparison': False}
        
        content_date = first_content.generated_at
        
        before_start = content_date - timedelta(days=7)
        before_end = content_date

        after_start = content_date
        after_end = min(datetime.utcnow(), content_date + timedelta(days=7))

        mentions_before = self.db.query(ProductMention).join(LLMResponse).filter(
            LLMResponse.created_at >= before_start,
            LLMResponse.created_at < before_end
        ).count()
        
        mentions_after = self.db.query(ProductMention).join(LLMResponse).filter(
            LLMResponse.created_at >= after_start,
            LLMResponse.created_at <= after_end
        ).count()
        
        return {
            'has_comparison': mentions_before > 0 and mentions_after > 0,
            'content_date': content_date,
            'before_start': before_start,
            'before_end': before_end,
            'after_start': after_start,
            'after_end': after_end
        }
    
    def calculate_baseline_metrics(self) -> Dict:
        """
        Рассчитывает базовые метрики, когда сравнения еще нет
        """
        total_mentions = self.db.query(ProductMention).count()
        target_mentions = self.db.query(ProductMention).filter(
            ProductMention.product_name.ilike(f"%{config.TARGET_PRODUCT}%")
        ).count()

        target_sentiment = {'positive': 0, 'neutral': 0, 'negative': 0}
        target_mentions_list = self.db.query(ProductMention).filter(
            ProductMention.product_name.ilike(f"%{config.TARGET_PRODUCT}%")
        ).all()
        
        for mention in target_mentions_list:
            if mention.sentiment in target_sentiment:
                target_sentiment[mention.sentiment] += 1

        content_items = self.db.query(GeneratedContent).count()
        content_cost = content_items * self.CONTENT_COST

        competitor_stats = {}
        for comp in config.COMPETITORS[:3]:
            count = self.db.query(ProductMention).filter(
                ProductMention.product_name.ilike(f"%{comp}%")
            ).count()
            if count > 0:
                competitor_stats[comp] = count
        
        return {
            'has_comparison': False,
            'status': 'baseline',
            'current_metrics': {
                'total_mentions': total_mentions,
                'target_mentions': target_mentions,
                'target_mentions_percentage': (target_mentions / total_mentions * 100) if total_mentions > 0 else 0,
                'target_sentiment': target_sentiment,
                'content_items': content_items,
                'content_cost': content_cost,
                'competitor_stats': competitor_stats
            },
            'recommendation': 'Запустите контент-кампанию и повторите анализ через неделю'
        }
    
    def calculate_content_cost(self) -> float:
        """Простой расчет стоимости контента"""
        content_items = self.db.query(GeneratedContent).count()
        return content_items * self.CONTENT_COST
    
    def get_mentions_stats(self, start_date, end_date) -> Dict:
        """Получает статистику упоминаний за период"""
        if not start_date or not end_date:
            return {'total': 0, 'sentiment': {}, 'target_count': 0}

        mentions = self.db.query(ProductMention).join(LLMResponse).filter(
            LLMResponse.created_at >= start_date,
            LLMResponse.created_at <= end_date
        ).all()

        sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
        target_count = 0
        
        for mention in mentions:

            if mention.sentiment in sentiment_counts:
                sentiment_counts[mention.sentiment] += 1

            if config.TARGET_PRODUCT.lower() in mention.product_name.lower():
                target_count += 1
        
        return {
            'total': len(mentions),
            'sentiment': sentiment_counts,
            'target_count': target_count
        }
    
    def calculate_mentions_value(self, stats: Dict) -> float:
        """Рассчитывает денежную ценность упоминаний"""
        value = 0

        for sentiment, count in stats['sentiment'].items():
            if sentiment in self.MENTION_VALUE:
                value += count * self.MENTION_VALUE[sentiment]
        
        value += stats['target_count'] * 20
        
        return round(value, 2)
    
    def calculate_growth_metrics(self, before: Dict, after: Dict) -> Dict:
        """Рассчитывает метрики роста"""
        metrics = {}

        if before['total'] > 0:
            metrics['mentions_growth'] = round(
                (after['total'] - before['total']) / before['total'] * 100, 1
            )
        else:
            metrics['mentions_growth'] = 100 if after['total'] > 0 else 0
 
        if before['target_count'] > 0:
            metrics['target_growth'] = round(
                (after['target_count'] - before['target_count']) / before['target_count'] * 100, 1
            )
        else:
            metrics['target_growth'] = 100 if after['target_count'] > 0 else 0

        before_positive = before['sentiment'].get('positive', 0)
        after_positive = after['sentiment'].get('positive', 0)
        
        if before_positive > 0:
            metrics['positive_growth'] = round(
                (after_positive - before_positive) / before_positive * 100, 1
            )
        else:
            metrics['positive_growth'] = 100 if after_positive > 0 else 0
        
        return metrics
    
    def interpret_roi(self, roi_percentage: float) -> str:
        """Простая интерпретация ROI"""
        if roi_percentage > 500:
            return "Фантастический результат!"
        elif roi_percentage > 200:
            return "Отличная окупаемость"
        elif roi_percentage > 100:
            return "Хорошая окупаемость"
        elif roi_percentage > 0:
            return "Скромная окупаемость"
        elif roi_percentage == 0:
            return "Окупился"
        else:
            return "Убыточный"
    
    def generate_roi_report(self):
        """Генерирует простой отчет"""
        print("\n" + "="*60)
        print("ПРОСТОЙ АНАЛИЗ ROI")
        print("="*60)

        roi_data = self.calculate_simple_roi()
        
        print(f"\nЦЕЛЕВОЙ ПРОДУКТ: {config.TARGET_PRODUCT}")
        
        if not roi_data['has_comparison']:
            print("\nБАЗОВЫЕ ПОКАЗАТЕЛИ:")
            metrics = roi_data['current_metrics']
            
            print(f"   • Всего упоминаний: {metrics['total_mentions']}")
            print(f"   • Упоминаний {config.TARGET_PRODUCT}: {metrics['target_mentions']}")
            
            if metrics['target_mentions'] > 0:
                sentiment = metrics['target_sentiment']
                positive_pct = (sentiment['positive'] / metrics['target_mentions'] * 100)
                print(f"   • Позитивных упоминаний: {positive_pct:.1f}%")
            
            print(f"   • Создано материалов: {metrics['content_items']}")
            print(f"   • Стоимость контента: ${metrics['content_cost']}")
            
            if metrics['competitor_stats']:
                print(f"\nСРАВНЕНИЕ С КОНКУРЕНТАМИ:")
                for comp, count in metrics['competitor_stats'].items():
                    print(f"      • {comp}: {count} упоминаний")
            
            print(f"\n{roi_data['recommendation']}")
            
        else:
            print(f"\nПЕРИОД СРАВНЕНИЯ:")
            print(f"   • До контента: {roi_data['before_period']['start'].strftime('%d.%m')} - "
                  f"{roi_data['before_period']['end'].strftime('%d.%m')}")
            print(f"   • После контента: {roi_data['after_period']['start'].strftime('%d.%m')} - "
                  f"{roi_data['after_period']['end'].strftime('%d.%m')}")
            
            print(f"\nРЕЗУЛЬТАТЫ:")
            print(f"   • Упоминаний до: {roi_data['before_period']['stats']['total']}")
            print(f"   • Упоминаний после: {roi_data['after_period']['stats']['total']}")
            print(f"   • Рост: {roi_data['growth']['mentions_growth']}%")
            
            print(f"\nЦЕЛЕВЫЕ УПОМИНАНИЯ:")
            print(f"   • До: {roi_data['before_period']['stats']['target_count']}")
            print(f"   • После: {roi_data['after_period']['stats']['target_count']}")
            print(f"   • Рост: {roi_data['growth']['target_growth']}%")
            
            print(f"\nПОЗИТИВНЫЕ УПОМИНАНИЯ:")
            before_pos = roi_data['before_period']['stats']['sentiment'].get('positive', 0)
            after_pos = roi_data['after_period']['stats']['sentiment'].get('positive', 0)
            print(f"   • До: {before_pos}")
            print(f"   • После: {after_pos}")
            print(f"   • Рост: {roi_data['growth']['positive_growth']}%")
            
            print(f"\nФИНАНСОВЫЕ ПОКАЗАТЕЛИ:")
            print(f"   • Стоимость контента: ${roi_data['content_cost']}")
            print(f"   • Ценность до: ${roi_data['before_period']['value']}")
            print(f"   • Ценность после: ${roi_data['after_period']['value']}")
            print(f"   • Прирост ценности: ${roi_data['roi']['value_increase']}")
            
            print(f"\nROI КАМПАНИИ:")
            print(f"   • ROI: {roi_data['roi']['percentage']}%")
            print(f"   • Чистая прибыль: ${roi_data['roi']['net_profit']}")
            print(f"   • Оценка: {roi_data['roi']['interpretation']}")

        with open('roi_simple_report.json', 'w', encoding='utf-8') as f:
            json.dump(roi_data, f, ensure_ascii=False, indent=2)
        
        print("Отчет сохранен: roi_simple_report.json")
        
        self.db.close()
        return roi_data

if __name__ == "__main__":
    calculator = ROICalculator()
    report = calculator.generate_roi_report()