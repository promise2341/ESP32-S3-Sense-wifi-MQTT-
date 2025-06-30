import network
import time
from umqtt.simple import MQTTClient
import json
import ubinascii
import hashlib
import gc
from camera import Camera, GrabMode, PixelFormat, FrameSize, GainCeiling
from config import *

# 分块传输配置
CHUNK_SIZE = 3072  # 3KB
MAX_CHUNKS_PER_MESSAGE = 1  # 每个MQTT消息只包含一个块

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

def calculate_md5(data):
    """计算MD5校验和"""
    # 在MicroPython中，使用ubinascii.hexlify()来获取十六进制字符串
    md5_hash = hashlib.md5(data).digest()
    return ubinascii.hexlify(md5_hash).decode('utf-8')

def send_image_chunks_via_mqtt(client, image_data):
    """分块发送图片数据"""
    try:
        # 计算图片的MD5校验和
        image_md5 = calculate_md5(image_data)
        
        # 使用ubinascii进行base64编码
        image_base64 = ubinascii.b2a_base64(image_data).decode('utf-8').rstrip('\n')
        
        # 计算分块数量
        total_chunks = (len(image_base64) + CHUNK_SIZE - 1) // CHUNK_SIZE
        
        print(f"图片大小: {len(image_data)} 字节")
        print(f"Base64大小: {len(image_base64)} 字符")
        print(f"总分块数: {total_chunks}")
        print(f"每块大小: {CHUNK_SIZE} 字符")
        
        # 发送图片信息头
        header_message = {
            "type": "header",
            "timestamp": time.time(),
            "device_id": MQTT_CLIENT_ID,
            "image_md5": image_md5,
            "total_chunks": total_chunks,
            "chunk_size": CHUNK_SIZE,
            "image_size": len(image_data)
        }
        
        client.publish(f"{MQTT_TOPIC}/header", json.dumps(header_message))
        print("✅ 图片信息头发送成功!")
        
        # 分块发送图片数据
        for chunk_index in range(total_chunks):
            start_pos = chunk_index * CHUNK_SIZE
            end_pos = min(start_pos + CHUNK_SIZE, len(image_base64))
            chunk_data = image_base64[start_pos:end_pos]
            
            # 计算当前块的MD5
            chunk_md5 = calculate_md5(chunk_data.encode('utf-8'))
            
            chunk_message = {
                "type": "chunk",
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
                "chunk_data": chunk_data,
                "chunk_md5": chunk_md5,
                "device_id": MQTT_CLIENT_ID,
                "is_last": (chunk_index == total_chunks - 1)
            }
            
            client.publish(f"{MQTT_TOPIC}/chunk", json.dumps(chunk_message))
            print(f"✅ 块 {chunk_index + 1}/{total_chunks} 发送成功")
            
            # 短暂延迟，避免发送过快
            time.sleep(0.1)
            
            # 垃圾回收，释放内存
            gc.collect()
        
        # 发送完成信号
        completion_message = {
            "type": "completion",
            "timestamp": time.time(),
            "device_id": MQTT_CLIENT_ID,
            "image_md5": image_md5,
            "total_chunks": total_chunks
        }
        
        client.publish(f"{MQTT_TOPIC}/completion", json.dumps(completion_message))
        print("✅ 图片传输完成信号发送成功!")
        
        return True
        
    except Exception as e:
        print(f"❌ 发送图片失败: {e}")
        return False

def main():
    """主函数"""
    print("ESP32-S3 Sense 分块传输相机MQTT程序启动")
    
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
            
            # 分块发送图片
            if send_image_chunks_via_mqtt(mqtt_client, image_data):
                print("图片已成功分块发送到MQTT服务器")
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