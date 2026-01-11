import os
import tempfile
from contextlib import contextmanager
from typing import Generator, Optional, Union
from .config import settings



# 临时文件审计日志路径
AUDIT_LOG_PATH = os.path.join(tempfile.gettempdir(), "vp_app_temp_files.log")

class TempfileManager:
    """
    临时文件管理器，用于安全地创建和管理临时文件。
    """

    @staticmethod
    def _log_temp_file(path: str) -> None:
        """记录创建的临时文件路径到审计日志"""
        try:
            with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"{path}\n")
        except Exception:
            # 记录日志失败不应阻塞主流程
            pass

    @staticmethod
    def cleanup_stale_files() -> int:
        """
        清理所有记录在审计日志中的临时文件。
        通常在应用启动或关闭时调用。
        
        Returns:
            int: 成功清理的文件数量
        """
        if not os.path.exists(AUDIT_LOG_PATH):
            return 0

        files_to_keep = []
        cleaned_count = 0
        
        try:
            with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
                paths = set(line.strip() for line in f if line.strip())
            
            for path in paths:
                if os.path.exists(path):
                    try:
                        if os.path.isfile(path):
                            os.remove(path)
                            cleaned_count += 1
                        # 如果是目录等其他情况暂不处理，防止误删
                    except OSError:
                        # 删除失败（可能正在被使用），保留记录
                        files_to_keep.append(path)
                # 如果文件不存在，说明已经被正常清理，无需保留记录

            # 重写日志文件，只保留未删除的文件
            if files_to_keep:
                with open(AUDIT_LOG_PATH, "w", encoding="utf-8") as f:
                    for path in files_to_keep:
                        f.write(f"{path}\n")
            else:
                # 如果没有需要保留的文件，删除日志文件
                try:
                    os.remove(AUDIT_LOG_PATH)
                except OSError:
                    pass
                    
        except Exception:
            return 0
            
        return cleaned_count

    @staticmethod
    @contextmanager
    def create_temp_file(
        suffix: Optional[str] = None,
        prefix: Optional[str] = None,
        dir: Optional[str] = settings.TMP_DIR,
        mode: str = "w+b",
        delete: bool = True,
    ) -> Generator[str, None, None]:
        """
        创建一个临时文件上下文管理器，yield 文件路径。
        在进入上下文前文件会被创建并关闭（释放句柄），确保其他进程或库可以通过路径访问。
        在退出上下文时，根据 delete 参数决定是否删除文件。

        Args:
            suffix: 文件名后缀
            prefix: 文件名前缀
            dir: 存放目录，如果为None则使用系统默认临时目录
            mode: 文件打开模式，默认为二进制读写
            delete: 退出上下文时是否删除文件，默认为 True

        Yields:
            str: 临时文件的绝对路径
        """
        # delete=False 传递给 NamedTemporaryFile，因为我们需要手动控制删除时机
        # 且为了兼容性（如在Windows上或某些库需要通过路径再次打开文件），我们先关闭它。
        tmp_file = tempfile.NamedTemporaryFile(
            suffix=suffix, prefix=prefix, dir=dir, mode=mode, delete=False
        )
        
        try:
            # 关闭文件句柄，只保留路径
            tmp_file.close()
            
            # 记录到审计日志
            TempfileManager._log_temp_file(tmp_file.name)
            
            yield tmp_file.name
        finally:
            if delete and os.path.exists(tmp_file.name):
                try:
                    os.remove(tmp_file.name)
                except OSError:
                    # 记录错误或忽略，这里选择忽略以免影响主流程，
                    # 实际生产中可能需要 log warning
                    pass
