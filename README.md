# py-xiaozhi

## 项目简介

py-xiaozhi 是一个使用 Python 实现的小智语音客户端，旨在通过代码学习和在没有硬件条件下体验 AI 小智的语音功能。
本仓库是基于 zhh827 的[py-xiaozhi](https://github.com/zhh827/py-xiaozhi/tree/main)优化再新增功能

## 项目背景

- 原始硬件项目：[xiaozhi-esp32](https://github.com/78/xiaozhi-esp32)
- 参考 Python 实现：[py-xiaozhi](https://github.com/zhh827/py-xiaozhi/tree/main)

## 演示

- [Bilibili 演示视频](https://b23.tv/GbXeLHX)

## 功能特点

- 语音交互
- 图形化界面
- 音量控制
- 会话管理
- 加密音频传输

## 环境要求

- Python 3.8+（推荐 3.12）
- Windows/Linux/macOS

## 安装依赖

### Windows 环境

1. 克隆项目

```bash
git clone https://github.com/Huang-junsen/py-xiaozhi.git
cd py-xiaozhi
```

2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

3. 拷贝 opus.dll

- 将 `opus.dll` 拷贝到 `C:\Windows\System32` 目录

4. 系统依赖

- 需要安装 [FFmpeg](https://ffmpeg.org/download.html)

### Linux/macOS 环境

1. 安装系统依赖：

- Linux:

```bash
sudo apt-get install python3-pyaudio portaudio19-dev ffmpeg
```

- MacOS:

```bash
brew install portaudio opus python-tk ffmpeg
```

PS: 可能有其他未补全的，还请自行根据报错安装对应依赖

2. 拉取项目和依赖

```bash
git clone https://github.com/Huang-junsen/py-xiaozhi.git
cd py-xiaozhi
pip3 install -r requirements.txt
```

### 使用虚拟环境进行依赖安装

```bash
// 创建虚拟环境：
python3 -m venv .venv
// 激活虚拟环境：
source .venv/bin/activate
pip3 install -r requirements.txt
```

## 运行

```bash
python main.py
```

## 使用说明

- 启动应用程序后，GUI 界面会自动连接
- 点击并按住 "按住说话" 按钮开始语音交互
- 松开按钮结束语音输入

## 已知问题

- 需要稳定的网络连接
- 音频设备兼容性可能存在差异

## 已实现功能

- [x] 优化了 goodbye 后无法重连问题
- [x] 新增 GUI 页面，无需在控制台一直按空格
- [x] 拆分代码，封装为类，各司其职
- [x] 控制 windows、mac 音量大小（linux 需要自行实现）
- [x] MAC_ADDR 自动获取（解决 mac 地址冲突问题）

## 待实现功能

- [ ] WebSocket 通信（开发中）
- [ ] 新 GUI （Electron）
- [ ] 第三方音乐库

## 贡献

欢迎提交 Issues 和 Pull Requests！

## 免责声明

本项目仅用于学习和研究目的，不得用于商业用途。

## 感谢以下开源人员

[Xiaoxia](https://github.com/78)
[zhh827](https://github.com/zhh827)
