import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod


class LogEntry: 
    
    def __init__(self, timestamp: str, status: int, url: str, 
                 request_method: str, response_time: float, 
                 http_user_agent: str): # Инициализация лог-записи
        self.timestamp = self._parse_timestamp(timestamp)
        self.status = status
        self.url = url
        self.request_method = request_method
        self.response_time = response_time
        self.http_user_agent = http_user_agent
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime: # Парсинг строки времени в объект datetime
        if timestamp_str.endswith('+00:00'): # Обработка формата ISO с временной зоной
            timestamp_str = timestamp_str[:-6] + 'Z'
        elif '+' in timestamp_str: # Обработка формата ISO без временной зоны
            timestamp_str = timestamp_str.split('+')[0] + 'Z'
        
        try: # Попытка преобразования строки в datetime
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError: # Обработка ошибок преобразования
            return datetime.strptime(timestamp_str.replace('Z', ''), 
                                   '%Y-%m-%dT%H:%M:%S')
    
    def get_endpoint(self) -> str: # Извлечение конечной точки из URL (удаление параметров запроса и ID)
        url_path = self.url.split('?')[0] # Удаление параметров запроса

        # Удаление завершающего слэша
        if url_path.endswith('/') and len(url_path) > 1:
            url_path = url_path[:-1]

        # Заменяем числовые ID на плейсхолдер для группировки
        endpoint = re.sub(r'/\d+', '/...', url_path)
        
        return endpoint


class ReportGenerator(ABC): # Базовый класс для генераторов отчетов
    
    @abstractmethod
    def generate(self, log_entries: List[LogEntry]) -> Dict[str, Any]: # Генерация отчета из лог-записей
        pass


class AverageReportGenerator(ReportGenerator): # Генерация отчета о средней времени ответа по конечным точкам.
    
    def generate(self, log_entries: List[LogEntry]) -> Dict[str, Dict[str, Any]]: # Генерация отчета о средней времени ответа по конечным точкам.
        endpoint_stats = {}
        
        for entry in log_entries: # Извлечение конечной точки из URL
            endpoint = entry.get_endpoint()
            
            if endpoint not in endpoint_stats: # Инициализация статистики для конечной точки
                endpoint_stats[endpoint] = {
                    'total_time': 0.0,
                    'count': 0
                }
            
            endpoint_stats[endpoint]['total_time'] += entry.response_time
            endpoint_stats[endpoint]['count'] += 1
        
        # Рассчет средних значений
        result = {}
        for endpoint, stats in endpoint_stats.items():
            result[endpoint] = {
                'count': stats['count'],
                'avg_response_time': stats['total_time'] / stats['count']
            }
        
        # Сортировка по убыванию количества, затем по возрастанию среднего времени
        return dict(sorted(result.items(), 
                          key=lambda x: (-x[1]['count'], x[1]['avg_response_time'])))


class LogAnalyzer: # Основной класс для анализа логов.
    
    def __init__(self):
        self._log_entries: List[LogEntry] = []
    
    def load_log_file(self, file_path: Path, filter_date: Optional[datetime] = None): # Загрузка и парсинг лог-файла
        try: # Проверяем, существует ли файл и не является ли он пустым
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1): 
                    line = line.strip()
                    if not line:
                        continue
                    
                    try: # Парсим строку как JSON
                        log_data = json.loads(line)
                        entry = self._create_log_entry(log_data)
                        
                        # Проверка даты, если указана
                        if filter_date:
                            entry_date = entry.timestamp.date()
                            if entry_date != filter_date.date():
                                continue
                        
                        self._log_entries.append(entry)
                        
                    except (json.JSONDecodeError, KeyError, ValueError) as e: # Обработка ошибок парсинга
                        print(f"Warning: Skipping invalid log line {line_num} in {file_path}: {e}")
                        continue
                        
        except IOError as e: # Обработка ошибок чтения файла
            raise Exception(f"Failed to read file {file_path}: {e}")
    
    def _create_log_entry(self, log_data: Dict[str, Any]) -> LogEntry: # Создание объекта LogEntry из словаря
        required_fields = ['@timestamp', 'status', 'url', 'request_method', 
                          'response_time', 'http_user_agent']
        
        for field in required_fields:
            if field not in log_data:
                raise KeyError(f"Missing required field: {field}")
        
        return LogEntry( 
            timestamp=log_data['@timestamp'],
            status=int(log_data['status']),
            url=log_data['url'],
            request_method=log_data['request_method'],
            response_time=float(log_data['response_time']),
            http_user_agent=log_data['http_user_agent']
        ) 
    
    def get_log_entries(self) -> List[LogEntry]: # Получение списка всех загруженных лог-записей
        return self._log_entries.copy()
    
    def clear(self): # Очистка списка лог-записей
        self._log_entries.clear()
