import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

class ConfigManager:
    def __init__(self):
        self.config = {}
        self.load()

    def load(self):
        """从 config.json 加载配置"""
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = {}

    def save(self):
        """将当前配置保存回 config.json"""
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)

    def get(self, key, default=None):
        """获取配置项"""
        # 如果不存在该键，在返回默认值的同时写入字典
        if key not in self.config and default is not None:
            self.config[key] = default
            self.save()
        return self.config.get(key, default)

    def set(self, key, value):
        """设置配置项"""
        self.config[key] = value
        self.save()
