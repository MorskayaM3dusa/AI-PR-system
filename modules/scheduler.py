# modules/scheduler.py
"""
Планировщик ежедневного автоматического обновления
"""
import schedule
import time
import threading
from datetime import datetime
import logging
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from modules.llm_query import query_mistral
from modules.response_analyzer import process_all_responses
from database import SessionLocal, LLMQuery
import config

class DailyUpdater:
    def __init__(self):
        self.setup_logging()
        self.is_running = False
        
    def setup_logging(self):
        """Настройка логирования"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('daily_updates.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def run_daily_update(self):
        """Основная функция ежедневного обновления"""
        if self.is_running:
            self.logger.warning("Обновление уже выполняется")
            return False
        
        self.is_running = True
        start_time = datetime.now()
        self.logger.info(f"Начало ежедневного обновления в {start_time}")
        
        try:
            new_queries_count = self.make_daily_queries()
            self.logger.info("Анализирую новые ответы...")
            process_all_responses()
            self.update_influence_index()
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds() / 60
            
            self.logger.info(
                f"Ежедневное обновление завершено!\n"
                f"   Время: {duration:.1f} минут\n"
                f"   Новых запросов: {new_queries_count}\n"
                f"   Время начала: {start_time.strftime('%H:%M')}\n"
                f"   Время окончания: {end_time.strftime('%H:%M')}"
            )
            self.save_update_session(start_time, end_time, new_queries_count)
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении: {e}", exc_info=True)
            return False
            
        finally:
            self.is_running = False
    
    def make_daily_queries(self):
        """Выполняет ежедневные запросы"""
        self.logger.info(f"Выполняю {len(config.DAILY_QUERIES)} ежедневных запросов")
        
        success_count = 0
        db = SessionLocal()
        
        try:
            for i, query_text in enumerate(config.DAILY_QUERIES, 1):
                try:
                    self.logger.info(f"[{i}/{len(config.DAILY_QUERIES)}] Запрос: {query_text[:60]}...")

                    full_prompt = f"""Please provide current information about workflow automation tools.
Focus on recent developments, updates, and market changes in 2025.
Be objective and mention specific tools when relevant.

Query: {query_text}

Provide up-to-date information:"""

                    response_text = query_mistral(full_prompt)
                    
                    if response_text:
                        query_record = LLMQuery(
                            query_text=query_text,
                            llm_model=config.MISTRAL_MODEL
                        )
                        db.add(query_record)
                        db.flush()
                        
                        from database import LLMResponse
                        response_record = LLMResponse(
                            query_id=query_record.id,
                            response_text=response_text,
                            full_raw_response=response_text
                        )
                        db.add(response_record)
                        
                        success_count += 1
                        self.logger.info(f"Успешно сохранен ответ {i}")
                    
                    if i < len(config.DAILY_QUERIES):
                        time.sleep(2)
                        
                except Exception as e:
                    self.logger.error(f"Ошибка в запросе {i}: {e}")
                    continue
            
            db.commit()
            self.logger.info(f"Успешно выполнено запросов: {success_count}/{len(config.DAILY_QUERIES)}")
            
            return success_count
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Ошибка в make_daily_queries: {e}")
            return 0
        finally:
            db.close()
    
    def update_influence_index(self):
        """Обновляет индекс влияния"""
        try:
            from modules.roi_calculator import ROICalculator
            calculator = ROICalculator()
            report = calculator.generate_roi_report()

            report_filename = f"daily_reports/influence_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
            import json
            os.makedirs('daily_reports', exist_ok=True)
            
            with open(report_filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'report': report
                }, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Индекс влияния сохранен: {report_filename}")
            
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении индекса влияния: {e}")
    
    def save_update_session(self, start_time, end_time, queries_count):
        """Сохраняет информацию о сессии обновления"""
        try:
            from database import AnalysisSession
            
            db = SessionLocal()
            session = AnalysisSession(
                session_type='daily_update',
                queries_count=queries_count,
                started_at=start_time,
                completed_at=end_time,
                status='completed'
            )
            db.add(session)
            db.commit()
            db.close()
            
            self.logger.info(f"Сессия обновления сохранена в базу (ID: {session.id})")
            
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении сессии: {e}")
    
    def start_scheduler(self):
        """Запускает планировщик"""
        if not config.AUTO_UPDATE_ENABLED:
            self.logger.warning("Автоматическое обновление отключено в конфиге")
            return

        schedule_time = f"{config.UPDATE_SCHEDULE_HOUR:02d}:00"
        schedule.every().day.at(schedule_time).do(self.run_daily_update)
        
        self.logger.info(f"📅 Планировщик запущен. Обновление ежедневно в {schedule_time}")

        if config.UPDATE_SCHEDULE_HOUR == datetime.now().hour:
            self.logger.info("Запускаю обновление сразу (текущий час совпадает)")
            self.run_daily_update()

        while True:
            try:
                schedule.run_pending()
                time.sleep(60)

                if datetime.now().minute == 0:
                    self.logger.info(f"Планировщик работает. Следующее обновление: {schedule_time}")
                    
            except KeyboardInterrupt:
                self.logger.info("Планировщик остановлен пользователем")
                break
            except Exception as e:
                self.logger.error(f"Ошибка в планировщике: {e}")
                time.sleep(300)

def run_in_background():
    """Запускает планировщик в фоновом режиме"""
    updater = DailyUpdater()

    thread = threading.Thread(target=updater.start_scheduler, daemon=True)
    thread.start()
    
    return thread

def run_once_now():
    """Запускает единоразовое обновление"""
    updater = DailyUpdater()
    return updater.run_daily_update()