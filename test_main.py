"""
Integration tests for the main script.
"""

import json
import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import patch
import pytest


class TestMainScript: # Тесты для основного скрипта
    
    def create_test_log_file(self, log_entries): # Помощник для создания временного лог файла
        temp_file = NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        for entry in log_entries:
            temp_file.write(json.dumps(entry) + '\n')
        temp_file.close()
        return Path(temp_file.name)
    
    def test_main_with_valid_log_file(self): # Тест основного скрипта с корректным лог файлом
        log_entries = [
            {
                "@timestamp": "2025-06-22T13:57:32+00:00",
                "status": 200,
                "url": "/api/users/123",
                "request_method": "GET",
                "response_time": 0.024,
                "http_user_agent": "TestAgent/1.0"
            },
            {
                "@timestamp": "2025-06-22T13:57:33+00:00",
                "status": 200,
                "url": "/api/users/456",
                "request_method": "GET",
                "response_time": 0.056,
                "http_user_agent": "TestAgent/1.0"
            },
            {
                "@timestamp": "2025-06-22T13:57:34+00:00",
                "status": 200,
                "url": "/api/posts/789",
                "request_method": "GET",
                "response_time": 0.120,
                "http_user_agent": "TestAgent/1.0"
            }
        ]
        
        log_file = self.create_test_log_file(log_entries)
        
        try: # Test command line execution
            result = subprocess.run([
                sys.executable, "main.py",
                "--file", str(log_file),
                "--report", "average"
            ], capture_output=True, text=True, cwd=Path(__file__).parent)
            
            # Should succeed
            assert result.returncode == 0
            assert "AVERAGE REPORT" in result.stdout
            assert "/api/users/..." in result.stdout
            assert "/api/posts/..." in result.stdout
               
        finally: 
            log_file.unlink()
    
    def test_main_with_date_filter(self):
        """Test main script with date filter."""
        log_entries = [
            {
                "@timestamp": "2025-06-22T13:57:32+00:00",
                "status": 200,
                "url": "/api/users",
                "request_method": "GET",
                "response_time": 0.024,
                "http_user_agent": "TestAgent/1.0"
            },
            {
                "@timestamp": "2025-06-23T13:57:33+00:00",
                "status": 200,
                "url": "/api/users",
                "request_method": "GET",
                "response_time": 0.056,
                "http_user_agent": "TestAgent/1.0"
            }
        ]
        
        log_file = self.create_test_log_file(log_entries)
        
        try:
            result = subprocess.run([
                sys.executable, "main.py",
                "--file", str(log_file),
                "--report", "average",
                "--date", "2025-06-22"
            ], capture_output=True, text=True, cwd=Path(__file__).parent)
            
            assert result.returncode == 0
            assert "Filtered by date: 2025-06-22" in result.stdout
            
        finally:
            log_file.unlink()
    
    def test_main_with_multiple_files(self):
        """Test main script with multiple log files."""
        log_entries1 = [
            {
                "@timestamp": "2025-06-22T13:57:32+00:00",
                "status": 200,
                "url": "/api/users",
                "request_method": "GET",
                "response_time": 0.024,
                "http_user_agent": "TestAgent/1.0"
            }
        ]
        
        log_entries2 = [
            {
                "@timestamp": "2025-06-22T13:57:33+00:00",
                "status": 200,
                "url": "/api/posts",
                "request_method": "GET",
                "response_time": 0.056,
                "http_user_agent": "TestAgent/1.0"
            }
        ]
        
        log_file1 = self.create_test_log_file(log_entries1)
        log_file2 = self.create_test_log_file(log_entries2)
        
        try:
            result = subprocess.run([
                sys.executable, "main.py",
                "--file", str(log_file1),
                "--file", str(log_file2),
                "--report", "average"
            ], capture_output=True, text=True, cwd=Path(__file__).parent)
            
            assert result.returncode == 0
            assert "/api/users" in result.stdout
            assert "/api/posts" in result.stdout
            
        finally:
            log_file1.unlink()
            log_file2.unlink()
    
    def test_main_missing_file(self):
        """Test main script with non-existent file."""
        result = subprocess.run([
            sys.executable, "main.py",
            "--file", "nonexistent.log",
            "--report", "average"
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        
        assert result.returncode == 1
        assert "does not exist" in result.stdout
    
    def test_main_invalid_date(self):
        """Test main script with invalid date format."""
        log_file = self.create_test_log_file([])
        
        try:
            result = subprocess.run([
                sys.executable, "main.py",
                "--file", str(log_file),
                "--report", "average",
                "--date", "invalid-date"
            ], capture_output=True, text=True, cwd=Path(__file__).parent)
            
            assert result.returncode == 1
            assert "Invalid date format" in result.stdout
            
        finally:
            log_file.unlink()
    
    def test_main_invalid_report_type(self):
        """Test main script with invalid report type."""
        log_file = self.create_test_log_file([])
        
        try:
            result = subprocess.run([
                sys.executable, "main.py",
                "--file", str(log_file),
                "--report", "invalid"
            ], capture_output=True, text=True, cwd=Path(__file__).parent)
            
            assert result.returncode == 2  # argparse error
            
        finally:
            log_file.unlink()


if __name__ == "__main__":
    pytest.main([__file__])
