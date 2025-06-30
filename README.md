# ESP32-S3 Sense 相机MQTT项目

这个项目实现了使用XIAO ESP32-S3 Sense开发板拍照并通过MQTT分块传输到服务器的功能。支持实时图片传输、自动重连、错误处理和Windows端GUI接收界面。

## 🚀 功能特性

- **自动连接WiFi网络** - 支持自动重连和连接状态监控
- **高质量拍照** - 使用板载摄像头，支持多种分辨率和JPEG质量设置
- **分块传输** - 通过MQTT协议分块传输大图片，避免单次传输失败
- **完整校验机制** - 图片级和块级MD5校验，确保数据完整性
- **自动重试机制** - 接收端检测重复块和缺失块，支持超时清理
- **Windows GUI界面** - 友好的图形界面，实时显示传输状态和日志
- **多设备支持** - 支持多个ESP32设备同时传输
- **内存优化** - 垃圾回收和内存管理，适合资源受限的ESP32

## 📁 文件说明

### ESP32端文件
- `main_chunked.py` - **推荐使用** - 分块传输版本的主程序
- `main_simple.py` - 简化版本，单次传输完整图片
- `main.py` - 完整版本的主程序（旧版本）
- `config.py` - 配置文件，包含WiFi、MQTT和相机设置
- `test.py` - 测试脚本，用于验证各个功能模块

### Windows端文件
- `windows_receiver_gui.py` - **推荐使用** - 带GUI界面的接收程序
- `windows_receiver.py` - 命令行版本的接收程序
- `requirements.txt` - Windows端Python依赖包

### 文档
- `README.md` - 项目说明文档

## ⚙️ 配置说明

在 `config.py` 文件中可以修改以下配置：

### WiFi配置
```python
WIFI_SSID = "你的WiFi名称"
WIFI_PASSWORD = "你的WiFi密码"
```

### MQTT配置
```python
MQTT_BROKER = "emqx.cidatahub.com"  # MQTT服务器地址
MQTT_PORT = 26701                   # MQTT端口
MQTT_CLIENT_ID = "wifitest"         # 设备ID
MQTT_USERNAME = "nolan"             # MQTT用户名
MQTT_PASSWORD = "opeioe"            # MQTT密码
MQTT_TOPIC = "esp32/camera"         # MQTT主题
```

### 相机配置
```python
CAMERA_JPEG_QUALITY = 90  # JPEG质量 (1-100)
CAMERA_FRAME_SIZE = "HD"  # 分辨率: VGA, SVGA, XGA, HD, SXGA, UXGA
CAMERA_FB_COUNT = 2       # 帧缓冲区数量
```

### 程序配置
```python
PHOTO_INTERVAL = 30  # 拍照间隔（秒）
```

### 分块传输配置
```python
CHUNK_SIZE = 3072  # 每块大小（字节），建议不超过4KB
```

## 🛠️ 使用方法

### ESP32端设置

1. **准备硬件**
   - XIAO ESP32-S3 Sense开发板
   - 确保摄像头模块正常工作

2. **安装MicroPython固件**
   - 下载支持ESP32-S3的MicroPython固件
   - 使用esptool或其他工具烧录固件

3. **上传代码文件**
   ```bash
   # 使用ampy或其他工具上传文件
   ampy --port COM3 put main_chunked.py
   ampy --port COM3 put config.py
   ```

4. **修改配置**
   - 编辑 `config.py` 文件，设置正确的WiFi和MQTT信息

5. **运行程序**
   ```python
   # 在MicroPython REPL中运行
   exec(open('main_chunked.py').read())
   ```

### Windows端设置

1. **安装Python依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **运行接收程序**
   
   **GUI版本（推荐）**：
   ```bash
   python windows_receiver_gui.py
   ```
   
   **命令行版本**：
   ```bash
   python windows_receiver.py
   ```

3. **GUI界面功能**
   - 连接状态显示
   - 启动/停止接收器
   - 实时传输统计
   - 详细日志显示
   - 一键打开图片文件夹

## 📡 分块传输协议

### 传输流程
1. **Header消息** - 发送图片信息头
   - 主题：`esp32/camera/header`
   - 包含：图片MD5、总分块数、图片大小、设备ID等

2. **Chunk消息** - 分块发送图片数据
   - 主题：`esp32/camera/chunk`
   - 包含：块索引、块数据、块MD5、设备ID等

3. **Completion消息** - 发送完成信号
   - 主题：`esp32/camera/completion`
   - 包含：传输完成确认、设备ID等

### 消息格式

#### Header消息
```json
{
    "type": "header",
    "timestamp": 1234567890.123,
    "device_id": "wifitest",
    "image_md5": "abc123...",
    "total_chunks": 27,
    "chunk_size": 3072,
    "image_size": 61619
}
```

