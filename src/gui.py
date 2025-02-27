import threading
import tkinter as tk
from tkinter import ttk, messagebox
import src.config
import socket
import time
import platform
import subprocess
import concurrent.futures
from src.audio_transmission import check_microphone_permission  # 导入权限检查函数

class GUI:
    def __init__(
        self,
        mqtt_client
    ):
        self.mqtt_client = mqtt_client
        """创建 GUI 界面"""
        root = tk.Tk()
        self.root = root
        self.root.title("小智语音控制")
        self.root.geometry("300x200")
        
        # 音量控制相关变量初始化
        self.volume_timer = None
        self.volume_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.last_volume = 50  # 初始音量值
        self.volume_debounce_time = 300  # 防抖动时间(毫秒)

        # 状态显示
        self.status_frame = ttk.Frame(root)
        self.status_frame.pack(pady=10)

        self.status_label = ttk.Label(self.status_frame, text="状态: 未连接")
        self.status_label.pack(side=tk.LEFT)

        # 音量控制
        self.volume_frame = ttk.Frame(root)
        self.volume_frame.pack(pady=10)

        ttk.Label(self.volume_frame, text="音量:").pack(side=tk.LEFT)
        self.volume_scale = ttk.Scale(
            self.volume_frame,
            from_=0,
            to=100,
            command=lambda v: self.handle_volume_change(int(float(v)))
        )
        self.volume_scale.set(50)
        self.volume_scale.pack(side=tk.LEFT, padx=10)

        # 控制按钮
        self.btn_frame = ttk.Frame(root)
        self.btn_frame.pack(pady=20)

        self.talk_btn = ttk.Button(self.btn_frame, text="按住说话")
        self.talk_btn.bind("<ButtonPress-1>", self.on_button_press)
        self.talk_btn.bind("<ButtonRelease-1>", self.on_button_release)
        self.talk_btn.pack(side=tk.LEFT, padx=10)

        # 状态更新线程
        threading.Thread(target=self.update_status, daemon=True).start()
        
        # 检查麦克风权限
        self.root.after(500, self.check_mic_permission)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()
    
    def check_mic_permission(self):
        """检查麦克风权限，并在必要时显示提示"""
        if not check_microphone_permission():
            messagebox.showwarning(
                "需要麦克风权限", 
                "请授予麦克风访问权限:\n"
                "1. 打开 系统设置 > 隐私与安全性 > 麦克风\n"
                "2. 找到 Python 或 Terminal 应用并允许访问\n"
                "3. 重新启动本程序"
            )
            self.talk_btn.config(state="disabled")  # 禁用按钮
            self.status_label.config(text="状态: 无麦克风权限")
    
    def on_button_press(self, event):
        """按钮按下事件处理
        功能流程：
        1. 检查连接状态，必要时重建连接
        2. 发送hello协议建立会话
        3. 如果正在TTS播放则发送终止指令
        4. 发送listen指令启动语音采集
        """
        # 检查连接状态和会话
        if not self.mqtt_client.conn_state or not self.mqtt_client.session_id:
            # 清理旧连接状态
            src.config.listen_state = None
            
            # 发送设备握手协议
            hello_msg = {
                "type": "hello",
                "version": 3,
                "transport": "udp",
                "audio_params": {
                    "format": "opus",
                    "sample_rate": 16000,  # 16kHz采样率
                    "channels": 1,  # 单声道
                    "frame_duration": 60  # 60ms帧时长
                }
            }
            self.mqtt_client.publish(hello_msg)
            # 等待连接建立
            time.sleep(0.5)

        # 中断正在播放的语音
        if self.mqtt_client.tts_state in ["start", "entence_start"]:
            self.mqtt_client.publish({
                "type": "abort"
            })

        # 启动语音采集
        session_id = self.mqtt_client.session_id
        if session_id:
            # 设置监听状态为开始
            src.config.listen_state = "start"
            listen_msg = {
                "session_id": session_id,
                "type": "listen",
                "state": "start",
                "mode": "manual"
            }
            self.mqtt_client.publish(listen_msg)

    def on_button_release(self, event):
        """按钮释放事件处理
        发送停止录音指令
        """
        # 设置监听状态为停止
        src.config.listen_state = "stop"
        session_id = self.mqtt_client.session_id
        if session_id:
            stop_msg = {
                "session_id": session_id,
                "type": "listen",
                "state": "stop"
            }
            self.mqtt_client.publish(stop_msg)

    def update_status(self):
        """更新状态显示"""
        status = "已连接" if self.mqtt_client.conn_state else "未连接"
        self.status_label.config(text=f"状态: {status} | TTS状态: {self.mqtt_client.tts_state}")
        self.root.after(1000, self.update_status)

    def on_close(self):
        """关闭窗口时退出"""
        if hasattr(self, 'volume_executor'):
            self.volume_executor.shutdown(wait=False)
        self.root.destroy()

    def handle_volume_change(self, volume: int):
        """处理音量变化的防抖动函数
        
        Args:
            volume: 音量值(0-100)
        """
        # 如果值没变，不做任何操作
        if volume == self.last_volume:
            return
            
        # 更新最后的音量值
        self.last_volume = volume
        
        # 取消之前的定时任务（如果存在）
        if self.volume_timer:
            self.root.after_cancel(self.volume_timer)
            
        # 设置新的定时任务，延迟执行音量更新
        self.volume_timer = self.root.after(
            self.volume_debounce_time, 
            lambda: self.volume_executor.submit(self.update_volume, volume)
        )
        
    def update_volume(self, volume: int):
        """更新系统音量
        Args:
            volume: 音量值(0-100)
        """
        system = platform.system()
        
        try:
            if system == "Windows":
                # Windows音量控制
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume_control = cast(interface, POINTER(IAudioEndpointVolume))

                # 将0-100的值转换为-65.25到0的分贝值
                volume_db = -65.25 * (1 - volume/100.0)
                volume_control.SetMasterVolumeLevel(volume_db, None)
            
            elif system == "Darwin":  # macOS
                # macOS音量控制 (使用osascript)
                subprocess.run(["osascript", "-e", f"set volume output volume {volume}"], 
                               capture_output=True)  # 捕获输出避免打印到控制台
            
            else:
                print(f"不支持在 {system} 平台上设置音量")

            print(f"音量设置为: {volume}")
        
        except Exception as e:
            print(f"设置音量失败: {e}")
