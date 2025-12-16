# modules/web_scraper.py
"""
Модуль для сбора данных с авторитетных источников
"""
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

import requests
import json
import time
from typing import Dict, Optional
from bs4 import BeautifulSoup
from database import SessionLocal, AuthoritativeSource
import config

class WebScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def scrape_website(self, url: str) -> Optional[Dict]:
        """
        Собирает данные с веб-сайта
        """
        try:
            print(f"Собираю данные с: {url}")
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            if response.encoding is None:
                response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            title = soup.title.string if soup.title else ""

            for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                script.decompose()

            main_content = soup.find('main') or soup.find('article') or soup.find('div', {'class': 'content'}) or soup

            text = main_content.get_text(separator=' ', strip=True)
            
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Извлекаем мета-описание
            meta_desc = soup.find("meta", {"name": "description"}) or soup.find("meta", {"property": "og:description"})
            description = meta_desc["content"] if meta_desc else ""
            
            # Ищем упоминания продуктов (на английском)
            mentions = {}
            all_products = [config.TARGET_PRODUCT] + config.COMPETITORS
            
            text_lower = text.lower()
            for product in all_products:
                product_lower = product.lower()
                if product_lower in text_lower:
                    # Находим все упоминания
                    import re
                    pattern = re.compile(r'.{0,50}' + re.escape(product) + r'.{0,50}', re.IGNORECASE)
                    matches = pattern.findall(text)
                    mentions[product] = {
                        'count': len(matches),
                        'examples': matches[:3]  # Первые 3 упоминания
                    }
            
            return {
                'url': url,
                'title': title[:200],
                'description': description[:500],
                'content_preview': text[:1000] + '...' if len(text) > 1000 else text,
                'content_length': len(text),
                'mentions': mentions,
                'has_target_product': config.TARGET_PRODUCT.lower() in text_lower,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except requests.exceptions.Timeout:
            print(f"Таймаут при запросе к {url}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Ошибка сети при запросе к {url}: {e}")
            return None
        except Exception as e:
            print(f"Ошибка при обработке {url}: {e}")
            return None
    
    def scrape_known_sources(self) -> Dict:
        """
        Собирает данные с известных платформ из базы данных
        """
        db = SessionLocal()

        top_sources = db.query(AuthoritativeSource).order_by(
            AuthoritativeSource.mention_count.desc()
        ).limit(8).all()
        
        results = {
            'websites': [],
            'summary': {
                'total_scraped': 0,
                'target_mentions': 0,
                'competitor_mentions': 0
            }
        }
        
        print(f"\nНачинаю сбор данных с топ-{len(top_sources)} источников...")

        scraped_count = 0
        for source in top_sources:
            source_name = source.source_name

            if '.' not in source_name or ' ' in source_name:
                continue

            url = source_name
            if not url.startswith(('http://', 'https://')):
                url = f'https://{url}'
            
            try:
                print(f"\n[{scraped_count + 1}/{len(top_sources)}] Проверяю: {url}")
                data = self.scrape_website(url)
                
                if data:
                    results['websites'].append(data)
                    scraped_count += 1

                    if data['has_target_product']:
                        results['summary']['target_mentions'] += 1
                    competitor_count = sum(1 for product in config.COMPETITORS 
                                         if product.lower() in data.get('mentions', {}))
                    results['summary']['competitor_mentions'] += competitor_count
                    target_status = "ЕСТЬ" if data['has_target_product'] else "НЕТ"
                    print(f"   Статус упоминания {config.TARGET_PRODUCT}: {target_status}")
                    print(f"   Длина контента: {data['content_length']} символов")
                    print(f"   Английский контент: {data['english_ratio']:.1%}")
                
            except Exception as e:
                print(f"Пропускаю из-за ошибки: {e}")
            time.sleep(2)
        
        results['summary']['total_scraped'] = scraped_count
        db.close()
        self.generate_report(results)
        with open('scraped_data.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\nСбор данных завершён.")
        print(f"   Успешно собрано: {scraped_count} сайтов")
        print(f"   {config.TARGET_PRODUCT} упоминается на: {results['summary']['target_mentions']} сайтах")
        print(f"   Результаты сохранены в: scraped_data.json")
        
        return results
    
    def generate_report(self, results: Dict):
        """Генерирует отчет"""
        print("\n" + "="*60)
        print("ОТЧЁТ ПО АНАЛИЗУ ИСТОЧНИКОВ")
        print("="*60)
        
        summary = results['summary']
        print(f"\nОБЩАЯ СТАТИСТИКА:")
        print(f"   Проанализировано сайтов: {summary['total_scraped']}")
        print(f"   Сайтов с упоминанием {config.TARGET_PRODUCT}: {summary['target_mentions']}")
        print(f"   Сайтов с упоминаниями конкурентов: {summary['competitor_mentions']}")
        
        if summary['total_scraped'] > 0:
            coverage_percentage = (summary['target_mentions'] / summary['total_scraped']) * 100
            print(f"   Покрытие {config.TARGET_PRODUCT}: {coverage_percentage:.1f}%")
        
        print(f"\nТОП ИСТОЧНИКОВ С УПОМИНАНИЕМ {config.TARGET_PRODUCT}:")
        target_sites = [site for site in results['websites'] if site['has_target_product']]
        
        if target_sites:
            for i, site in enumerate(target_sites[:5], 1):
                print(f"   {i}. {site['url']}")
                print(f"      Заголовок: {site['title'][:80]}...")

                competitors_on_site = []
                for comp in config.COMPETITORS:
                    if comp.lower() in site.get('mentions', {}):
                        competitors_on_site.append(comp)
                
                if competitors_on_site:
                    print(f"      Также упоминаются: {', '.join(competitors_on_site[:3])}")
        else:
            print(f"   {config.TARGET_PRODUCT} не упоминается ни на одном из проверенных сайтов")
        
        print(f"\nКОНКУРЕНТЫ НА ПРОВЕРЕННЫХ САЙТАХ:")
        competitor_stats = {}
        for site in results['websites']:
            mentions = site.get('mentions', {})
            for comp in config.COMPETITORS:
                if comp in mentions:
                    competitor_stats[comp] = competitor_stats.get(comp, 0) + 1
        
        if competitor_stats:
            sorted_competitors = sorted(competitor_stats.items(), key=lambda x: x[1], reverse=True)
            for comp, count in sorted_competitors[:5]:
                percentage = (count / summary['total_scraped']) * 100 if summary['total_scraped'] > 0 else 0
                print(f"   • {comp}: {count} сайтов ({percentage:.1f}%)")
        else:
            print(f"Конкуренты не найдены на проверенных сайтах")
        
        print(f"\nРЕКОМЕНДАЦИИ:")
        if summary['target_mentions'] == 0:
            print(f"   1. СРОЧНО: {config.TARGET_PRODUCT} отсутствует в авторитетных источниках")
            print(f"   2. Начните с публикации на Medium, Dev.to, GitHub")
            print(f"   3. Создайте техническую документацию на английском")
        elif summary['target_mentions'] < len(config.COMPETITORS):
            print(f"   1. Увеличить присутствие {config.TARGET_PRODUCT} в топ-источниках")
            print(f"   2. Фокус на сайтах где есть конкуренты, но нет {config.TARGET_PRODUCT}")
            print(f"   3. Создать контент с сравнениями и кейсами")
        else:
            print(f"   1. Поддерживать текущее присутствие")
            print(f"   2. Улучшать качество существующих упоминаний")
            print(f"   3. Расширять на новые платформы")
        
        print("="*60)

if __name__ == "__main__":
    scraper = WebScraper()
    results = scraper.scrape_known_sources()