import json
import pytest
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import patch

from log_analyzer import LogEntry, LogAnalyzer, AverageReportGenerator


class TestLogEntry:
    
    def test_log_entry_creation(self):
        # Тест создания записи лога с валидными данными
        entry = LogEntry(
            timestamp="2025-06-22T13:57:32+00:00",
            status=200,
            url="/api/context/test",
            request_method="GET",
            response_time=0.024,
            http_user_agent="TestAgent/1.0"
        )
        
        assert entry.status == 200
        assert entry.url == "/api/context/test"
        assert entry.request_method == "GET"
        assert entry.response_time == 0.024
        assert entry.http_user_agent == "TestAgent/1.0"
        assert isinstance(entry.timestamp, datetime)
    
    def test_timestamp_parsing(self): # Тест разных форматов временных меток
        entry1 = LogEntry("2025-06-22T13:57:32+00:00", 200, "/api/test", "GET", 0.1, "Agent")
        entry2 = LogEntry("2025-06-22T13:57:32Z", 200, "/api/test", "GET", 0.1, "Agent")
        
        assert entry1.timestamp.year == 2025
        assert entry1.timestamp.month == 6
        assert entry1.timestamp.day == 22
        assert entry2.timestamp.year == 2025
    
    def test_get_endpoint_removes_ids(self): # Тест извлечения конечной точки без числовых ID
        entry = LogEntry("2025-06-22T13:57:32+00:00", 200, "/api/users/123/posts/456", "GET", 0.1, "Agent")
        assert entry.get_endpoint() == "/api/users/.../posts/..."
    
    def test_get_endpoint_removes_query_params(self): # Тест извлечения конечной точки без параметров запроса
        entry = LogEntry("2025-06-22T13:57:32+00:00", 200, "/api/users?page=1&limit=10", "GET", 0.1, "Agent")
        assert entry.get_endpoint() == "/api/users"
    
    def test_get_endpoint_removes_trailing_slash(self): # Тест извлечения конечной точки без завершающего слэша
        entry = LogEntry("2025-06-22T13:57:32+00:00", 200, "/api/users/", "GET", 0.1, "Agent")
        assert entry.get_endpoint() == "/api/users"
    
    def test_get_endpoint_root_path(self): # Тест извлечения конечной точки для корневого пути
        entry = LogEntry("2025-06-22T13:57:32+00:00", 200, "/", "GET", 0.1, "Agent")
        assert entry.get_endpoint() == "/"


class TestAverageReportGenerator: # Тест класса AverageReportGenerator
    
    def test_generate_empty_list(self): # Тест генерации отчета с пустым списком записей лога
        generator = AverageReportGenerator()
        result = generator.generate([])
        assert result == {}
    
    def test_generate_single_endpoint(self): # Тест генерации отчета с одной конечной точкой
        entries = [
            LogEntry("2025-06-22T13:57:32+00:00", 200, "/api/users", "GET", 0.1, "Agent"),
            LogEntry("2025-06-22T13:57:33+00:00", 200, "/api/users", "GET", 0.2, "Agent"),
        ]
        
        generator = AverageReportGenerator()
        result = generator.generate(entries)
        
        assert len(result) == 1
        assert "/api/users" in result
        assert result["/api/users"]["count"] == 2
        assert abs(result["/api/users"]["avg_response_time"] - 0.15) < 0.001
    
    def test_generate_multiple_endpoints(self): # Тест генерации отчета с несколькими конечными точками
        entries = [
            LogEntry("2025-06-22T13:57:32+00:00", 200, "/api/users", "GET", 0.1, "Agent"),
            LogEntry("2025-06-22T13:57:33+00:00", 200, "/api/posts", "GET", 0.2, "Agent"),
            LogEntry("2025-06-22T13:57:34+00:00", 200, "/api/users", "GET", 0.3, "Agent"),
        ]
        
        generator = AverageReportGenerator()
        result = generator.generate(entries)
        
        assert len(result) == 2
        assert result["/api/users"]["count"] == 2
        assert result["/api/users"]["avg_response_time"] == 0.2
        assert result["/api/posts"]["count"] == 1
        assert result["/api/posts"]["avg_response_time"] == 0.2
    
    def test_generate_sorting(self): # Тест сортировки результатов
        entries = [
            LogEntry("2025-06-22T13:57:32+00:00", 200, "/api/slow", "GET", 0.5, "Agent"),
            LogEntry("2025-06-22T13:57:33+00:00", 200, "/api/fast", "GET", 0.1, "Agent"),
            LogEntry("2025-06-22T13:57:34+00:00", 200, "/api/fast", "GET", 0.1, "Agent"),
        ]
        
        generator = AverageReportGenerator()
        result = generator.generate(entries)
        
        endpoints = list(result.keys()) # Тестируем, что конечные точки отсортированы
        assert endpoints[0] == "/api/fast"
        assert endpoints[1] == "/api/slow"


