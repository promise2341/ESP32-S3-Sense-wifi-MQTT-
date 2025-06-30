# WiFi配置
WIFI_SSID = "Bosstown7"
WIFI_PASSWORD = "#1Bosttown"

# MQTT配置
MQTT_BROKER = "****.com"  # 你的mqtt服务器地址
MQTT_PORT = 26701
MQTT_CLIENT_ID = "wifitest"  # 登录客户端ID
MQTT_USERNAME = "***"   # 你的mqtt账号
MQTT_PASSWORD = "****"  # 账号所对应的密码
MQTT_TOPIC = "esp32/camera"  # 订阅的topic

# 相机配置
CAMERA_JPEG_QUALITY = 90  # 质量可自己调试
CAMERA_FRAME_SIZE = "HD"  # 可选: VGA, SVGA, XGA, HD, SXGA, UXGA
CAMERA_FB_COUNT = 2

# 程序配置
PHOTO_INTERVAL = 30  # 拍照间隔（秒） 
