import paho.mqtt.client as mqtt
import json
import base64
import hashlib
import os
import time
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
import subprocess
import webbrowser

# MQTT配置
MQTT_BROKER = "emqx.cidatahub.com"
MQTT_PORT = 26701
MQTT_USERNAME = "nolan"
MQTT_PASSWORD = "opeioe"
MQTT_TOPIC = "esp32/camera"

# 接收配置
SAVE_DIR = "received_images"
TIMEOUT_SECONDS = 60

class ImageReceiverGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ESP32-S3 图片接收器")
        self.root.geometry("800x600")
        
        # 接收器实例
        self.receiver = None
        self.is_running = False
        
        # 创建界面
        self.create_widgets()
        
        # 启动状态更新线程
        self.update_thread = threading.Thread(target=self.update_status, daemon=True)
        self.update_thread.start()
    
    def create_widgets(self):
        """创建GUI组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # 连接状态
        ttk.Label(main_frame, text="连接状态:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.status_label = ttk.Label(main_frame, text="未连接", foreground="red")
        self.status_label.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # 控制按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="启动接收器", command=self.start_receiver)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="停止接收器", command=self.stop_receiver, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="打开图片文件夹", command=self.open_image_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="清空日志", command=self.clear_log).pack(side=tk.LEFT, padx=5)
        
        # 统计信息
        stats_frame = ttk.LabelFrame(main_frame, text="统计信息", padding="5")
        stats_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        stats_frame.columnconfigure(1, weight=1)
        stats_frame.columnconfigure(3, weight=1)
        
        ttk.Label(stats_frame, text="正在接收:").grid(row=0, column=0, sticky=tk.W)
        self.pending_label = ttk.Label(stats_frame, text="0")
        self.pending_label.grid(row=0, column=1, sticky=tk.W, padx=10)
        
        ttk.Label(stats_frame, text="已完成:").grid(row=0, column=2, sticky=tk.W)
        self.completed_label = ttk.Label(stats_frame, text="0")
        self.completed_label.grid(row=0, column=3, sticky=tk.W, padx=10)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="接收日志", padding="5")
        log_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 进度条
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
    
    def log_message(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        # 在主线程中更新GUI
        self.root.after(0, self._update_log, log_entry)
    
    def _update_log(self, message):
        """在主线程中更新日志"""
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)
        
        # 限制日志行数
        lines = self.log_text.get("1.0", tk.END).split('\n')
        if len(lines) > 1000:
            self.log_text.delete("1.0", f"{len(lines)-500}.0")
    
    def clear_log(self):
        """清空日志"""
        self.log_text.delete("1.0", tk.END)
    
    def start_receiver(self):
        """启动接收器"""
        if self.is_running:
            return
        
        try:
            self.receiver = ImageReceiver(self)
            self.receiver.start_background()
            
            self.is_running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_label.config(text="已连接", foreground="green")
            self.progress.start()
            
            self.log_message("🚀 接收器启动成功")
            
        except Exception as e:
            messagebox.showerror("错误", f"启动接收器失败: {e}")
            self.log_message(f"❌ 启动失败: {e}")
    
    def stop_receiver(self):
        """停止接收器"""
        if not self.is_running:
            return
        
        try:
            if self.receiver:
                self.receiver.stop()
            
            self.is_running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.status_label.config(text="未连接", foreground="red")
            self.progress.stop()
            
            self.log_message("🛑 接收器已停止")
            
        except Exception as e:
            messagebox.showerror("错误", f"停止接收器失败: {e}")
    
    def open_image_folder(self):
        """打开图片文件夹"""
        if not os.path.exists(SAVE_DIR):
            os.makedirs(SAVE_DIR)
        
        try:
            if os.name == 'nt':  # Windows
                subprocess.run(['explorer', SAVE_DIR])
            else:  # Linux/Mac
                subprocess.run(['xdg-open', SAVE_DIR])
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件夹: {e}")
    
    def update_status(self):
        """更新状态信息"""
        while True:
            if self.is_running and self.receiver:
                try:
                    status = self.receiver.get_status()
                    
                    # 在主线程中更新GUI
                    self.root.after(0, self._update_status_labels, status)
                except:
                    pass
            
            time.sleep(1)
    
    def _update_status_labels(self, status):
        """在主线程中更新状态标签"""
        self.pending_label.config(text=str(status['pending_count']))
        self.completed_label.config(text=str(status['completed_count']))

class ImageReceiver:
    def __init__(self, gui):
        self.gui = gui
        self.client = mqtt.Client()
        self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        # 图片接收状态
        self.pending_images = {}
        self.completed_images = {}
        self.lock = threading.Lock()
        
        # 创建保存目录
        if not os.path.exists(SAVE_DIR):
            os.makedirs(SAVE_DIR)
        
        # 控制标志
        self.running = False
        self.cleanup_thread = None
    
    def on_connect(self, client, userdata, flags, rc):
        """MQTT连接回调"""
        if rc == 0:
            self.gui.log_message("✅ 成功连接到MQTT服务器!")
            client.subscribe(f"{MQTT_TOPIC}/header")
            client.subscribe(f"{MQTT_TOPIC}/chunk")
            client.subscribe(f"{MQTT_TOPIC}/completion")
            self.gui.log_message(f"已订阅主题: {MQTT_TOPIC}/header, {MQTT_TOPIC}/chunk, {MQTT_TOPIC}/completion")
        else:
            self.gui.log_message(f"❌ MQTT连接失败，错误代码: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        """MQTT断开连接回调"""
        if rc != 0:
            self.gui.log_message(f"⚠️ MQTT连接意外断开，错误代码: {rc}")
        else:
            self.gui.log_message("MQTT连接已断开")
    
    def on_message(self, client, userdata, msg):
        """MQTT消息接收回调"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            data = json.loads(payload)
            
            self.gui.log_message(f"📨 收到消息: {topic}")
            
            if topic.endswith("/header"):
                self.handle_header(data)
            elif topic.endswith("/chunk"):
                self.handle_chunk(data)
            elif topic.endswith("/completion"):
                self.handle_completion(data)
                
        except Exception as e:
            self.gui.log_message(f"❌ 处理消息时出错: {e}")
    
    def handle_header(self, data):
        """处理图片信息头"""
        with self.lock:
            image_id = f"{data['device_id']}_{data['timestamp']}"
            
            if image_id in self.pending_images:
                self.gui.log_message(f"⚠️ 图片 {image_id} 已存在，跳过重复的头信息")
                return
            
            self.pending_images[image_id] = {
                'header': data,
                'chunks': {},
                'received_chunks': 0,
                'total_chunks': data['total_chunks'],
                'start_time': time.time(),
                'image_md5': data['image_md5'],
                'device_id': data['device_id']
            }
            
            self.gui.log_message(f"📸 开始接收图片: {image_id}")
            self.gui.log_message(f"   总分块数: {data['total_chunks']}")
            self.gui.log_message(f"   图片大小: {data['image_size']} 字节")
    
    def handle_chunk(self, data):
        """处理图片数据块"""
        with self.lock:
            image_id = None
            for img_id, img_data in self.pending_images.items():
                if img_data['device_id'] == data.get('device_id', ''):
                    image_id = img_id
                    break
            
            if image_id is None:
                self.gui.log_message(f"⚠️ 未找到对应的图片头信息，跳过块 {data['chunk_index']}")
                return
            
            img_data = self.pending_images[image_id]
            chunk_index = data['chunk_index']
            
            if chunk_index in img_data['chunks']:
                self.gui.log_message(f"⚠️ 块 {chunk_index} 已接收，跳过重复")
                return
            
            chunk_data = data['chunk_data']
            chunk_md5 = hashlib.md5(chunk_data.encode('utf-8')).hexdigest()
            
            if chunk_md5 != data['chunk_md5']:
                self.gui.log_message(f"❌ 块 {chunk_index} MD5校验失败")
                return
            
            img_data['chunks'][chunk_index] = chunk_data
            img_data['received_chunks'] += 1
            
            self.gui.log_message(f"✅ 接收块 {chunk_index + 1}/{img_data['total_chunks']}")
            
            if img_data['received_chunks'] == img_data['total_chunks']:
                self.gui.log_message(f"🎉 图片 {image_id} 所有块接收完成!")
                self.assemble_image(image_id)
    
    def handle_completion(self, data):
        """处理完成信号"""
        with self.lock:
            image_id = None
            for img_id, img_data in self.pending_images.items():
                if img_data['device_id'] == data.get('device_id', ''):
                    image_id = img_id
                    break
            
            if image_id is None:
                self.gui.log_message(f"⚠️ 未找到对应的图片，跳过完成信号")
                return
            
            img_data = self.pending_images[image_id]
            
            if img_data['received_chunks'] == img_data['total_chunks']:
                self.gui.log_message(f"✅ 收到完成信号，图片 {image_id} 传输完成")
                self.assemble_image(image_id)
            else:
                self.gui.log_message(f"⚠️ 收到完成信号，但图片 {image_id} 还有 {img_data['total_chunks'] - img_data['received_chunks']} 个块未接收")
    
    def assemble_image(self, image_id):
        """组装图片"""
        try:
            img_data = self.pending_images[image_id]
            
            chunks = []
            for i in range(img_data['total_chunks']):
                if i not in img_data['chunks']:
                    self.gui.log_message(f"❌ 缺少块 {i}，无法组装图片")
                    return
                chunks.append(img_data['chunks'][i])
            
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
            
            image_md5 = hashlib.md5(image_binary).hexdigest()
            if image_md5 != img_data['image_md5']:
                self.gui.log_message(f"❌ 图片MD5校验失败")
                return
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{SAVE_DIR}/image_{image_id}_{timestamp}.jpg"
            
            with open(filename, 'wb') as f:
                f.write(image_binary)
            
            self.gui.log_message(f"💾 图片保存成功: {filename}")
            self.gui.log_message(f"   文件大小: {len(image_binary)} 字节")
            
            self.completed_images[image_id] = {
                'filename': filename,
                'size': len(image_binary),
                'md5': image_md5,
                'device_id': img_data['device_id'],
                'timestamp': img_data['header']['timestamp']
            }
            
            del self.pending_images[image_id]
            
        except Exception as e:
            self.gui.log_message(f"❌ 组装图片时出错: {e}")
    
    def cleanup_timeout_images(self):
        """清理超时的图片"""
        while self.running:
            time.sleep(10)
            
            with self.lock:
                current_time = time.time()
                timeout_images = []
                
                for image_id, img_data in self.pending_images.items():
                    if current_time - img_data['start_time'] > TIMEOUT_SECONDS:
                        timeout_images.append(image_id)
                
                for image_id in timeout_images:
                    self.gui.log_message(f"⏰ 图片 {image_id} 接收超时，已清理")
                    del self.pending_images[image_id]
    
    def start_background(self):
        """在后台启动接收器"""
        self.running = True
        
        # 启动清理线程
        self.cleanup_thread = threading.Thread(target=self.cleanup_timeout_images, daemon=True)
        self.cleanup_thread.start()
        
        # 启动MQTT客户端
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.client.loop_start()
    
    def stop(self):
        """停止接收器"""
        self.running = False
        
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
    
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
    root = tk.Tk()
    app = ImageReceiverGUI(root)
    
    # 设置窗口关闭事件
    def on_closing():
        if app.is_running:
            app.stop_receiver()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main() 