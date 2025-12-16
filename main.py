# main.py
"""
Главный скрипт для запуска системы ИИ-пиара
Координирует все модули
"""
import os
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def print_header():
    """Печатает заголовок системы"""
    print("\n" + "="*70)
    print("СИСТЕМА ИИ-ПИАРА: АНАЛИЗ И УЛУЧШЕНИЕ ВОСПРИЯТИЯ LLM")
    print("="*70)

def print_menu():
    """Печатает меню системы"""
    print("\nМЕНЮ СИСТЕМЫ:")
    print("1. Полный анализ (все этапы)")
    print("2. Только анализ LLM-ответов")
    print("3. Анализ источников")
    print("4. Генерация контента")
    print("5. Расчет ROI и влияния")
    print("6. Запуск дашборда")
    print("7. Запуск ежедневного обновления (разово)")
    print("8. Запуск планировщика (фоновая служба)")
    print("9. Очистка данных")
    print("0. Выход")
    print("-"*70)

def run_full_analysis():
    """Запускает полный анализ"""
    print("\nЗАПУСК ПОЛНОГО АНАЛИЗА...")
    print("Этап 1/5: Анализ ответов LLM")
    
    try:
        from modules.llm_query import run_analysis_queries
        run_analysis_queries()
        print("Этап 1 завершен")
    except Exception as e:
        print(f"Ошибка на этапе 1: {e}")
        return
    
    time.sleep(2)
    
    print("\nЭтап 2/5: Анализ упоминаний и тональности")
    try:
        from modules.response_analyzer import process_all_responses, generate_reputation_report, print_detailed_report
        process_all_responses()
        report, total_mentions = generate_reputation_report()
        print_detailed_report(report, total_mentions)
        print("Этап 2 завершен")
    except Exception as e:
        print(f"Ошибка на этапе 2: {e}")
        return
    
    time.sleep(2)
    
    print("\nЭтап 3/5: Анализ авторитетных источников")
    try:
        from modules.source_finder import generate_sources_report
        generate_sources_report()
        print("Этап 3 завершен")
    except Exception as e:
        print(f"Ошибка на этапе 3: {e}")
        return
    
    time.sleep(2)
    
    print("\nЭтап 4/5: Генерация контента")
    try:
        from modules.content_generator import run_content_generation
        run_content_generation()
        print("Этап 4 завершен")
    except Exception as e:
        print(f"Ошибка на этапе 4: {e}")
        return
    
    time.sleep(2)
    
    print("\nЭтап 5/5: Расчет ROI и влияние")
    try:
        from modules.roi_calculator import ROICalculator
        calculator = ROICalculator()
        calculator.generate_roi_report()
        print("Этап 5 завершен")
    except Exception as e:
        print(f"Ошибка на этапе 5: {e}")
        return
    
    print("\n" + "="*70)
    print("ПОЛНЫЙ АНАЛИЗ ЗАВЕРШЕН УСПЕШНО!")
    print("="*70)
    print("\nСгенерированные файлы:")
    print("   • База данных: ai_pr.db")
    print("   • Отчет по репутации: в консоли")
    print("   • Отчет по источникам: sources_report.json")
    print("   • Технический контент: technical_ai_content_*.txt")
    print("   • ROI отчет: roi_report.json")
    print("\nДля визуализации запустите: streamlit run modules/dashboard.py")
    print("="*70)

def run_llm_analysis():
    """Запускает только анализ LLM-ответов"""
    print("\nЗАПУСК АНАЛИЗА LLM-ОТВЕТОВ...")
    try:
        from modules.llm_query import run_analysis_queries
        from modules.response_analyzer import process_all_responses, generate_reputation_report, print_detailed_report
        
        run_analysis_queries()
        process_all_responses()
        report, total_mentions = generate_reputation_report()
        print_detailed_report(report, total_mentions)
        
        print("\nАнализ LLM-ответов завершен")
    except Exception as e:
        print(f"Ошибка: {e}")

def run_sources_analysis():
    """Запускает анализ источников"""
    print("\nАНАЛИЗ АВТОРИТЕТНЫХ ИСТОЧНИКОВ...")
    try:
        from modules.source_finder import generate_sources_report
        generate_sources_report()
        print("\nАнализ источников завершен")
    except Exception as e:
        print(f"Ошибка: {e}")

def run_content_generation():
    """Запускает генерацию контента"""
    print("\nЗАПУСК ГЕНЕРАЦИИ КОНТЕНТА...")
    try:
        from modules.content_generator import run_content_generation as generate_content
        generate_content()
        print("\nГенерация контента завершена")
    except Exception as e:
        print(f"Ошибка: {e}")

def run_roi_calculation():
    """Запускает расчет ROI"""
    print("\nРАСЧЕТ ROI И ВЛИЯНИЯ...")
    try:
        from modules.roi_calculator import ROICalculator
        calculator = ROICalculator()
        calculator.generate_roi_report()
        print("\nРасчет ROI завершен")
    except Exception as e:
        print(f"Ошибка: {e}")