class TestLogAnalyzer: # Тест LogAnalyzer класса
    
    def test_create_log_entry_valid_data(self): # Тест создания записи лога с валидными данными
        analyzer = LogAnalyzer()
        log_data = {
            "@timestamp": "2025-06-22T13:57:32+00:00",
            "status": 200,
            "url": "/api/test",
            "request_method": "GET",
            "response_time": 0.024,
            "http_user_agent": "TestAgent/1.0"
        }
        
        entry = analyzer._create_log_entry(log_data)
        assert entry.status == 200
        assert entry.url == "/api/test"
    
    def test_create_log_entry_missing_field(self): # Тест создания записи лога с отсутствующим обязательным полем
        analyzer = LogAnalyzer()
        log_data = {
            "@timestamp": "2025-06-22T13:57:32+00:00",
            "status": 200,
            "request_method": "GET",
            "response_time": 0.024,
            "http_user_agent": "TestAgent/1.0"
        }
        
        with pytest.raises(KeyError): # Проверяем, что возникает исключение при отсутствии обязательного поля
            analyzer._create_log_entry(log_data)
    
    def test_load_log_file_valid(self): # Тест загрузки валидного файла лога
        log_data = [
            {
                "@timestamp": "2025-06-22T13:57:32+00:00",
                "status": 200,
                "url": "/api/test1",
                "request_method": "GET",
                "response_time": 0.024,
                "http_user_agent": "TestAgent/1.0"
            },
            {
                "@timestamp": "2025-06-22T13:57:33+00:00",
                "status": 404,
                "url": "/api/test2",
                "request_method": "POST",
                "response_time": 0.056,
                "http_user_agent": "TestAgent/2.0"
            }
        ]
        
        with NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f: # Создаем временный файл для теста
            for entry in log_data:
                f.write(json.dumps(entry) + '\n')
            temp_path = Path(f.name)
        
        try: # Загружаем лог файл и проверяем записи
            analyzer = LogAnalyzer()
            analyzer.load_log_file(temp_path)
            
            entries = analyzer.get_log_entries()
            assert len(entries) == 2
            assert entries[0].url == "/api/test1"
            assert entries[1].url == "/api/test2"
        finally: # Удаляем временный файл
            temp_path.unlink()
    
    def test_load_log_file_with_date_filter(self): # Тест загрузки лог файла с фильтром по дате
        log_data = [
            {
                "@timestamp": "2025-06-22T13:57:32+00:00",
                "status": 200,
                "url": "/api/test1",
                "request_method": "GET",
                "response_time": 0.024,
                "http_user_agent": "TestAgent/1.0"
            },
            {
                "@timestamp": "2025-06-23T13:57:33+00:00",
                "status": 404,
                "url": "/api/test2",
                "request_method": "POST",
                "response_time": 0.056,
                "http_user_agent": "TestAgent/2.0"
            }
        ]
        
        with NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f: # Создаем временный файл для теста
            for entry in log_data:
                f.write(json.dumps(entry) + '\n')
            temp_path = Path(f.name)
        
        try: # Загружаем лог файл с фильтром по дате
            analyzer = LogAnalyzer() 
            filter_date = datetime(2025, 6, 22)
            analyzer.load_log_file(temp_path, filter_date)
            
            entries = analyzer.get_log_entries()
            assert len(entries) == 1
            assert entries[0].url == "/api/test1"
        finally: # Удаляем временный файл
            temp_path.unlink()
    
    def test_load_log_file_invalid_json(self): # Тест загрузки файла лога с некорректным JSON
        with NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write('{"valid": "json"}\n')
            f.write('invalid json line\n')
            f.write('{"another": "valid"}\n')
            temp_path = Path(f.name)
        
        try: # Загружаем лог файл с некорректными строками
            analyzer = LogAnalyzer()
            with patch('builtins.print') as mock_print: 
                analyzer.load_log_file(temp_path) 
                mock_print.assert_called() # Проверяем, что выведено предупреждение о некорректной строке
            
            entries = analyzer.get_log_entries() # Проверяем, что некорректные строки пропущены
            assert len(entries) == 0 
        finally: # Удаляем временный файл
            temp_path.unlink()
    
    def test_clear(self): # Тест очистки записей лога
        analyzer = LogAnalyzer()
        log_data = {
            "@timestamp": "2025-06-22T13:57:32+00:00",
            "status": 200,
            "url": "/api/test",
            "request_method": "GET",
            "response_time": 0.024,
            "http_user_agent": "TestAgent/1.0"
        }
        
        entry = analyzer._create_log_entry(log_data) 
        analyzer._log_entries.append(entry) 
        
        assert len(analyzer.get_log_entries()) == 1 
        analyzer.clear()
        assert len(analyzer.get_log_entries()) == 0 


if __name__ == "__main__": 
    pytest.main([__file__])
