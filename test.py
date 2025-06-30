import network
import time
from umqtt.simple import MQTTClient
import json
import base64
from camera import Camera, GrabMode, PixelFormat, FrameSize, GainCeiling
from config import *

def test_wifi():
    """测试WiFi连接"""
    print("=== 测试WiFi连接 ===")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        print(f"正在连接到WiFi: {WIFI_SSID}")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        
        max_wait = 10
        while max_wait > 0:
            if wlan.isconnected():
                break
            max_wait -= 1
            print("等待WiFi连接...")
            time.sleep(1)
        
        if wlan.isconnected():
            print(f"✅ WiFi连接成功!")
            print(f"IP地址: {wlan.ifconfig()[0]}")
            return True
        else:
            print("❌ WiFi连接失败!")
            return False
    else:
        print(f"✅ WiFi已连接! IP: {wlan.ifconfig()[0]}")
        return True

def test_mqtt():
    """测试MQTT连接"""
    print("\n=== 测试MQTT连接 ===")
    try:
        client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, port=MQTT_PORT, 
                           user=MQTT_USERNAME, password=MQTT_PASSWORD)
        client.connect()
        print("✅ MQTT连接成功!")
        
        # 发送测试消息
        test_message = {
            "test": True,
            "timestamp": time.time(),
            "device_id": MQTT_CLIENT_ID
        }
        client.publish(MQTT_TOPIC, json.dumps(test_message))
        print("✅ 测试消息发送成功!")
        
        client.disconnect()
        return True
    except Exception as e:
        print(f"❌ MQTT连接失败: {e}")
        return False

def test_camera():
    """测试相机功能"""
    print("\n=== 测试相机功能 ===")
    try:
        cam = Camera(pixel_format=PixelFormat.JPEG,
                     frame_size=FrameSize.HD,
                     jpeg_quality=90,
                     fb_count=2,
                     grab_mode=GrabMode.LATEST)

        cam.init()
        print("✅ 相机初始化成功!")
        
        time.sleep(2)
        img = cam.capture()
        print(f"✅ 拍照成功! 图片大小: {len(img)} 字节")
        
        cam.deinit()
        print("✅ 相机资源释放成功!")
        return True
    except Exception as e:
        print(f"❌ 相机测试失败: {e}")
        return False

def test_full_pipeline():
    """测试完整流程"""
    print("\n=== 测试完整流程 ===")
    
    # 测试WiFi
    if not test_wifi():
        print("❌ WiFi测试失败，跳过后续测试")
        return False
    
    # 测试MQTT
    if not test_mqtt():
        print("❌ MQTT测试失败，跳过后续测试")
        return False
    
    # 测试相机
    if not test_camera():
        print("❌ 相机测试失败")
        return False
    
    print("\n✅ 所有测试通过!")
    return True

def main():
    """主测试函数"""
    print("ESP32-S3 Sense 功能测试程序")
    print("=" * 40)
    
    # 显示配置信息
    print(f"WiFi SSID: {WIFI_SSID}")
    print(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"MQTT Client ID: {MQTT_CLIENT_ID}")
    print(f"MQTT Topic: {MQTT_TOPIC}")
    print("=" * 40)
    
    # 运行测试
    success = test_full_pipeline()
    
    if success:
        print("\n🎉 所有功能测试通过，可以运行主程序!")
    else:
        print("\n⚠️  部分功能测试失败，请检查配置和连接")

if __name__ == "__main__":
    main() 