#### Chunk消息
```json
{
    "type": "chunk",
    "chunk_index": 0,
    "total_chunks": 27,
    "chunk_data": "base64编码的数据块",
    "chunk_md5": "def456...",
    "device_id": "wifitest",
    "is_last": false
}
```

#### Completion消息
```json
{
    "type": "completion",
    "timestamp": 1234567890.123,
    "device_id": "wifitest",
    "image_md5": "abc123...",
    "total_chunks": 27
}
```

## 🔒 校验机制

- **图片级校验**：使用MD5校验整个图片的完整性
- **块级校验**：每个数据块都有独立的MD5校验
- **自动重试**：接收端会检测重复块和缺失块
- **超时清理**：自动清理超时的未完成传输（默认60秒）
- **错误恢复**：支持网络中断后的自动重连

## 🔧 编码说明

- **ESP32端**：使用`ubinascii.b2a_base64()`进行编码
- **Windows端**：使用`base64.b64decode()`进行解码，支持自动padding处理
- **MD5计算**：ESP32端使用`ubinascii.hexlify()`获取十六进制字符串

## ⚠️ 注意事项

1. **网络要求**
   - 确保WiFi网络稳定且密码正确
   - 确保MQTT服务器地址和端口可访问
   - 建议在稳定的网络环境下使用

2. **性能优化**
   - 分块大小建议不超过4KB，避免MQTT消息过大
   - 可以根据网络状况调整拍照间隔
   - 适当降低图片质量可以减少传输时间

3. **存储管理**
   - Windows端会自动创建`received_images`目录保存图片
   - 定期清理旧图片以节省存储空间
   - ESP32端会进行垃圾回收以释放内存

4. **多设备使用**
   - 每个ESP32设备应使用不同的`MQTT_CLIENT_ID`
   - 接收端支持同时接收多个设备的图片

## 🐛 故障排除

### 常见问题

- **WiFi连接失败**
  - 检查SSID和密码是否正确
  - 确认WiFi信号强度
  - 检查ESP32是否支持该WiFi频段

- **MQTT连接失败**
  - 检查服务器地址、端口和认证信息
  - 确认网络连接正常
  - 检查MQTT服务器是否在线

- **拍照失败**
  - 检查相机连接和初始化
  - 确认摄像头模块正常工作
  - 检查内存是否充足

- **内存不足**
  - 降低图片质量或分辨率
  - 减少帧缓冲区数量
  - 增加垃圾回收频率

- **传输失败**
  - 检查网络稳定性
  - 适当增加分块间隔
  - 减少分块大小

- **解码失败**
  - 检查ubinascii编码是否正确
  - 确认base64数据完整性
  - 检查padding是否正确

- **chunk消息被跳过**
  - 确保ESP32发送的chunk消息包含device_id字段
  - 检查接收端的图片匹配逻辑
  - 确认时间戳格式正确

- **MD5计算错误**
  - 在MicroPython中使用ubinascii.hexlify()来获取MD5的十六进制字符串
  - 确认数据编码格式一致
  - 检查字符串编码方式

### 调试技巧

1. **启用详细日志**
   - ESP32端会输出详细的传输信息
   - Windows GUI端显示实时日志
   - 命令行版本提供详细的状态信息

2. **监控网络状态**
   - 检查WiFi连接状态
   - 监控MQTT连接状态
   - 观察传输成功率

3. **性能监控**
   - 监控内存使用情况
   - 观察传输速度
   - 检查图片质量

## 📦 依赖库

### ESP32端
- **MicroPython固件** - 支持ESP32-S3的MicroPython固件
- **umqtt.simple** - MQTT客户端库
- **camera** - 相机库（ESP32-S3固件自带）
- **ubinascii** - 编码库（MicroPython自带）
- **hashlib** - 哈希计算库（MicroPython自带）
- **network** - 网络库（MicroPython自带）

### Windows端
- **Python 3.7+** - 基础Python环境
- **paho-mqtt** - MQTT客户端库
- **tkinter** - GUI库（Python自带）
- **hashlib** - 哈希计算库（Python自带）
- **base64** - Base64编码库（Python自带）

## 🔄 版本历史

### v2.0 (当前版本)
- ✅ 修复MicroPython中MD5计算问题
- ✅ 修复chunk消息device_id匹配问题
- ✅ 优化GUI界面和用户体验
- ✅ 完善错误处理和日志记录
- ✅ 添加详细的故障排除指南

### v1.0
- 基础的分块传输功能
- 简单的命令行接收器
- 基本的错误处理

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进这个项目！

1. Fork这个仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个Pull Request

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 联系方式

如果你有任何问题或建议，请通过以下方式联系：

- 提交GitHub Issue
- 发送邮件到项目维护者

---

**注意**: 这个项目专为XIAO ESP32-S3 Sense开发板设计，其他ESP32型号可能需要调整代码。 