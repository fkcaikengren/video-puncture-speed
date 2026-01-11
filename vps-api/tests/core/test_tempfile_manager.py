import os
import pytest
from unittest.mock import patch
from app.core.tempfile_manager import TempfileManager

@pytest.fixture
def mock_audit_log(tmp_path):
    """Mock audit log path for isolation"""
    log_file = tmp_path / "test_audit.log"
    with patch("app.core.tempfile_manager.AUDIT_LOG_PATH", str(log_file)):
        yield log_file

def test_create_temp_file_basic(mock_audit_log):
    """测试基本的临时文件创建和自动删除"""
    path = None
    with TempfileManager.create_temp_file() as tmp_path:
        path = tmp_path
        assert os.path.exists(path)
        assert os.path.isfile(path)
        
        # 验证日志已记录
        assert mock_audit_log.exists()
        with open(mock_audit_log, "r") as f:
            content = f.read()
            assert path in content
            
        # 尝试写入
        with open(path, 'w') as f:
            f.write('test')
    
    # 上下文结束后应被删除
    assert not os.path.exists(path)

def test_create_temp_file_with_options(mock_audit_log):
    """测试带选项的临时文件创建"""
    suffix = '.txt'
    prefix = 'test_prefix_'
    
    with TempfileManager.create_temp_file(suffix=suffix, prefix=prefix) as path:
        filename = os.path.basename(path)
        assert filename.startswith(prefix)
        assert filename.endswith(suffix)
        assert os.path.exists(path)

def test_create_temp_file_no_delete(mock_audit_log):
    """测试 delete=False 选项"""
    path = None
    try:
        with TempfileManager.create_temp_file(delete=False) as tmp_path:
            path = tmp_path
            assert os.path.exists(path)
        
        # 上下文结束后应仍然存在
        assert os.path.exists(path)
        
        # 验证日志记录
        with open(mock_audit_log, "r") as f:
            content = f.read()
            assert path in content
            
    finally:
        # 清理
        if path and os.path.exists(path):
            os.remove(path)

def test_create_temp_file_exception(mock_audit_log):
    """测试发生异常时是否自动清理"""
    path = None
    try:
        with TempfileManager.create_temp_file() as tmp_path:
            path = tmp_path
            assert os.path.exists(path)
            raise ValueError("Test exception")
    except ValueError:
        pass
    
    # 即使发生异常，默认也应该清理
    assert not os.path.exists(path)

def test_cleanup_stale_files(mock_audit_log):
    """测试清理陈旧文件功能"""
    # 1. 创建几个文件，模拟残留
    files_to_create = []
    for _ in range(3):
        # 使用 delete=False 模拟残留
        with TempfileManager.create_temp_file(delete=False) as path:
            files_to_create.append(path)
    
    # 确认文件存在且记录在日志中
    with open(mock_audit_log, "r") as f:
        log_content = f.read()
        for path in files_to_create:
            assert os.path.exists(path)
            assert path in log_content
            
    # 2. 手动删除其中一个，模拟已经被外部清理
    os.remove(files_to_create[0])
    
    # 3. 执行清理
    cleaned_count = TempfileManager.cleanup_stale_files()
    
    # 4. 验证结果
    # 应该清理了剩下的 2 个文件
    assert cleaned_count == 2
    
    # 所有文件都不应该存在了
    for path in files_to_create:
        assert not os.path.exists(path)
        
    # 日志文件应该被清空或删除（如果没有剩余记录）
    if mock_audit_log.exists():
        with open(mock_audit_log, "r") as f:
            assert f.read().strip() == ""
