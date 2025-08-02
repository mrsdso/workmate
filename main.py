import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try: # Импортируем библиотеку для красивого вывода таблиц
    from tabulate import tabulate
except ImportError: # Если библиотека не установлена, выводим сообщение об ошибке
    print("Error: tabulate library is required for pretty output")
    print("Please install it with: pip install tabulate")
    sys.exit(1)

from log_analyzer import LogAnalyzer, AverageReportGenerator # Импортируем классы для анализа логов и генерации отчетов


def parse_arguments() -> argparse.Namespace: # Функция для парсинга аргументов командной строки
    parser = argparse.ArgumentParser(
        description="Analyze JSON log files and generate reports"
    )
    
    parser.add_argument( # Параметр для указания лог файлов
        "--file",
        type=str,
        required=True,
        help="Path to log file(s). Can be specified multiple times.",
        action="append",
        dest="files"
    )
    
    parser.add_argument( # Параметр для указания типа отчета
        "--report",
        type=str,
        required=True,
        choices=["average"],
        help="Type of report to generate"
    )
    
    parser.add_argument( # Параметр для фильтрации логов по дате
        "--date",
        type=str,
        help="Filter logs by date (format: YYYY-MM-DD)"
    )
    
    return parser.parse_args() # Возвращаем распарсенные аргументы


def validate_files(file_paths: List[str]) -> List[Path]: # Функция для проверки существования и доступности файлов
    validated_paths = []
    
    for file_path in file_paths: # Проверяем каждый путь к файлу
        path = Path(file_path)
        if not path.exists():
            print(f"Error: File '{file_path}' does not exist")
            sys.exit(1)
        if not path.is_file():
            print(f"Error: '{file_path}' is not a file")
            sys.exit(1)
        if not path.stat().st_size > 0:
            print(f"Warning: File '{file_path}' is empty")
        
        validated_paths.append(path)
    
    return validated_paths # Возвращаем список проверенных путей к файлам


def validate_date(date_str: Optional[str]) -> Optional[datetime]: # Функция для проверки и парсинга даты
    if date_str is None:
        return None
    
    try: # Пытаемся распарсить дату в формате YYYY-MM-DD
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError: # Если формат неверный, выводим сообщение об ошибке
        print(f"Error: Invalid date format '{date_str}'. Use YYYY-MM-DD")
        sys.exit(1)


def main(): # Основная точка входа.
    try: # Парсим аргументы командной строки
        args = parse_arguments()
        
        # Валидируем входные данные
        file_paths = validate_files(args.files)
        filter_date = validate_date(args.date)
        
        # Инициализируем анализатор логов
        analyzer = LogAnalyzer()
        
        # Загружаем лог файлы
        for file_path in file_paths:
            try:
                analyzer.load_log_file(file_path, filter_date)
            except Exception as e: # Обработка ошибок при загрузке файла
                print(f"Error loading file '{file_path}': {e}")
                sys.exit(1)
        
        # Генерируем отчет
        if args.report == "average":
            report_generator = AverageReportGenerator()
            report_data = report_generator.generate(analyzer.get_log_entries())
            
            if not report_data:
                print("No data found for the specified criteria")
                return

            # Отображаем отчет
            headers = ["Endpoint", "Requests", "Average Response Time (s)"]
            table_data = [
                [endpoint, data["count"], f"{data['avg_response_time']:.3f}"]
                for endpoint, data in report_data.items()
            ]
            
            print(f"\n{args.report.upper()} REPORT")
            print("=" * 50)
            if filter_date: # Если указана дата, выводим ее
                print(f"Filtered by date: {filter_date.strftime('%Y-%m-%d')}")
            print(f"Files processed: {', '.join(str(p.name) for p in file_paths)}")
            print()
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
            print()
    
    except KeyboardInterrupt: # Обработка прерывания пользователем
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:  # Общая обработка исключений
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__": # Запуск основной функции
    main()
