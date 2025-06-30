@echo off
echo ========================================
echo ESP32-S3 Sense 相机MQTT项目 - 安装脚本
echo ========================================
echo.

echo 正在检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到Python环境
    echo 请先安装Python 3.7或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python环境检查通过
echo.

echo 正在安装Python依赖包...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ 依赖包安装失败
    pause
    exit /b 1
)

echo.
echo ✅ 安装完成！
echo.
echo 现在你可以运行以下命令启动接收器：
echo.
echo GUI版本（推荐）：
echo   python windows_receiver_gui.py
echo.
echo 命令行版本：
echo   python windows_receiver.py
echo.
pause 