def run_dashboard():
    """Запускает дашборд"""
    print("\nЗАПУСК ДАШБОРДА...")
    print("Для остановки дашборда нажмите Ctrl+C в этом окне")
    print("\nЗапуск...")
    
    try:
        os.system("streamlit run modules/dashboard.py")
    except KeyboardInterrupt:
        print("\nДашборд остановлен")
    except Exception as e:
        print(f"Ошибка при запуске дашборда: {e}")

def run_daily_update_once():
    """Запускает разовое ежедневное обновление"""
    print("\nЗАПУСК ЕЖЕДНЕВНОГО ОБНОВЛЕНИЯ...")
    try:
        from modules.scheduler import run_once_now
        success = run_once_now()
        if success:
            print("Ежедневное обновление успешно завершено!")
        else:
            print("Обновление завершено с ошибками")
    except Exception as e:
        print(f"Ошибка: {e}")

def run_scheduler_background():
    """Запускает планировщик в фоновом режиме"""
    print("\nЗАПУСК ПЛАНИРОВЩИКА В ФОНОВОМ РЕЖИМЕ...")
    print("Планировщик будет автоматически обновлять данные каждый день в полдень")
    print("Для остановки нажмите Ctrl+C")
    
    try:
        from modules.scheduler import DailyUpdater
        updater = DailyUpdater()
        updater.start_scheduler()
    except KeyboardInterrupt:
        print("\nПланировщик остановлен")
    except Exception as e:
        print(f"Ошибка: {e}")

def clear_data():
    """Очищает данные"""
    print("\nОЧИСТКА ДАННЫХ...")
    
    files_to_remove = [
        "ai_pr.db",
        "sources_report.json",
        "scraped_data.json",
        "roi_report.json",
        "technical_ai_content_*.txt",
        "external_content_*.txt",
        "owned_content_*.txt",
        "market_analysis.log",
        "content_prompts/*",
        "daily_updates.log",
        "daily_reports/*",
        "english_style_analysis_*.json"
    ]
    
    confirm = input("Вы уверены? Это удалит все данные. (y/n): ")
    
    if confirm.lower() == 'y':
        import glob
        import shutil
        removed_count = 0
        
        for pattern in files_to_remove:
            for file in glob.glob(pattern):
                try:
                    if os.path.isfile(file):
                        os.remove(file)
                        print(f"   Удален файл: {file}")
                    elif os.path.isdir(file):
                        shutil.rmtree(file)
                        print(f"   Удалена папка: {file}")
                    removed_count += 1
                except Exception as e:
                    print(f"Не удалось удалить {file}: {e}")
        if os.path.exists("exports"):
            try:
                shutil.rmtree("exports")
                print("   Удалена папка: exports")
                removed_count += 1
            except:
                pass
        if os.path.exists("daily_reports"):
            try:
                shutil.rmtree("daily_reports")
                print("   Удалена папка: daily_reports")
                removed_count += 1
            except:
                pass
        
        print(f"\nОчистка завершена. Удалено объектов: {removed_count}")
    else:
        print("Очистка отменена")

def main():
    """Главная функция"""
    print_header()
    
    while True:
        print_menu()
        
        try:
            choice = input("\nВыберите действие (0-9): ").strip()
            
            if choice == '0':
                print("\nВыход из системы")
                break
            
            elif choice == '1':
                run_full_analysis()
            
            elif choice == '2':
                run_llm_analysis()
            
            elif choice == '3':
                run_sources_analysis()
            
            elif choice == '4':
                run_content_generation()
            
            elif choice == '5':
                run_roi_calculation()
            
            elif choice == '6':
                run_dashboard()
            
            elif choice == '7':
                run_daily_update_once()
            
            elif choice == '8':
                run_scheduler_background()
            
            elif choice == '9':
                clear_data()
            
            else:
                print("Неверный выбор. Попробуйте снова.")
        
        except KeyboardInterrupt:
            print("\n\nВыход по запросу пользователя")
            break
        except Exception as e:
            print(f"Неожиданная ошибка: {e}")

        if choice not in ['6', '8']:
            input("\nНажмите Enter для продолжения...")
            os.system('cls' if os.name == 'nt' else 'clear')
            print_header()

if __name__ == "__main__":
    required_modules = [
        "config",
        "database",
        "modules.llm_query",
        "modules.response_analyzer",
        "modules.source_finder",
        "modules.content_generator",
        "modules.roi_calculator",
        "modules.dashboard",
        "modules.scheduler"
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError as e:
            missing_modules.append((module, str(e)))
    
    if missing_modules:
        print("ОШИБКА: Отсутствуют необходимые модули:")
        for module, error in missing_modules:
            print(f"   - {module}: {error}")
    else:
        try:
            from config import MISTRAL_API_KEY
            if not MISTRAL_API_KEY or MISTRAL_API_KEY == "":
                print("ПРЕДУПРЕЖДЕНИЕ: MISTRAL_API_KEY не найден в .env файле")
                print("Выход...")
                sys.exit(1)
        except ImportError:
            print("Не удалось импортировать config.py")
            sys.exit(1)
        os.makedirs("daily_reports", exist_ok=True)
        os.makedirs("exports", exist_ok=True)

        main()