#!/bin/bash

echo "========================================"
echo "ESP32-S3 Sense 相机MQTT项目 - 安装脚本"
echo "========================================"
echo

echo "正在检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python3环境"
    echo "请先安装Python 3.7或更高版本"
    echo "Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "CentOS/RHEL: sudo yum install python3 python3-pip"
    echo "macOS: brew install python3"
    exit 1
fi

echo "✅ Python环境检查通过"
echo "Python版本: $(python3 --version)"
echo

echo "正在安装Python依赖包..."
python3 -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ 依赖包安装失败"
    exit 1
fi

echo
echo "✅ 安装完成！"
echo
echo "现在你可以运行以下命令启动接收器："
echo
echo "GUI版本（推荐）："
echo "  python3 windows_receiver_gui.py"
echo
echo "命令行版本："
echo "  python3 windows_receiver.py"
echo 