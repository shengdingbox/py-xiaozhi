import pyaudio
import opuslib
import socket
import time
import logging
import src.config
import platform
import subprocess
import sys
from src.utils import aes_ctr_encrypt, aes_ctr_decrypt

# 初始化 PyAudio
audio = pyaudio.PyAudio()


def check_microphone_permission():
    """检查麦克风权限，并引导用户开启权限
    
    Returns:
        bool: 是否有麦克风权限
    """
    system = platform.system()
    
    if system == "Darwin":  # macOS
        try:
            # 尝试列出音频设备
            devices = audio.get_device_count()
            
            # 尝试打开一个临时的音频流测试权限
            temp_stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=960,
                start=False  # 不实际启动流
            )
            temp_stream.close()
            return True
        except Exception as e:
            if "Internal PortAudio error" in str(e):
                logging.error("❌ 麦克风权限被拒绝")
                print("\n")
                print("="*60)
                print("⚠️  需要麦克风权限")
                print("请按照以下步骤授予权限:")
                print("1. 打开 系统设置 > 隐私与安全性 > 麦克风")
                print("2. 找到 Python 或 Terminal 应用并允许麦克风访问")
                print("3. 重新启动本程序")
                print("="*60)
                print("\n")
                return False
    
    # 对于其他系统，默认认为有权限
    return True


def send_audio():
    """音频采集和发送线程函数
    1. 采集麦克风音频数据
    2. 使用 Opus 进行音频编码
    3. 使用 AES-CTR 进行加密
    4. 通过 UDP 发送音频数据
    """
    # 首先检查麦克风权限
    if not check_microphone_permission():
        logging.error("❌ 无法访问麦克风，请授予权限后重试")
        return

    key = src.config.aes_opus_info['udp']['key']
    nonce = src.config.aes_opus_info['udp']['nonce']
    server_ip = src.config.aes_opus_info['udp']['server']
    server_port = src.config.aes_opus_info['udp']['port']

    # 初始化 Opus 编码器
    try:
        encoder = opuslib.Encoder(16000, 1, opuslib.APPLICATION_AUDIO)
    except Exception as e:
        logging.error(f"❌ Opus 编码器初始化失败: {e}")
        logging.error("请确保已安装 opus 库: pip install opuslib")
        return

    if audio is None:
        logging.error("❌ PyAudio 未初始化！")
        return
    if src.config.udp_socket is None:
        logging.error("❌ UDP 套接字未初始化！")
        return

    # 打开麦克风流 (帧大小应与 Opus 编码器匹配)
    try:
        mic = audio.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=960)
        logging.info("✅ 成功打开麦克风")
    except Exception as e:
        logging.error(f"❌ 无法打开麦克风: {e}")
        return

    # 连接到UDP服务器
    try:
        src.config.udp_socket.connect((server_ip, server_port))
        logging.info(f"✅ 已连接到UDP服务器 {server_ip}:{server_port}")
    except Exception as e:
        logging.error(f"❌ UDP连接失败: {e}")
        mic.close()
        return

    try:
        while src.config.udp_socket:
            # 如果监听状态是 "stop"，则暂停发送
            if src.config.listen_state is not None and src.config.listen_state == "stop":
                time.sleep(0.1)
                continue

            # 读取 960 采样点的音频数据
            data = mic.read(960, exception_on_overflow=False)

            # Opus 编码（将 PCM 音频数据压缩）
            encoded_data = encoder.encode(data, 960)
            src.config.local_sequence += 1  # 更新音频数据的序列号

            # 🔹 生成新的 nonce（加密 IV）
            new_nonce = nonce[:4] + format(len(encoded_data), '04x') + nonce[8:24] + format(src.config.local_sequence, '08x')

            # 🔹 AES 加密 Opus 编码数据
            encrypt_encoded_data = aes_ctr_encrypt(
                bytes.fromhex(key),
                bytes.fromhex(new_nonce),
                bytes(encoded_data)
            )

            # 🔹 拼接 nonce 和密文
            packet_data = bytes.fromhex(new_nonce) + encrypt_encoded_data

            # 发送音频数据
            if src.config.udp_socket:
                try:
                    src.config.udp_socket.send(packet_data)
                except (socket.error, OSError) as e:
                    logging.error(f"❌ UDP发送错误: {e}")
                    break

    except Exception as e:
        logging.error(f"❌ send_audio 发生错误: {e}")

    finally:
        logging.info("🔴 send_audio 线程退出")
        src.config.local_sequence = 0  # 归零序列号
        mic.stop_stream()
        mic.close()


def recv_audio():
    """音频接收和播放线程函数
    1. 通过 UDP 接收音频数据
    2. 使用 AES-CTR 进行解密
    3. 使用 Opus 进行解码
    4. 播放 PCM 音频
    """

    key = src.config.aes_opus_info['udp']['key']
    nonce = src.config.aes_opus_info['udp']['nonce']
    sample_rate = src.config.aes_opus_info['audio_params']['sample_rate']
    frame_duration = src.config.aes_opus_info['audio_params']['frame_duration']

    # 🔹 计算 Opus 解码所需的帧数
    frame_num = int(sample_rate * (frame_duration / 1000))

    logging.info(f"🔵 recv_audio: 采样率 -> {sample_rate}, 帧时长 -> {frame_duration}ms, 帧数 -> {frame_num}")

    # 初始化 Opus 解码器
    try:
        decoder = opuslib.Decoder(sample_rate, 1)
    except Exception as e:
        logging.error(f"❌ Opus 解码器初始化失败: {e}")
        logging.error("请确保已安装 opus 库: pip install opuslib")
        return

    # 确保 `audio` 正确初始化
    if audio is None:
        logging.error("❌ PyAudio 未初始化！")
        return

    # 打开扬声器输出流
    try:
        spk = audio.open(format=pyaudio.paInt16, channels=1, rate=sample_rate, output=True, frames_per_buffer=frame_num)
    except Exception as e:
        logging.error(f"❌ 无法打开音频输出设备: {e}")
        return

    try:
        while src.config.udp_socket:
            try:
                # 监听 UDP 端口接收音频数据
                data, _ = src.config.udp_socket.recvfrom(4096)
                
                # 🔹 分离 nonce 和加密音频数据
                received_nonce = data[:16]
                encrypted_audio = data[16:]

                # 🔹 AES 解密
                decrypted_audio = aes_ctr_decrypt(
                    bytes.fromhex(key),
                    received_nonce,
                    encrypted_audio
                )

                # 🔹 Opus 解码（将解密后的数据转换为 PCM）
                pcm_audio = decoder.decode(decrypted_audio, frame_num)

                # 播放解码后的 PCM 音频
                spk.write(pcm_audio)
            except (socket.error, OSError) as e:
                if src.config.udp_socket is None:
                    break  # 正常退出
                logging.error(f"❌ UDP接收错误: {e}")
                time.sleep(0.5)  # 避免错误循环消耗CPU
                if "Bad file descriptor" in str(e):
                    break  # 套接字已关闭，退出循环

    except Exception as e:
        logging.error(f"❌ recv_audio 发生错误: {e}")
    
    finally:
        logging.info("🔴 recv_audio 线程退出")
        spk.stop_stream()
        spk.close()
