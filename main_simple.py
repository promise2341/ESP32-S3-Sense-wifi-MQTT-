import network
import time
from umqtt.simple import MQTTClient
import json
import base64
from camera import Camera, GrabMode, PixelFormat, FrameSize, GainCeiling
from config import *

def connect_wifi():
    """连接WiFi"""
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
            print(f"WiFi连接成功! IP: {wlan.ifconfig()[0]}")
            return True
        else:
            print("WiFi连接失败!")
            return False
    
    return True

def connect_mqtt():
    """连接MQTT服务器"""
    try:
        client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, port=MQTT_PORT, 
                           user=MQTT_USERNAME, password=MQTT_PASSWORD)
        client.connect()
        print("MQTT连接成功!")
        return client
    except Exception as e:
        print(f"MQTT连接失败: {e}")
        return None

def camera_img():
    """拍照功能"""
    # 根据配置选择帧大小
    frame_size_map = {
        "VGA": FrameSize.VGA,
        "SVGA": FrameSize.SVGA,
        "XGA": FrameSize.XGA,
        "HD": FrameSize.HD,
        "SXGA": FrameSize.SXGA,
        "UXGA": FrameSize.UXGA
    }
    
    cam = Camera(pixel_format=PixelFormat.JPEG,
                 frame_size=frame_size_map.get(CAMERA_FRAME_SIZE, FrameSize.HD),
                 jpeg_quality=CAMERA_JPEG_QUALITY,
                 fb_count=CAMERA_FB_COUNT,
                 grab_mode=GrabMode.LATEST)

    cam.init()
    time.sleep(2)
    img = cam.capture()
    cam.deinit()
    return bytes(img)

def send_image_via_mqtt(client, image_data):
    """通过MQTT发送图片"""
    try:
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        message = {
            "timestamp": time.time(),
            "image": image_base64,
            "device_id": MQTT_CLIENT_ID,
            "image_size": len(image_data)
        }
        
        client.publish(MQTT_TOPIC, json.dumps(message))
        print("图片发送成功!")
        return True
    except Exception as e:
        print(f"发送图片失败: {e}")
        return False

def main():
    """主函数"""
    print("ESP32-S3 Sense 相机MQTT程序启动")
    
    # 连接WiFi
    if not connect_wifi():
        return
    
    # 连接MQTT
    mqtt_client = connect_mqtt()
    if mqtt_client is None:
        return
    
    try:
        while True:
            print(f"\n开始拍照... (间隔: {PHOTO_INTERVAL}秒)")
            
            # 拍照
            image_data = camera_img()
            print(f"拍照完成，图片大小: {len(image_data)} 字节")
            
            # 发送图片
            if send_image_via_mqtt(mqtt_client, image_data):
                print("图片已成功发送到MQTT服务器")
            else:
                print("图片发送失败")
            
            print(f"等待 {PHOTO_INTERVAL} 秒后再次拍照...")
            time.sleep(PHOTO_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序运行出错: {e}")
    finally:
        try:
            mqtt_client.disconnect()
            print("MQTT连接已断开")
        except:
            pass

if __name__ == "__main__":
    main() 