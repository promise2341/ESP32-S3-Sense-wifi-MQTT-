import paho.mqtt.client as mqtt
import json
import base64
import hashlib
import os
import time
from datetime import datetime
from collections import defaultdict
import threading
import queue

# MQTT配置
MQTT_BROKER = "emqx.cidatahub.com"
MQTT_PORT = 26701
MQTT_USERNAME = "nolan"
MQTT_PASSWORD = "opeioe"
MQTT_TOPIC = "esp32/camera"

# 接收配置
SAVE_DIR = "received_images"
TIMEOUT_SECONDS = 60  # 图片接收超时时间

class ImageReceiver:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        # 图片接收状态
        self.pending_images = {}  # 存储正在接收的图片
        self.completed_images = {}  # 存储已完成的图片
        self.lock = threading.Lock()
        
        # 创建保存目录
        if not os.path.exists(SAVE_DIR):
            os.makedirs(SAVE_DIR)
        
        # 启动清理线程
        self.cleanup_thread = threading.Thread(target=self.cleanup_timeout_images, daemon=True)
        self.cleanup_thread.start()
    
    def on_connect(self, client, userdata, flags, rc):
        """MQTT连接回调"""
        if rc == 0:
            print("✅ 成功连接到MQTT服务器!")
            # 订阅相关主题
            client.subscribe(f"{MQTT_TOPIC}/header")
            client.subscribe(f"{MQTT_TOPIC}/chunk")
            client.subscribe(f"{MQTT_TOPIC}/completion")
            print(f"已订阅主题: {MQTT_TOPIC}/header, {MQTT_TOPIC}/chunk, {MQTT_TOPIC}/completion")
        else:
            print(f"❌ MQTT连接失败，错误代码: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        """MQTT断开连接回调"""
        if rc != 0:
            print(f"⚠️ MQTT连接意外断开，错误代码: {rc}")
        else:
            print("MQTT连接已断开")
    
    def on_message(self, client, userdata, msg):
        """MQTT消息接收回调"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            data = json.loads(payload)
            
            print(f"📨 收到消息: {topic}")
            
            if topic.endswith("/header"):
                self.handle_header(data)
            elif topic.endswith("/chunk"):
                self.handle_chunk(data)
            elif topic.endswith("/completion"):
                self.handle_completion(data)
                
        except Exception as e:
            print(f"❌ 处理消息时出错: {e}")
    
    def handle_header(self, data):
        """处理图片信息头"""
        with self.lock:
            image_id = f"{data['device_id']}_{data['timestamp']}"
            
            # 检查是否已存在
            if image_id in self.pending_images:
                print(f"⚠️ 图片 {image_id} 已存在，跳过重复的头信息")
                return
            
            # 创建新的图片接收任务
            self.pending_images[image_id] = {
                'header': data,
                'chunks': {},
                'received_chunks': 0,
                'total_chunks': data['total_chunks'],
                'start_time': time.time(),
                'image_md5': data['image_md5'],
                'device_id': data['device_id']
            }
            
            print(f"📸 开始接收图片: {image_id}")
            print(f"   总分块数: {data['total_chunks']}")
            print(f"   图片大小: {data['image_size']} 字节")
            print(f"   图片MD5: {data['image_md5']}")
    
    def handle_chunk(self, data):
        """处理图片数据块"""
        with self.lock:
            # 查找对应的图片
            image_id = None
            for img_id, img_data in self.pending_images.items():
                if img_data['device_id'] == data.get('device_id', ''):
                    image_id = img_id
                    break
            
            if image_id is None:
                print(f"⚠️ 未找到对应的图片头信息，跳过块 {data['chunk_index']}")
                return
            
            img_data = self.pending_images[image_id]
            chunk_index = data['chunk_index']
            
            # 检查块是否已接收
            if chunk_index in img_data['chunks']:
                print(f"⚠️ 块 {chunk_index} 已接收，跳过重复")
                return
            
            # 验证块的MD5
            chunk_data = data['chunk_data']
            chunk_md5 = hashlib.md5(chunk_data.encode('utf-8')).hexdigest()
            
            if chunk_md5 != data['chunk_md5']:
                print(f"❌ 块 {chunk_index} MD5校验失败")
                return
            
            # 保存块数据
            img_data['chunks'][chunk_index] = chunk_data
            img_data['received_chunks'] += 1
            
            print(f"✅ 接收块 {chunk_index + 1}/{img_data['total_chunks']} (MD5: {chunk_md5[:8]}...)")
            
            # 检查是否接收完成
            if img_data['received_chunks'] == img_data['total_chunks']:
                print(f"🎉 图片 {image_id} 所有块接收完成!")
                self.assemble_image(image_id)
    
    def handle_completion(self, data):
        """处理完成信号"""
        with self.lock:
            # 查找对应的图片
            image_id = None
            for img_id, img_data in self.pending_images.items():
                if img_data['device_id'] == data.get('device_id', ''):
                    image_id = img_id
                    break
            
            if image_id is None:
                print(f"⚠️ 未找到对应的图片，跳过完成信号")
                return
            
            img_data = self.pending_images[image_id]
            
            # 检查是否所有块都已接收
            if img_data['received_chunks'] == img_data['total_chunks']:
                print(f"✅ 收到完成信号，图片 {image_id} 传输完成")
                self.assemble_image(image_id)
            else:
                print(f"⚠️ 收到完成信号，但图片 {image_id} 还有 {img_data['total_chunks'] - img_data['received_chunks']} 个块未接收")
    
    def assemble_image(self, image_id):
        """组装图片"""
        try:
            img_data = self.pending_images[image_id]
            
            # 按顺序拼接所有块
            chunks = []
            for i in range(img_data['total_chunks']):
                if i not in img_data['chunks']:
                    print(f"❌ 缺少块 {i}，无法组装图片")
                    return
                chunks.append(img_data['chunks'][i])
            
            # 拼接Base64数据
            image_base64 = ''.join(chunks)
            
            # 解码为二进制数据 - 处理ubinascii编码的数据
            try:
                # 首先尝试标准base64解码
                image_binary = base64.b64decode(image_base64)
            except Exception:
                # 如果失败，尝试添加padding
                padding = 4 - (len(image_base64) % 4)
                if padding != 4:
                    image_base64 += '=' * padding
                image_binary = base64.b64decode(image_base64)
            
            # 验证图片MD5
            image_md5 = hashlib.md5(image_binary).hexdigest()
            if image_md5 != img_data['image_md5']:
                print(f"❌ 图片MD5校验失败，期望: {img_data['image_md5']}, 实际: {image_md5}")
                return
            
            # 保存图片
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{SAVE_DIR}/image_{image_id}_{timestamp}.jpg"
            
            with open(filename, 'wb') as f:
                f.write(image_binary)
            
            print(f"💾 图片保存成功: {filename}")
            print(f"   文件大小: {len(image_binary)} 字节")
            print(f"   MD5校验: {image_md5}")
            
            # 移动到已完成列表
            self.completed_images[image_id] = {
                'filename': filename,
                'size': len(image_binary),
                'md5': image_md5,
                'device_id': img_data['device_id'],
                'timestamp': img_data['header']['timestamp']
            }
            
            # 从待处理列表中移除
            del self.pending_images[image_id]
            
        except Exception as e:
            print(f"❌ 组装图片时出错: {e}")
    
    def cleanup_timeout_images(self):
        """清理超时的图片"""
        while True:
            time.sleep(10)  # 每10秒检查一次
            
            with self.lock:
                current_time = time.time()
                timeout_images = []
                
                for image_id, img_data in self.pending_images.items():
                    if current_time - img_data['start_time'] > TIMEOUT_SECONDS:
                        timeout_images.append(image_id)
                
                for image_id in timeout_images:
                    print(f"⏰ 图片 {image_id} 接收超时，已清理")
                    del self.pending_images[image_id]
    
    def start(self):
        """启动接收器"""
        try:
            print("🚀 启动图片接收器...")
            print(f"MQTT服务器: {MQTT_BROKER}:{MQTT_PORT}")
            print(f"保存目录: {SAVE_DIR}")
            print(f"超时时间: {TIMEOUT_SECONDS} 秒")
            print("=" * 50)
            
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_forever()
            
        except KeyboardInterrupt:
            print("\n🛑 用户中断，正在关闭...")
        except Exception as e:
            print(f"❌ 启动失败: {e}")
        finally:
            self.client.disconnect()
            print("接收器已关闭")
    
    def get_status(self):
        """获取当前状态"""
        with self.lock:
            return {
                'pending_count': len(self.pending_images),
                'completed_count': len(self.completed_images),
                'pending_images': list(self.pending_images.keys()),
                'completed_images': list(self.completed_images.keys())
            }

def main():
    """主函数"""
    receiver = ImageReceiver()
    receiver.start()

if __name__ == "__main__":
    main() 