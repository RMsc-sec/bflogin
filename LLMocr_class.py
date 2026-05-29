"""
基于大模型的OCR识别类 - SDK版本

特性:
1. 支持普通字符验证码和数学计算题验证码
2. 支持base64和原始二进制图片
3. 超时控制和重试机制
"""

import re
import time
import requests
import base64
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API_URL = "https://openrouter.ai/api/v1/chat/completions"
# MODEL_NAME = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
# MAX_RETRY = 3
# REQUEST_TIMEOUT = 30

# API_URL = "https://127.0.0.1:11434/api/v1/chat/completions"
# MODEL_NAME = "qwen3-vl:4b"
# MAX_RETRY = 3
# REQUEST_TIMEOUT = 30

class LLMocr:
    """大模型OCR识别类"""
    
    # Ollama API配置
    API_URL = "https://api.siliconflow.cn/v1/chat/completions"
    MODEL_NAME = "Qwen/Qwen3-VL-8B-Thinking"
    REQUEST_TIMEOUT = 30
    MAX_RETRY = 3
    
    def __init__(self, verify_type: str = "math", digits: int = 6):
        """
        初始化OCR识别器
        
        Args:
            verify_type: 验证码类型，normal（普通字符）或 math（数学计算）
            digits: 验证码位数
        """
        self.verify_type = verify_type
        self.digits = digits
        logger.info(f"LLMocr initialized with type={verify_type}, digits={digits}")
    
    def is_base64(self, data: bytes) -> bool:
        """判断数据是否为base64编码"""
        try:
            decoded = base64.b64decode(data, validate=True)
            return base64.b64encode(decoded) == data
        except Exception:
            return False
    
    def build_payload(self, image_base64: str) -> dict:
        """根据验证类型动态构建payload"""
        if self.verify_type == "normal":
            user_prompt = (
                f"你需要对下面发送的图片进行OCR识别，"
                f"所有图片都是{self.digits}位字符，"
                f"你只需要回答我{self.digits}位字符，不要多余内容。"
            )
            messages = [
                {
                    "role": "user",
                    "content": user_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": ""},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ]
        else:
            user_prompt = (
                f"你需要对下面发送的图片进行OCR识别并计算，"
                f"所有图片都是{self.digits}位数字的计算题，"
                f"你只需要给出计算结果，不要多余内容。"
            )
            messages = [
                {
                    "role": "user",
                    "content": user_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": ""},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ]
        
        return {
            "model": self.MODEL_NAME,
            "stream": False,
            "messages": messages
        }
    
    def process_ocr(self, image_base64: str) -> str | None:
        """执行OCR识别的核心函数"""
        payload = self.build_payload(image_base64)
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer sk-xxxx"
        }
        for attempt in range(self.MAX_RETRY):
            try:
                resp = requests.post(self.API_URL, json=payload, headers=headers, timeout=self.REQUEST_TIMEOUT)
                logger.debug(f"HTTP {resp.status_code} | Attempt {attempt + 1}")
                
                resp.raise_for_status()
                data = resp.json()
                
                if "choices" in data and data["choices"]:
                    content = data["choices"][0]["message"]["content"]
                    
                    if self.verify_type == "normal":
                        match = re.search(r'\w+', content)
                        if match:
                            return match.group()[:self.digits]
                    
                    match = re.search(r'\d+', content)
                    if match:
                        return match.group()
                    
                    return content.strip()
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout on attempt {attempt + 1}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {e}")
            
            time.sleep(1)
        
        return None
    
    def handle_image_data(self, raw_data: bytes) -> str:
        """处理图片数据，自动判断base64或原始二进制"""
        if self.is_base64(raw_data):
            image_base64 = raw_data.decode('utf-8').strip()
            logger.info("Received base64 encoded image")
            return image_base64
        else:
            image_base64 = base64.b64encode(raw_data).decode('utf-8')
            logger.info("Received raw binary image, encoded to base64")
            return image_base64
    
    def recognize(self, image_data: bytes) -> str | None:
        """
        识别验证码图片
        
        Args:
            image_data: 图片数据，可以是base64编码的bytes或原始二进制图片数据
        
        Returns:
            识别结果字符串，失败返回None
        """
        try:
            image_base64 = self.handle_image_data(image_data)
            result = self.process_ocr(image_base64)
            logger.info(f"OCR result: {result}")
            return result
        except Exception as e:
            logger.error(f"OCR recognition error: {e}")
            return None


if __name__ == "__main__":
    # 测试示例
    ocr = LLMocr(verify_type="math", digits=6)
    print("LLMocr class initialized successfully")
