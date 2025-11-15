import base64
from pathlib import Path
from typing import List

class FileHandler:
    """文件处理工具"""
    
    @staticmethod
    def read_image_as_base64(file_path: str) -> str:
        """读取图片并转为 base64"""
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    @staticmethod
    def save_report(report: str, output_path: str):
        """保存报告到文件"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
    
    @staticmethod
    def validate_files(file_paths: List[str]) -> List[str]:
        """验证文件是否存在"""
        valid_files = []
        for path in file_paths:
            if Path(path).exists():
                valid_files.append(path)
            else:
                print(f"警告: 文件不存在 - {path}")
        return valid_files
