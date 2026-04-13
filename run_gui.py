import tkinter as tk
from tkinter import ttk, messagebox
import keyboard
import threading
import sys
import os
import ctypes
import time
import mss
import mss.tools
import pystray
from PIL import Image, ImageDraw

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join([f'"{arg}"' for arg in sys.argv]), None, 1)
    sys.exit()

from core.config import ConfigManager
from core.bot import AutoBot

class OverlayWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-transparentcolor", "black")
        self.config(bg="black")
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"50x50+{sw-80}+{sh-100}")
        self.canvas = tk.Canvas(self, width=50, height=50, bg="black", highlightthickness=0)
        self.canvas.pack()
        self.circle = self.canvas.create_oval(10, 10, 40, 40, fill="gray", outline="gray")
        self.withdraw()

    def update_state(self, state):
        if state == "running":
            self.deiconify()
            self.canvas.itemconfig(self.circle, fill="#00FF00", outline="#00FF00")
        elif state == "paused":
            self.deiconify()
            self.canvas.itemconfig(self.circle, fill="#FFC107", outline="#FFC107")
        else:
            self.withdraw()

class Snipper(tk.Toplevel):
    def __init__(self, master, on_capture):
        super().__init__(master)
        self.on_capture = on_capture
        self.attributes("-alpha", 0.3)
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.config(cursor="cross")
        self.canvas = tk.Canvas(self, cursor="cross", bg="black")
        self.canvas.pack(fill="both", expand=True)
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Escape>", lambda e: self.destroy())

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2, fill="white")

    def on_drag(self, event):
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        end_x, end_y = event.x, event.y
        self.destroy()
        x1, y1 = min(self.start_x :Iterable[SupportsRichComparisonT@min], end_x), min(self.start_y, end_y)
        x2, y2 = max(self.start_x, end_x), max(self.start_y, end_y)
        if x2 - x1 > 5 and y2 - y1 > 5:
            self.on_capture((x1, y1, x2, y2))

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("原神剧情自动点击器")
        self.geometry("380x430")
        self.resizable(False, False)
        
        # 配置与核心逻辑初始化
        self.config = ConfigManager()
        self.bot = AutoBot(update_callback=self.update_status_label)
        self.listening_entry = None
        self.overlay = OverlayWindow(self)
        
        self.create_widgets()
        self.setup_hotkeys()
        self.setup_tray()
        
    def bind_key_listener(self, entry_widget):
        # 绑定焦点事件，获取焦点时开始监听按键，失去焦点时停止
        entry_widget.bind("<FocusIn>", lambda e: self.start_listening(entry_widget))
        entry_widget.bind("<FocusOut>", lambda e: self.stop_listening())
        entry_widget.bind("<Key>", self.handle_key_event)
        # 禁止输入默认字符，由我们通过事件捕获接管
        entry_widget.config(state="readonly")

    def start_listening(self, entry_widget):
        self.listening_entry = entry_widget
        entry_widget.config(state="normal")
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, "请按键...")
        entry_widget.config(state="readonly")

    def stop_listening(self):
        self.listening_entry = None

    def handle_key_event(self, event):
        if self.listening_entry:
            key = event.keysym.lower()
            # 过滤一些不相关的按键并且做简单的映射转换使得 keyboard 库能识别
            ignored_keys = ["return", "tab", "shift_l", "shift_r", "control_l", "control_r", "alt_l", "alt_r", "caps_lock", "num_lock", "scroll_lock", "iso_level3_shift"]
            if key in ignored_keys:
                return "break"
                
            if key == "delete":
                key = "delete"
            elif key == "backspace":
                key = "backspace"
            elif key == "escape":
                key = "esc"
            elif key == "prior":
                key = "page up"
            elif key == "next":
                key = "page down"
            elif key == "space":
                key = "space"

            self.listening_entry.config(state="normal")
            self.listening_entry.delete(0, tk.END)
            self.listening_entry.insert(0, key)
            self.listening_entry.config(state="readonly")
            
            # 将焦点移开以表示录入完成
            self.focus()
            return "break"

    def create_widgets(self):
        # 整体框架
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)

        # 状态显示区
        self.status_var = tk.StringVar(value="状态: 停止")
        status_lbl = ttk.Label(main_frame, textvariable=self.status_var, font=("Microsoft YaHei", 16, "bold"), foreground="#d32f2f")
        status_lbl.pack(pady=10)

        # 设置区
        settings_frame = ttk.LabelFrame(main_frame, text="热键与设置", padding="10")
        settings_frame.pack(fill="x", pady=10)
        
        ttk.Label(settings_frame, text="启动/停止热键:").grid(row=0, column=0, sticky="w", pady=2)
        self.entry_start_hk = ttk.Entry(settings_frame, width=15)
        self.entry_start_hk.insert(0, self.config.get("start_hotkey", "delete"))
        self.bind_key_listener(self.entry_start_hk)
        self.entry_start_hk.grid(row=0, column=1, padx=5)

        ttk.Label(settings_frame, text="暂停/恢复热键:").grid(row=1, column=0, sticky="w", pady=2)
        self.entry_pause_hk = ttk.Entry(settings_frame, width=15)
        self.entry_pause_hk.insert(0, self.config.get("pause_hotkey", "f7"))
        self.bind_key_listener(self.entry_pause_hk)
        self.entry_pause_hk.grid(row=1, column=1, padx=5)

        ttk.Label(settings_frame, text="游戏操作键位:").grid(row=2, column=0, sticky="w", pady=2)
        self.entry_action_key = ttk.Entry(settings_frame, width=15)
        self.entry_action_key.insert(0, self.config.get("action_key", "space"))
        self.bind_key_listener(self.entry_action_key)
        self.entry_action_key.grid(row=2, column=1, padx=5)
        
        ttk.Label(settings_frame, text="截图找图热键:").grid(row=3, column=0, sticky="w", pady=2)
        self.entry_capture_hk = ttk.Entry(settings_frame, width=15)
        self.entry_capture_hk.insert(0, self.config.get("capture_hotkey", "f8"))
        self.bind_key_listener(self.entry_capture_hk)
        self.entry_capture_hk.grid(row=3, column=1, padx=5)

        btn_save = ttk.Button(settings_frame, text="保存设置", command=self.save_settings)
        btn_save.grid(row=4, column=0, columnspan=2, pady=10)

        # 按钮控制区
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=10)
        
        self.btn_toggle = ttk.Button(btn_frame, text="启动", command=self.toggle_bot)
        self.btn_toggle.pack(side="left", padx=5, expand=True, fill="x")
        
        self.btn_pause = ttk.Button(btn_frame, text="暂停", command=self.toggle_pause, state="disabled")
        self.btn_pause.pack(side="right", padx=5, expand=True, fill="x")

    def save_settings(self):
        start_hk = self.entry_start_hk.get().strip()
        pause_hk = self.entry_pause_hk.get().strip()
        action_key = self.entry_action_key.get().strip()
        capture_hk = self.entry_capture_hk.get().strip()
        
        if "请按键" in start_hk or "请按键" in pause_hk or "请按键" in action_key or "请按键" in capture_hk:
            messagebox.showwarning("警告", "请正确录入有效的配置项按键")
            return
        
        if not start_hk or not pause_hk or not action_key or not capture_hk:
            messagebox.showwarning("警告", "配置项不能为空")
            return
            
        self.config.set("start_hotkey", start_hk)
        self.config.set("pause_hotkey", pause_hk)
        self.config.set("action_key", action_key)
        self.config.set("capture_hotkey", capture_hk)
        
        # 重新绑定热键
        self.setup_hotkeys()
        messagebox.showinfo("成功", "设置已保存并生效！")

    def update_status_label(self, msg):
        # 跨线程更新 UI
        def _update():
            if msg == "已启动运行" or msg == "运行中":
                self.status_var.set(f"状态: {msg}")
                self.btn_toggle.config(text="停止")
                self.btn_pause.config(state="normal", text="暂停")
                self.overlay.update_state("running")
            elif msg == "已暂停":
                self.status_var.set(f"状态: {msg}")
                self.btn_pause.config(text="恢复")
                self.overlay.update_state("paused")
            elif msg.startswith("已停止"):
                self.status_var.set("状态: 停止")
                self.btn_toggle.config(text="启动")
                self.btn_pause.config(state="disabled", text="暂停")
                self.overlay.update_state("stopped")
            else:
                print(msg)
        self.after(0, _update)

    def setup_hotkeys(self):
        try:
            keyboard.unhook_all_hotkeys()
        except:
            pass

        try:
            start_hk = self.config.get("start_hotkey", "delete")
            pause_hk = self.config.get("pause_hotkey", "f7")
            capture_hk = self.config.get("capture_hotkey", "f8")
            
            # 注册全局热键
            keyboard.add_hotkey(start_hk, self.toggle_bot)
            keyboard.add_hotkey(pause_hk, self.toggle_pause)
            keyboard.add_hotkey(capture_hk, self.trigger_snip)
        except Exception as e:
            messagebox.showwarning("热键绑定失败", f"无法绑定全局热键。\n或者您设置的快捷键格式不正确。\n错误: {e}")

    def trigger_snip(self):
        self.after(0, self.start_snipping)

    def start_snipping(self):
        self.was_running = self.bot.running and not self.bot.paused
        if self.was_running:
            self.bot.pause()
        Snipper(self, self.capture_region)

    def capture_region(self, bbox):
        time.sleep(0.2)
        with mss.mss() as sct:
            monitor = {"top": bbox[1], "left": bbox[0], "width": bbox[2]-bbox[0], "height": bbox[3]-bbox[1]}
            sct_img = sct.grab(monitor)
            feature_dir = os.path.join(os.path.dirname(__file__), self.config.get("template_path", "features"))
            os.makedirs(feature_dir, exist_ok=True)
            filename = f"feature_{int(time.time()*1000)}.png"
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=os.path.join(feature_dir, filename))
            self.bot.load_templates()
            print(f"已保存特征图: {filename}")
            
        if getattr(self, 'was_running', False):
            self.bot.pause()

    def setup_tray(self):
        def create_image():
            image = Image.new('RGBA', (64, 64), (255, 255, 255, 0))
            dc = ImageDraw.Draw(image)
            dc.ellipse((8, 8, 56, 56), fill=(0, 200, 0))
            return image

        def on_show(icon, item):
            self.after(0, self.deiconify)

        def on_exit(icon, item):
            self.after(0, self.quit_app)

        menu = pystray.Menu(
            pystray.MenuItem("显示控制面板", on_show, default=True),
            pystray.MenuItem("完全退出", on_exit)
        )
        self.tray_icon = pystray.Icon("AutoClick", create_image(), "原神剧情自动点击器", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def toggle_bot(self):
        if self.bot.running:
            self.bot.stop()
            self.update_status_label("已停止")
        else:
            self.bot.start()

    def toggle_pause(self):
        if self.bot.running:
            self.bot.pause()

    def quit_app(self):
        self.bot.stop()
        if hasattr(self, 'tray_icon'):
            self.tray_icon.stop()
        self.destroy()
        os._exit(0)

    def on_closing(self):
        # 隐藏到系统托盘而不是退出
        self.withdraw()

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
