import os
import time
import threading
import random
import cv2
import numpy as np
import mss
import pydirectinput
import win32gui

from .config import ConfigManager

# pydirectinput 安全设置，否则可能会发生鼠标失控
pydirectinput.FAILSAFE = False

class AutoBot:
    def __init__(self, update_callback=None):
        self.config = ConfigManager()
        self.running = False
        self.paused = False
        self.thread = None
        self.templates = []
        self.update_callback = update_callback  # 用于通知 GUI 更新状态
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.load_templates()

    def update_status(self, msg):
        """向 GUI 发送状态更新"""
        if self.update_callback:
            self.update_callback(msg)
        else:
            print(f"[Bot] {msg}")

    def load_templates(self):
        """加载特征图"""
        template_dir = self.config.get("template_path", "features")
        full_path = os.path.join(self.base_dir, template_dir)
        self.templates.clear()
        
        if not os.path.exists(full_path):
            self.update_status(f"特征文件夹 {template_dir} 不存在！")
            return
            
        for file in os.listdir(full_path):
            if file.endswith(".png") or file.endswith(".jpg"):
                filepath = os.path.join(full_path, file)
                # 使用灰度模式读取以加速匹配
                img = cv2.imdecode(np.fromfile(filepath, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    self.templates.append(img)
        
        self.update_status(f"成功加载 {len(self.templates)} 张特征图")

    def _get_game_window(self):
        """获取目标游戏窗口的坐标区域"""
        title = self.config.get("target_window_title", "原神")
        if not title:
            return None
            
        # 尝试查找窗口
        hwnd = win32gui.FindWindow(None, title)
        if not hwnd:
            return None
            
        # 获取窗口客户区大小（去除边框）
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        # 将客户区坐标转换为屏幕坐标
        lt = win32gui.ClientToScreen(hwnd, (left, top))
        rb = win32gui.ClientToScreen(hwnd, (right, bottom))
        
        return {
            "top": lt[1],
            "left": lt[0],
            "width": rb[0] - lt[0],
            "height": rb[1] - lt[1]
        }

    def start(self):
        """启动自动循环"""
        if self.running:
            return
            
        # 每次启动时重新加载最新配置和图片
        self.config.load()
        self.load_templates()
        if not self.templates:
            self.update_status("没有找到特征图，无法启动")
            return

        self.running = True
        self.paused = False
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self.update_status("已启动运行")

    def stop(self):
        """停止自动循环"""
        self.running = False
        self.paused = False
        if self.thread:
            self.thread = None
        self.update_status("已停止")

    def pause(self):
        """切换暂停状态"""
        if not self.running:
            return
        self.paused = not self.paused
        state = "已暂停" if self.paused else "运行中"
        self.update_status(state)

    def _run_loop(self):
        """核心找图点击循环"""
        with mss.mss() as sct:
            while self.running:
                # 读取配置参数
                action_key = self.config.get("action_key", "space")
                match_threshold = self.config.get("match_threshold", 0.85)
                poll_interval = self.config.get("poll_interval_ms", 120) / 1000.0
                min_delay = self.config.get("min_delay", 0.03)
                max_delay = self.config.get("max_delay", 0.1)
    
                if self.paused:
                    time.sleep(0.5)
                    continue
    
                try:
                    # 获取区域：如果有指定原神窗口，则截取该窗口；否则全屏截取第一显示器
                    monitor = self._get_game_window()
                    if not monitor:
                        monitor = sct.monitors[1]
                    
                    # 截图
                    sct_img = sct.grab(monitor)
                    # 转换 OpenCV 格式并转为灰度图
                    img = np.array(sct_img)
                    gray_img = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
                
                    matched = False
                    # 遍历特征库匹配
                    for template in self.templates:
                        res = cv2.matchTemplate(gray_img, template, cv2.TM_CCOEFF_NORMED)
                        loc = np.where(res >= match_threshold)
                        if len(loc[0]) > 0:
                            matched = True
                            break
                            
                    # 如果匹配成功，则执行点击
                    if matched:
                        # 模拟随机延迟防封
                        delay = random.uniform(min_delay, max_delay)
                        time.sleep(delay)
                        # pydirectinput 发送 DirectX 按键给游戏层
                        pydirectinput.press(action_key)
                        
                except Exception as e:
                    print(f"[Bot Error] {e}")
                    
                # 循环轮询间隔
                time.sleep(poll_interval)
