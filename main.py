import os
import sys
import importlib.util
import logging
import traceback
import platform

# 确保 src/ 目录可以被 Python 识别
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

# ✅ 配置全局 logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
        logging.FileHandler("app.log", encoding="utf-8")  # 记录到日志文件
    ]
)

# 检查必要的依赖项
def check_dependencies():
    """检查必要的依赖项是否安装"""
    missing_deps = []
    
    # 检查opuslib
    if importlib.util.find_spec("opuslib") is None:
        missing_deps.append("opuslib")
    
    # 检查pyaudio
    if importlib.util.find_spec("pyaudio") is None:
        missing_deps.append("pyaudio")
    
    # 检查cryptography
    if importlib.util.find_spec("cryptography") is None:
        missing_deps.append("cryptography")
    
    # 检查paho-mqtt
    if importlib.util.find_spec("paho.mqtt") is None:
        missing_deps.append("paho-mqtt")
    
    if missing_deps:
        logging.error("❌ 缺少必要的依赖项: %s", ", ".join(missing_deps))
        logging.error("请使用以下命令安装: pip install %s", " ".join(missing_deps))
        return False
    
    return True

def main():
    # 检查依赖项
    if not check_dependencies():
        return 1
    
    logging.info("✅ 依赖项检查通过")
    logging.info("✅ 日志系统已初始化")

    try:
        # 从这里开始导入依赖的模块
        from src.ota import get_ota_version
        from src.mqtt_client import MQTTClient
        from src.gui import GUI
        
        # 打印系统信息，便于调试
        logging.info(f"操作系统: {platform.system()} {platform.release()}")
        
        """程序入口"""
        # 获取 OTA 版本 & MQTT 服务器信息
        get_ota_version()

        # 启动 MQTT
        mqtt_client = MQTTClient()

        # 启动 GUI
        gui = GUI(mqtt_client=mqtt_client)
        mqtt_client.gui = gui

    except Exception as e:
        logging.error(f"❌ 程序运行出错: {str(e)}")
        logging.error(f"错误详情:\n{traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    main()
