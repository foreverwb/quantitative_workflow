"""
文件处理器
支持多图片上传、格式检测、base64 编码
"""

import base64
import mimetypes
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from loguru import logger
from PIL import Image


class FileHandler:
    """文件处理器类"""
    
    # 支持的图片格式
    SUPPORTED_IMAGE_FORMATS = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.svg': 'image/svg+xml'
    }
    
    def __init__(self, max_size_mb: int = 10):
        """
        初始化文件处理器
        
        Args:
            max_size_mb: 单个文件最大大小(MB)
        """
        self.max_size_bytes = max_size_mb * 1024 * 1024
    
    def scan_folder(self, folder_path: Path) -> List[Path]:
        """
        扫描文件夹,获取所有支持的图片文件
        
        Args:
            folder_path: 文件夹路径
            
        Returns:
            图片文件路径列表
        """
        if not folder_path.exists():
            raise FileNotFoundError(f"文件夹不存在: {folder_path}")
        
        if not folder_path.is_dir():
            raise ValueError(f"路径不是文件夹: {folder_path}")
        
        image_files = []
        
        # 遍历所有支持的格式
        for ext in self.SUPPORTED_IMAGE_FORMATS.keys():
            # 大小写都匹配
            image_files.extend(folder_path.glob(f'*{ext}'))
            image_files.extend(folder_path.glob(f'*{ext.upper()}'))
        
        # 排序(按文件名)
        image_files = sorted(set(image_files))
        
        logger.info(f"📁 扫描文件夹: {folder_path}")
        logger.info(f"🖼️  找到 {len(image_files)} 个图片文件")
        
        for file in image_files:
            logger.debug(f"  - {file.name} ({self._format_size(file.stat().st_size)})")
        
        return image_files
    
    def validate_file(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        验证文件是否有效
        
        Args:
            file_path: 文件路径
            
        Returns:
            (是否有效, 错误信息)
        """
        # 检查文件是否存在
        if not file_path.exists():
            return False, f"文件不存在: {file_path}"
        
        # 检查文件大小
        file_size = file_path.stat().st_size
        if file_size == 0:
            return False, f"文件为空: {file_path.name}"
        
        if file_size > self.max_size_bytes:
            return False, f"文件过大: {file_path.name} ({self._format_size(file_size)})"
        
        # 检查文件格式
        ext = file_path.suffix.lower()
        if ext not in self.SUPPORTED_IMAGE_FORMATS:
            return False, f"不支持的格式: {ext}"
        
        # 尝试打开图片(验证完整性)
        try:
            with Image.open(file_path) as img:
                img.verify()
            return True, None
        except Exception as e:
            return False, f"图片损坏: {file_path.name} - {str(e)}"
    
    def encode_image_to_base64(self, file_path: Path) -> str:
        """
        将图片编码为 base64 字符串
        
        Args:
            file_path: 图片文件路径
            
        Returns:
            base64 编码的字符串
        """
        with open(file_path, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def get_media_type(self, file_path: Path) -> str:
        """
        获取文件的 MIME 类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            MIME 类型字符串
        """
        ext = file_path.suffix.lower()
        return self.SUPPORTED_IMAGE_FORMATS.get(ext, 'image/png')
    
    def create_vision_message_content(
        self, 
        text: str, 
        image_paths: List[Path]
    ) -> List[Dict]:
        """
        创建视觉消息内容(用于 OpenAI/Claude 等模型)
        
        Args:
            text: 文本内容
            image_paths: 图片路径列表
            
        Returns:
            消息内容列表
        """
        content = [{"type": "text", "text": text}]
        
        for image_path in image_paths:
            # 验证文件
            is_valid, error_msg = self.validate_file(image_path)
            if not is_valid:
                logger.warning(f"⚠️ 跳过无效文件: {error_msg}")
                continue
            
            # 编码图片
            try:
                base64_image = self.encode_image_to_base64(image_path)
                media_type = self.get_media_type(image_path)
                
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{media_type};base64,{base64_image}",
                        "detail": "high"  # 高分辨率分析
                    }
                })
                
                logger.debug(f"✅ 已编码: {image_path.name}")
                
            except Exception as e:
                logger.error(f"❌ 编码失败: {image_path.name} - {str(e)}")
                continue
        
        return content
    
    def classify_images_by_command(self, image_paths: List[Path]) -> Dict[str, List[Path]]:
        """
        根据文件名中的命令关键词分类图片
        
        Args:
            image_paths: 图片路径列表
            
        Returns:
            按命令分类的字典 {"gexr": [...], "trigger": [...], ...}
        """
        # 命令关键词映射
        command_keywords = {
            'gexr': ['gexr'],
            'trigger': ['trigger'],
            'dexn': ['dexn'],
            'vanna': ['vanna'],
            'skew': ['skew', 'iv'],
            'term': ['term'],
            'vexn': ['vexn'],
            'iv_path': ['iv_path', 'ivpath']
        }
        
        classified = {key: [] for key in command_keywords.keys()}
        classified['other'] = []
        
        for image_path in image_paths:
            filename_lower = image_path.name.lower()
            
            matched = False
            for category, keywords in command_keywords.items():
                if any(keyword in filename_lower for keyword in keywords):
                    classified[category].append(image_path)
                    matched = True
                    break
            
            if not matched:
                classified['other'].append(image_path)
        
        # 记录分类结果
        logger.info("📊 图片分类结果:")
        for category, files in classified.items():
            if files:
                logger.info(f"  {category}: {len(files)} 个文件")
                for file in files:
                    logger.debug(f"    - {file.name}")
        
        return classified
    
    def check_required_files(self, classified: Dict[str, List[Path]]) -> Dict[str, bool]:
        """
        检查必需的文件是否存在
        
        Args:
            classified: 分类后的文件字典
            
        Returns:
            检查结果 {"gexr": True/False, ...}
        """
        # 必需的命令类型
        required_commands = ['gexr', 'trigger', 'dexn', 'vanna', 'skew']
        
        check_result = {}
        missing = []
        
        for cmd in required_commands:
            has_files = len(classified.get(cmd, [])) > 0
            check_result[cmd] = has_files
            
            if not has_files:
                missing.append(cmd)
        
        if missing:
            logger.warning(f"⚠️ 缺失必需的数据类型: {', '.join(missing)}")
            logger.info("💡 提示: 确保上传包含以下命令输出的图片:")
            logger.info(f"  必需: {', '.join(required_commands)}")
            logger.info(f"  可选: term, vexn, iv_path")
        else:
            logger.success("✅ 所有必需的数据类型都已提供")
        
        return check_result
    
    def prepare_images_for_analysis(
        self, 
        folder_path: Path,
        text_prompt: str
    ) -> Tuple[List[Dict], Dict[str, bool]]:
        """
        准备用于分析的图片(完整流程)
        
        Args:
            folder_path: 数据文件夹路径
            text_prompt: 文本提示词
            
        Returns:
            (消息内容列表, 必需文件检查结果)
        """
        # 1. 扫描文件夹
        image_paths = self.scan_folder(folder_path)
        
        if not image_paths:
            raise ValueError(f"文件夹中没有找到图片文件: {folder_path}")
        
        # 2. 分类图片
        classified = self.classify_images_by_command(image_paths)
        
        # 3. 检查必需文件
        check_result = self.check_required_files(classified)
        
        # 4. 创建视觉消息
        message_content = self.create_vision_message_content(
            text=text_prompt,
            image_paths=image_paths
        )
        
        logger.info(f"✅ 准备完成: {len(image_paths)} 个图片已编码")
        
        return message_content, check_result
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


# 使用示例
if __name__ == "__main__":
    from pathlib import Path
    
    handler = FileHandler(max_size_mb=10)
    
    # 示例1: 扫描文件夹
    try:
        folder = Path("data/uploads/AAPL_20240115")
        message_content, check_result = handler.prepare_images_for_analysis(
            folder_path=folder,
            text_prompt="请解析 AAPL 的期权数据"
        )
        
        print(f"\n消息内容: {len(message_content)} 个元素")
        print(f"必需文件检查: {check_result}")
        
    except Exception as e:
        print(f"错误: {e}")