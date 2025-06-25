"""
文件自动分类器

功能: 自动把文件分类到对应的文件夹下
版本: 1.0.1
作者: xuyou & xiaomizha
"""
import os
import sys
import json
import yaml
import shutil
import webbrowser
import uuid
from datetime import datetime
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QPushButton, QLabel, QLineEdit, QTextEdit,
                             QFileDialog, QMessageBox, QProgressBar, QGroupBox,
                             QCheckBox, QScrollArea, QMenuBar, QAction,
                             QFrame, QSplitter, QTabWidget, QSpinBox, QComboBox,
                             QDialog, QDialogButtonBox, QGridLayout, QFormLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QCursor


class SettingsManager:
    """设置管理器"""

    def __init__(self):
        self.settings = QSettings("FileClassifier", "Settings")
        self._load_default_settings()

    def _load_default_settings(self):
        """加载默认设置"""
        self.default_settings = {
            # 常规设置
            'auto_save': True,
            'confirm_action': True,
            'log_level': '详细',

            # 界面设置
            'theme': '默认',
            'font_size': 10,

            # 分类设置
            'default_output_pattern': './{date}_{id}_分类',
            'move_files': True,
            'recursive': False,
            'preserve_structure': True,
            'remove_empty_folders': False,
            'exclude_output_dirs': True,

            # 高级设置
            'backup_rules': True,
            'max_log_lines': 1000,
        }

    def get(self, key, default=None):
        """获取设置值"""
        if default is None:
            default = self.default_settings.get(key)
        return self.settings.value(key, default)

    def set(self, key, value):
        """设置值"""
        self.settings.setValue(key, value)

    def get_bool(self, key):
        """获取布尔值设置"""
        return self.settings.value(key, self.default_settings.get(key, False), type=bool)

    def get_int(self, key):
        """获取整数值设置"""
        return self.settings.value(key, self.default_settings.get(key, 0), type=int)

    def reset_to_defaults(self):
        """重置为默认设置"""
        self.settings.clear()
        for key, value in self.default_settings.items():
            self.settings.setValue(key, value)


class QCollapsibleGroupBox(QGroupBox):
    """可折叠的GroupBox"""
    # 分类名, 是否启用
    rule_toggled = pyqtSignal(str, bool)

    def __init__(self, title="", parent=None, category_name=""):
        super().__init__(title, parent)
        self.setCheckable(True)
        self.setChecked(True)
        # 存储分类名称
        self.category_name = category_name
        self.toggled.connect(self.on_toggled)

    def on_toggled(self, checked):
        """切换折叠状态"""
        for child in self.findChildren(QWidget):
            if child != self:
                child.setVisible(checked)

        if self.category_name:
            self.rule_toggled.emit(self.category_name, checked)


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setWindowTitle("设置")
        self.setFixedSize(600, 500)
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout(self)
        tab_widget = QTabWidget()

        # 常规设置
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        self.auto_save_cb = QCheckBox("自动保存分类规则")
        general_layout.addRow("数据持久化:", self.auto_save_cb)
        self.confirm_action_cb = QCheckBox("执行操作前确认")
        general_layout.addRow("安全设置:", self.confirm_action_cb)
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["简洁", "详细", "调试"])
        general_layout.addRow("日志级别:", self.log_level_combo)
        self.exclude_output_cb = QCheckBox("排除输出目录, 防止重复分类")
        general_layout.addRow("智能排除:", self.exclude_output_cb)
        tab_widget.addTab(general_tab, "常规")

        # 分类设置
        classify_tab = QWidget()
        classify_layout = QFormLayout(classify_tab)
        self.output_pattern_input = QLineEdit()
        self.output_pattern_input.setPlaceholderText("./{date}_{id}_分类")
        classify_layout.addRow("输出路径模式:", self.output_pattern_input)
        self.preserve_structure_cb = QCheckBox("保持原有子目录结构")
        classify_layout.addRow("目录结构:", self.preserve_structure_cb)
        self.remove_empty_folders_cb = QCheckBox("分类后删除空文件夹")
        classify_layout.addRow("清理选项:", self.remove_empty_folders_cb)
        tab_widget.addTab(classify_tab, "分类")

        # 界面设置
        ui_tab = QWidget()
        ui_layout = QFormLayout(ui_tab)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["默认", "深色", "浅色"])
        ui_layout.addRow("主题:", self.theme_combo)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        ui_layout.addRow("字体大小:", self.font_size_spin)
        self.max_log_lines_spin = QSpinBox()
        self.max_log_lines_spin.setRange(100, 10000)
        self.max_log_lines_spin.setSuffix(" 行")
        ui_layout.addRow("最大日志行数:", self.max_log_lines_spin)
        tab_widget.addTab(ui_tab, "界面")
        layout.addWidget(tab_widget)

        button_layout = QHBoxLayout()
        reset_btn = QPushButton("重置默认")
        reset_btn.clicked.connect(self.reset_defaults)
        button_layout.addWidget(reset_btn)
        button_layout.addStretch()
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        button_layout.addWidget(buttons)
        layout.addLayout(button_layout)

    def load_settings(self):
        """加载设置"""
        self.auto_save_cb.setChecked(self.settings_manager.get_bool('auto_save'))
        self.confirm_action_cb.setChecked(self.settings_manager.get_bool('confirm_action'))
        self.log_level_combo.setCurrentText(self.settings_manager.get('log_level'))
        self.exclude_output_cb.setChecked(self.settings_manager.get_bool('exclude_output_dirs'))

        self.output_pattern_input.setText(self.settings_manager.get('default_output_pattern'))
        self.preserve_structure_cb.setChecked(self.settings_manager.get_bool('preserve_structure'))
        self.remove_empty_folders_cb.setChecked(self.settings_manager.get_bool('remove_empty_folders'))

        self.theme_combo.setCurrentText(self.settings_manager.get('theme'))
        self.font_size_spin.setValue(self.settings_manager.get_int('font_size'))
        self.max_log_lines_spin.setValue(self.settings_manager.get_int('max_log_lines'))

    def reset_defaults(self):
        """重置为默认设置"""
        reply = QMessageBox.question(
            self, "确认重置",
            "确定要重置所有设置为默认值吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.settings_manager.reset_to_defaults()
            self.load_settings()
            QMessageBox.information(self, "重置完成", "所有设置已重置为默认值")

    def accept(self):
        """保存设置"""
        self.settings_manager.set('auto_save', self.auto_save_cb.isChecked())
        self.settings_manager.set('confirm_action', self.confirm_action_cb.isChecked())
        self.settings_manager.set('log_level', self.log_level_combo.currentText())
        self.settings_manager.set('exclude_output_dirs', self.exclude_output_cb.isChecked())

        self.settings_manager.set('default_output_pattern', self.output_pattern_input.text())
        self.settings_manager.set('preserve_structure', self.preserve_structure_cb.isChecked())
        self.settings_manager.set('remove_empty_folders', self.remove_empty_folders_cb.isChecked())

        self.settings_manager.set('theme', self.theme_combo.currentText())
        self.settings_manager.set('font_size', self.font_size_spin.value())
        self.settings_manager.set('max_log_lines', self.max_log_lines_spin.value())

        super().accept()


class AboutDialog(QDialog):
    """关于对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于")
        self.setFixedSize(600, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 头部区域
        header_layout = QHBoxLayout()

        # 程序图标
        icon_label = QLabel()
        icon_pixmap = QPixmap("icon.png").scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon_label.setPixmap(icon_pixmap)
        header_layout.addWidget(icon_label)

        # 程序信息
        info_layout = QVBoxLayout()
        title_label = QLabel("文件自动分类器")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        info_layout.addWidget(title_label)
        desc_label = QLabel("自动将文件按类型分类到对应文件夹的实用工具")
        info_layout.addWidget(desc_label)
        version_label = QLabel("版本: 1.0.1")
        info_layout.addWidget(version_label)
        features_label = QLabel("✓ YAML配置格式\n✓ 智能路径管理\n✓ 结构保持选项\n✓ 空文件夹清理")
        info_layout.addWidget(features_label)
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # 中部链接区域
        links_group = QGroupBox("相关链接")
        links_layout = QGridLayout(links_group)

        # 链接按钮组
        donate_btn = QPushButton("💰 捐赠")
        donate_btn.setCursor(QCursor(Qt.PointingHandCursor))
        donate_btn.clicked.connect(lambda: webbrowser.open("https://github.com/xuyouer/"))
        links_layout.addWidget(donate_btn, 0, 0)
        contact_btn = QPushButton("📧 联系")
        contact_btn.setCursor(QCursor(Qt.PointingHandCursor))
        contact_btn.clicked.connect(lambda: webbrowser.open("https://github.com/xuyouer/"))
        links_layout.addWidget(contact_btn, 0, 1)
        homepage_btn = QPushButton("🏠 首页")
        homepage_btn.setCursor(QCursor(Qt.PointingHandCursor))
        homepage_btn.clicked.connect(lambda: webbrowser.open("https://github.com/xuyouer/"))
        links_layout.addWidget(homepage_btn, 1, 0)
        repo_btn = QPushButton("📦 开源仓库")
        repo_btn.setCursor(QCursor(Qt.PointingHandCursor))
        repo_btn.clicked.connect(lambda: webbrowser.open("https://github.com/xuyouer/xuyou-file-classifier"))
        links_layout.addWidget(repo_btn, 1, 1)
        author_layout = QHBoxLayout()
        author_label = QLabel("👥 作者: ")
        author_layout.addWidget(author_label)
        xuyou_btn = QPushButton("xuyou")
        xuyou_btn.setStyleSheet("QPushButton { border: none; color: blue; text-decoration: underline; }")
        xuyou_btn.setCursor(QCursor(Qt.PointingHandCursor))
        xuyou_btn.clicked.connect(lambda: webbrowser.open("https://github.com/xuyouer/"))
        author_layout.addWidget(xuyou_btn)
        and_label = QLabel("&")
        author_layout.addWidget(and_label)
        xiaomizha_btn = QPushButton("xiaomizha")
        xiaomizha_btn.setStyleSheet("QPushButton { border: none; color: blue; text-decoration: underline; }")
        xiaomizha_btn.setCursor(QCursor(Qt.PointingHandCursor))
        xiaomizha_btn.clicked.connect(lambda: webbrowser.open("https://github.com/xuyouer/"))
        author_layout.addWidget(xiaomizha_btn)
        author_layout.addStretch()
        author_widget = QWidget()
        author_widget.setLayout(author_layout)
        links_layout.addWidget(author_widget, 2, 0, 1, 2)
        layout.addWidget(links_group)

        # 底部版权信息
        current_year = datetime.now().year
        copyright_label = QLabel(f"Copyright © 2020-{current_year} xuyou, xiaomizha., Ltd.\nAll rights reserved.")
        copyright_label.setAlignment(Qt.AlignCenter)
        copyright_label.setStyleSheet("color: gray; font-weight: bold; font-size: 20px;")
        layout.addWidget(copyright_label)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("QPushButton { padding: 8px; }")
        layout.addWidget(close_btn)


class RuleEditDialog(QDialog):
    """规则编辑对话框"""

    def __init__(self, category="", extensions="", parent=None, edit_mode=False):
        super().__init__(parent)
        self.setWindowTitle("编辑规则" if edit_mode else "添加规则")
        self.setFixedSize(650, 200)
        self.edit_mode = edit_mode
        self.init_ui()

        if edit_mode:
            self.category_input.setText(category)
            self.extensions_input.setText(extensions)

    def init_ui(self):
        layout = QFormLayout(self)

        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("例: Documents")
        layout.addRow("分类名称:", self.category_input)

        self.extensions_input = QLineEdit()
        self.extensions_input.setPlaceholderText("例: doc,docx,pdf (用逗号分隔)")
        layout.addRow("文件扩展名:", self.extensions_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self):
        """获取输入数据"""
        return self.category_input.text().strip(), self.extensions_input.text().strip()


class FileClassifier:
    """文件分类器核心类"""

    def __init__(self, settings_manager, log_callback=None):
        self.settings_manager = settings_manager
        self.config_file = "classifier_rules.yaml"
        self.backup_dir = "rule_backups"
        # 禁用分类
        self.disabled_categories = set()
        # 记录输出目录历史
        self.output_dirs_history = set()
        # 回调函数
        self.log_callback = log_callback
        # 默认分类规则
        self.default_categories = {
            # 文档类
            'txt': 'Text',
            'doc': 'Documents',
            'docx': 'Documents',
            'pdf': 'PDF',
            'rtf': 'Documents',
            'odt': 'Documents',
            'pages': 'Documents',
            'wpd': 'Documents',
            'wps': 'Documents',
            'md': 'Text',
            'markdown': 'Text',
            'tex': 'Text',
            'text': 'Text',
            'nfo': 'Text',
            'log': 'Text',
            'wri': 'Documents',
            'xps': 'Documents',

            # 电子表格类
            'xlsx': 'Spreadsheets',
            'xls': 'Spreadsheets',
            'csv': 'Spreadsheets',
            'ods': 'Spreadsheets',
            'numbers': 'Spreadsheets',
            'tsv': 'Spreadsheets',
            'gsheet': 'Spreadsheets',

            # 演示文稿
            'ppt': 'Presentations',
            'pptx': 'Presentations',
            'odp': 'Presentations',
            'key': 'Presentations',
            'gslide': 'Presentations',

            # 电子书
            'epub': 'eBooks',
            'mobi': 'eBooks',
            'azw': 'eBooks',
            'azw3': 'eBooks',
            'fb2': 'eBooks',
            'lit': 'eBooks',
            'lrf': 'eBooks',
            'prc': 'eBooks',
            'kpf': 'eBooks',

            # 图片类
            'jpg': 'Images',
            'jpeg': 'Images',
            'png': 'Images',
            'gif': 'Images',
            'bmp': 'Images',
            'svg': 'Images',
            'ico': 'Images',
            'webp': 'Images',
            'tga': 'Images',
            'psd': 'Images',
            'ai': 'Images',
            'eps': 'Images',
            'raw': 'Images',
            'cr2': 'Images',
            'nef': 'Images',
            'heic': 'Images',
            'heif': 'Images',
            'avif': 'Images',
            'jxl': 'Images',
            'wmf': 'Images',
            'emf': 'Images',

            # 视频类
            'mp4': 'Videos',
            'avi': 'Videos',
            'mkv': 'Videos',
            'mov': 'Videos',
            'wmv': 'Videos',
            'flv': 'Videos',
            'webm': 'Videos',
            'm4v': 'Videos',
            'mpg': 'Videos',
            'mpeg': 'Videos',
            '3gp': 'Videos',
            '3g2': 'Videos',
            'rmvb': 'Videos',
            'rm': 'Videos',
            'asf': 'Videos',
            'vob': 'Videos',
            'm2ts': 'Videos',

            # 音频类
            'mp3': 'Audio',
            'wav': 'Audio',
            'flac': 'Audio',
            'aac': 'Audio',
            'ogg': 'Audio',
            'oga': 'Audio',
            'wma': 'Audio',
            'm4a': 'Audio',
            'ape': 'Audio',
            'alac': 'Audio',
            'opus': 'Audio',
            'aiff': 'Audio',
            'aif': 'Audio',
            'au': 'Audio',
            'ra': 'Audio',
            'amr': 'Audio',

            # 压缩包类
            'zip': 'Archives',
            'rar': 'Archives',
            '7z': 'Archives',
            'tar': 'Archives',
            'gz': 'Archives',
            'bz2': 'Archives',
            'xz': 'Archives',
            'dmg': 'Archives',
            'cab': 'Archives',
            'z': 'Archives',
            'arj': 'Archives',
            'lzh': 'Archives',

            # 代码类
            'py': 'Code',
            'js': 'Code',
            'html': 'Code',
            'htm': 'Code',
            'css': 'Code',
            'cpp': 'Code',
            'cxx': 'Code',
            'cc': 'Code',
            'c': 'Code',
            'h': 'Code',
            'hpp': 'Code',
            'java': 'Code',
            'kt': 'Code',
            'swift': 'Code',
            'go': 'Code',
            'rs': 'Code',
            'php': 'Code',
            'rb': 'Code',
            'pl': 'Code',
            'sh': 'Code',
            'bat': 'Code',
            'ps1': 'Code',
            'vbs': 'Code',
            'sql': 'Code',
            'r': 'Code',
            'scala': 'Code',
            'clj': 'Code',
            'hs': 'Code',
            'elm': 'Code',
            'dart': 'Code',
            'vue': 'Code',
            'jsx': 'Code',
            'tsx': 'Code',
            'ts': 'Code',
            'json': 'Code',
            'xml': 'Code',
            'yaml': 'Code',
            'yml': 'Code',
            'toml': 'Code',
            'conf': 'Code',
            'cjs': 'Code',
            'mjs': 'Code',
            'ejs': 'Code',
            'hbs': 'Code',
            'pug': 'Code',
            'haml': 'Code',
            'slim': 'Code',
            'mts': 'Code',
            'scss': 'Code',
            'sass': 'Code',
            'less': 'Code',
            'coffee': 'Code',
            'cljs': 'Code',
            'fs': 'Code',
            'jl': 'Code',
            'lua': 'Code',
            'groovy': 'Code',
            's': 'Code',
            'pas': 'Code',
            'for': 'Code',
            'f90': 'Code',
            'cob': 'Code',
            'bas': 'Code',
            'vb': 'Code',
            'csproj': 'Code',
            'vcproj': 'Code',
            'sln': 'Code',
            'gradle': 'Code',
            'pom': 'Code',
            'Makefile': 'Code',
            'makefile': 'Code',
            'Dockerfile': 'Code',
            'dockerfile': 'Code',
            'gitignore': 'Code',
            'npmrc': 'Code',
            'nvmrc': 'Code',

            # 字体类
            'ttf': 'Fonts',
            'otf': 'Fonts',
            'woff': 'Fonts',
            'woff2': 'Fonts',
            'eot': 'Fonts',
            'fon': 'Fonts',
            'fnt': 'Fonts',

            # 可执行文件
            'exe': 'Executables',
            'msi': 'Executables',
            'app': 'Executables',
            'pkg': 'Executables',
            'run': 'Executables',
            'deb': 'Executables',
            'rpm': 'Executables',
            'apk': 'Executables',
            'ipa': 'Executables',
            'jar': 'Executables',
            'com': 'Executables',
            'drv': 'Executables',
            'vmdk': 'Executables',
            'vhd': 'Executables',

            # 3D模型
            'obj': '3D_Models',
            'fbx': '3D_Models',
            '3ds': '3D_Models',
            'dae': '3D_Models',
            'blend': '3D_Models',
            'max': '3D_Models',
            'ma': '3D_Models',
            'mb': '3D_Models',

            # 数据库文件
            'db': 'Database',
            'sqlite': 'Database',
            'sqlite3': 'Database',
            'mdb': 'Database',
            'accdb': 'Database',
            'dbf': 'Database',
            'sqlitedb': 'Database',
            'frm': 'Database',
            'myd': 'Database',
            'myi': 'Database',
            'ibd': 'Database',

            # 应用文件
            'asar': 'App_Data',
            'blockmap': 'App_Data',
            'pak': 'App_Data',
            'dat': 'App_Data',
            'config': 'App_Data',
            'settings': 'App_Data',
            'pref': 'App_Data',

            # Flash文件
            'swf': 'Flash',
            'fla': 'Flash',

            # 种子文件
            'torrent': 'Torrents',

            # 快捷方式
            'lnk': 'Shortcuts',
            'url': 'Shortcuts',
            'webloc': 'Shortcuts',
            'desktop': 'Shortcuts',

            # CAD文件
            'dwg': 'CAD',
            'dxf': 'CAD',
            'dgn': 'CAD',
            'iges': 'CAD',
            'step': 'CAD',
            'stp': 'CAD',
            'sldprt': 'CAD',
            'sldasm': 'CAD',
            'prt': 'CAD',
            'asm': 'CAD',

            # GIS文件
            'shp': 'GIS',
            'shx': 'GIS',
            'geojson': 'GIS',
            'kml': 'GIS',
            'kmz': 'GIS',
            'gpx': 'GIS',
            'tiff': 'GIS',

            # 光盘镜像
            'iso': 'Disc_Images',
            'img': 'Disc_Images',
            'nrg': 'Disc_Images',
            'ccd': 'Disc_Images',
            'bin': 'Disc_Images',
            'cue': 'Disc_Images',

            # 临时文件
            'tmp': 'Temporary',
            'temp': 'Temporary',
            'bak': 'Temporary',

            # 系统文件
            'dll': 'System',
            'sys': 'System',
            'cfg': 'System',
            'ini': 'System',
            'inf': 'System',
            'reg': 'System',
            'dmp': 'System',
        }

        self.categories = self.default_categories.copy()
        self.load_rules()

    def _log(self, message):
        if self.log_callback:
            self.log_callback(message)

    def generate_output_path(self, base_dir, pattern=None):
        """生成输出路径"""
        if pattern is None:
            pattern = self.settings_manager.get('default_output_pattern')

        # 替换模式中的变量
        now = datetime.now()
        unique_id = str(uuid.uuid4())[:8]
        # 支持的变量
        variables = {
            'date': now.strftime('%Y%m%d'),
            'time': now.strftime('%H%M%S'),
            'datetime': now.strftime('%Y%m%d_%H%M%S'),
            'id': unique_id,
            'uuid': str(uuid.uuid4()),
        }
        # 替换变量
        output_path = pattern
        for var, value in variables.items():
            output_path = output_path.replace(f'{{{var}}}', value)
        # 如果是相对路径, 基于base_dir
        if not os.path.isabs(output_path):
            output_path = os.path.join(base_dir, output_path)
        # 记录输出目录
        self.output_dirs_history.add(os.path.abspath(output_path))
        return output_path

    def is_output_directory(self, path):
        """检查路径是否为输出目录"""
        if not self.settings_manager.get_bool('exclude_output_dirs'):
            return False
        abs_path = os.path.abspath(path)
        # 检查是否是已知的输出目录
        for output_dir in self.output_dirs_history:
            if abs_path == output_dir or abs_path.startswith(output_dir + os.sep):
                return True
        # 检查目录名是否匹配输出目录模式
        dir_name = os.path.basename(abs_path)
        if '分类' in dir_name and ('_' in dir_name or any(char.isdigit() for char in dir_name)):
            return True
        return False

    def toggle_category(self, category, enabled):
        """切换分类的启用状态"""
        if enabled:
            self.disabled_categories.discard(category)
            # 从默认规则中恢复该分类
            for ext, cat in self.default_categories.items():
                if cat == category:
                    self.categories[ext] = cat
        else:
            self.disabled_categories.add(category)
            # 临时移除该分类的规则
            extensions_to_remove = [ext for ext, cat in self.categories.items() if cat == category]
            for ext in extensions_to_remove:
                del self.categories[ext]

        self.save_rules()

    def backup_rules(self):
        """备份规则文件"""
        if not self.settings_manager.get_bool('backup_rules'):
            return
        if not os.path.exists(self.config_file):
            return

        # 创建备份目录
        os.makedirs(self.backup_dir, exist_ok=True)
        # 生成备份文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(self.backup_dir, f"rules_backup_{timestamp}.yaml")
        try:
            shutil.copy2(self.config_file, backup_file)
            self._log(f"规则已备份到: {backup_file}")
        except Exception as e:
            self._log(f"备份失败: {e}")

    def load_rules(self):
        """从YAML文件加载规则"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    # saved_rules = json.load(f)
                    # self.categories.update(saved_rules)
                    data = yaml.safe_load(f)
                    if data:
                        self.categories.update(data.get('categories', {}))
                        self.output_dirs_history.update(data.get('output_dirs_history', []))
                self._log("分类规则已成功加载")
        except Exception as e:
            self._log(f"加载规则失败: {e}")

    def save_rules(self):
        """保存规则到YAML文件"""
        try:
            # 备份现有规则
            self.backup_rules()
            data = {
                'categories': self.categories,
                'output_dirs_history': list(self.output_dirs_history),
                'metadata': {
                    'version': '1.0.1',
                    'created': datetime.now().isoformat(),
                    'disabled_categories': list(self.disabled_categories)
                }
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                # json.dump(self.categories, f, ensure_ascii=False, indent=2)
                yaml.dump(data, f, indent=2, allow_unicode=True)
            self._log("分类规则已自动保存")
        except Exception as e:
            self._log(f"保存规则失败: {e}")

    def add_category_rule(self, extension, category):
        """添加新的分类规则"""
        self.categories[extension.lower()] = category
        self.save_rules()

    def remove_category_rule(self, extension):
        """移除分类规则"""
        if extension.lower() in self.categories:
            del self.categories[extension.lower()]
            self.save_rules()

    def get_file_category(self, filename):
        """根据文件名获取分类"""
        if filename.startswith('.'):
            ext = filename[1:]
        else:
            _, ext = os.path.splitext(filename)
            ext = ext.lower().lstrip('.')
        # return self.categories.get(ext, None)

        category = self.categories.get(ext, None)
        # 检查分类是否被禁用
        if category and category in self.disabled_categories:
            return None
        return category

    def remove_empty_folders(self, path):
        """递归删除空文件夹"""
        if not os.path.exists(path) or not os.path.isdir(path):
            return

        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                self.remove_empty_folders(item_path)
        # 如果目录为空则删除
        try:
            if not os.listdir(path):
                os.rmdir(path)
                self._log(f"已删除空文件夹: {path}")
        except OSError:
            # 目录不为空或无法删除
            pass

    def classify_files(self, src_dir, output_dir=None, move_files=True, callback=None,
                       recursive=False, preserve_structure=None):
        """
        分类文件

        Args:
            src_dir: 源目录
            output_dir: 输出目录, 如果为None则自动生成
            move_files: True移动文件, False复制文件
            callback: 进度回调函数
            recursive: 是否递归处理子文件夹
            preserve_structure: 是否保持目录结构

        Returns:
            tuple: (成功数量, 失败列表, 总数量, 输出目录)
        """
        if not os.path.exists(src_dir):
            raise ValueError(f"目录不存在: {src_dir}")

        # 生成输出目录
        if output_dir is None:
            output_dir = self.generate_output_path(src_dir)
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        if preserve_structure is None:
            preserve_structure = self.settings_manager.get_bool('preserve_structure')
        # 获取所有文件
        all_files = []
        if recursive:
            # 递归获取所有文件
            for root, dirs, files in os.walk(src_dir):
                # 跳过输出目录
                if self.is_output_directory(root):
                    continue
                for file in files:
                    file_path = os.path.join(root, file)
                    # 存储相对于源目录的路径信息
                    rel_path = os.path.relpath(file_path, src_dir)
                    all_files.append((file_path, file, rel_path))
        else:
            # 只获取当前目录的文件
            for f in os.listdir(src_dir):
                file_path = os.path.join(src_dir, f)
                if os.path.isfile(file_path) and not self.is_output_directory(file_path):
                    all_files.append((file_path, f, f))

        total_files = len(all_files)
        success_count = 0
        failed_files = []

        for i, (file_path, filename, rel_path) in enumerate(all_files):
            try:
                # 获取文件分类
                category = self.get_file_category(filename)

                if category:
                    # 创建分类目录
                    category_dir = os.path.join(output_dir, category)
                    os.makedirs(category_dir, exist_ok=True)

                    # 构建目标文件路径
                    if preserve_structure and recursive:
                        # 保持原有的子目录结构
                        rel_dir = os.path.dirname(rel_path)
                        if rel_dir and rel_dir != '.':
                            target_subdir = os.path.join(category_dir, rel_dir)
                            os.makedirs(target_subdir, exist_ok=True)
                            dst_file = os.path.join(target_subdir, filename)
                        else:
                            dst_file = os.path.join(category_dir, filename)
                    else:
                        dst_file = os.path.join(category_dir, filename)

                    # 处理文件名冲突
                    counter = 1
                    base_name, ext = os.path.splitext(filename)
                    original_dst = dst_file
                    while os.path.exists(dst_file):
                        new_filename = f"{base_name}_{counter}{ext}"
                        # dst_file = os.path.join(category_dir, new_filename)
                        dst_file = os.path.join(os.path.dirname(original_dst), new_filename)
                        counter += 1

                    # 移动或复制文件
                    if move_files:
                        shutil.move(file_path, dst_file)
                    else:
                        shutil.copy2(file_path, dst_file)

                    success_count += 1
                else:
                    failed_files.append(f"无法识别: {rel_path}")

            except Exception as e:
                failed_files.append(f"{rel_path}: {str(e)}")

            # 调用进度回调
            if callback:
                callback(i + 1, total_files, rel_path)

        # 清理空文件夹
        if move_files and self.settings_manager.get_bool('remove_empty_folders'):
            self.remove_empty_folders(src_dir)
        return success_count, failed_files, total_files, output_dir


class ClassificationThread(QThread):
    """文件分类线程"""

    progress_updated = pyqtSignal(int, int, str)  # 当前进度, 总数, 当前文件
    classification_finished = pyqtSignal(int, list, int, str)  # 成功数, 失败列表, 总数, 输出目录

    def __init__(self, classifier, src_dir, output_dir=None, move_files=True,
                 recursive=False, preserve_structure=None):
        super().__init__()
        self.classifier = classifier
        self.src_dir = src_dir
        self.output_dir = output_dir
        self.move_files = move_files
        self.recursive = recursive
        self.preserve_structure = preserve_structure

    def run(self):
        """运行分类任务"""
        try:
            success_count, failed_files, total_files, output_dir = self.classifier.classify_files(
                self.src_dir,
                output_dir=self.output_dir,
                move_files=self.move_files,
                callback=self.progress_callback,
                recursive=self.recursive,
                preserve_structure=self.preserve_structure
            )
            self.classification_finished.emit(success_count, failed_files, total_files, output_dir)
        except Exception as e:
            self.classification_finished.emit(0, [f"错误: {str(e)}"], 0)

    def progress_callback(self, current, total, filename):
        """进度回调"""
        self.progress_updated.emit(current, total, filename)


class FileClassifierGUI(QMainWindow):
    """文件分类器GUI主窗口"""

    def __init__(self):
        super().__init__()
        self.settings_manager = SettingsManager()
        self.classification_thread = None
        self.init_ui()

        self.classifier = FileClassifier(self.settings_manager, log_callback=self.log_text.append)
        self.update_rules_management()
        self.update_rules_preview()

        self.create_menu_bar()
        self.center_window()
        self.apply_settings()

    def center_window(self):
        """将窗口居中显示"""
        screen = QApplication.desktop().screenGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("文件自动分类器 v1.0.1")
        self.setGeometry(0, 0, 850, 1000)
        self.setMaximumWidth(850)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 标题
        title_label = QLabel("文件自动分类器")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("Arial", 16, QFont.Bold)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)

        # 选项卡
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        self.init_basic_tab()
        self.init_rules_tab()
        self.init_log_tab()

    def init_basic_tab(self):
        """初始化基本操作选项卡"""
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)

        # 路径设置区域
        dir_group = QGroupBox("路径设置")
        dir_layout = QFormLayout(dir_group)
        self.dir_input = QLineEdit()
        self.dir_input.setPlaceholderText("请选择要分类的源目录...")
        browse_src_btn = QPushButton("浏览")
        browse_src_btn.clicked.connect(self.browse_source_directory)
        src_layout = QHBoxLayout()
        src_layout.addWidget(self.dir_input)
        src_layout.addWidget(browse_src_btn)
        dir_layout.addRow("源目录:", src_layout)
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setPlaceholderText("留空以在源目录下自动创建...")
        browse_out_btn = QPushButton("浏览")
        browse_out_btn.clicked.connect(self.browse_output_directory)
        out_layout = QHBoxLayout()
        out_layout.addWidget(self.output_dir_input)
        out_layout.addWidget(browse_out_btn)
        dir_layout.addRow("输出目录:", out_layout)
        basic_layout.addWidget(dir_group)

        # 选项区域
        options_group = QGroupBox("分类选项")
        options_layout = QGridLayout(options_group)
        self.move_files_cb = QCheckBox("移动文件 (取消则为复制)")
        self.recursive_cb = QCheckBox("包含子文件夹 (递归处理)")
        self.preserve_structure_cb = QCheckBox("保持原有目录结构")
        self.remove_empty_folders_cb = QCheckBox("清理源目录中的空文件夹 (仅移动时有效)")
        options_layout.addWidget(self.move_files_cb, 0, 0)
        options_layout.addWidget(self.recursive_cb, 0, 1)
        options_layout.addWidget(self.preserve_structure_cb, 1, 0)
        options_layout.addWidget(self.remove_empty_folders_cb, 1, 1)
        basic_layout.addWidget(options_group)
        basic_layout.addStretch()

        # 控制按钮
        button_layout = QHBoxLayout()
        self.classify_btn = QPushButton("开始分类")
        self.classify_btn.clicked.connect(self.start_classification)
        self.classify_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }")
        button_layout.addWidget(self.classify_btn)
        self.stop_btn = QPushButton("停止分类")
        self.stop_btn.clicked.connect(self.stop_classification)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 8px; }")
        button_layout.addWidget(self.stop_btn)
        basic_layout.addLayout(button_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(25)
        basic_layout.addWidget(self.progress_bar)

        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setMaximumHeight(35)
        self.status_label.setStyleSheet(
            "QLabel { background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 4px; padding: 8px; }")
        basic_layout.addWidget(self.status_label)
        self.tab_widget.addTab(basic_tab, "基本操作")

    def init_rules_tab(self):
        """初始化规则管理选项卡"""
        rules_tab = QWidget()
        rules_layout = QVBoxLayout(rules_tab)
        splitter = QSplitter(Qt.Vertical)
        rules_layout.addWidget(splitter)

        rules_manage_group = QGroupBox("分类规则管理")
        rules_manage_layout = QVBoxLayout(rules_manage_group)
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入扩展名或分类名称搜索...")
        self.search_input.textChanged.connect(self.filter_rules)
        clear_search_btn = QPushButton("清空")
        clear_search_btn.clicked.connect(self.search_input.clear)
        search_layout.addWidget(QLabel("搜索规则:"))
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(clear_search_btn)
        rules_manage_layout.addLayout(search_layout)

        rule_buttons_layout = QHBoxLayout()
        self.add_rule_btn = QPushButton("添加规则")
        self.add_rule_btn.clicked.connect(self.add_rule)
        self.add_rule_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; }")
        rule_buttons_layout.addWidget(self.add_rule_btn)
        self.reset_rules_btn = QPushButton("重置为默认")
        self.reset_rules_btn.clicked.connect(self.reset_rules)
        self.reset_rules_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; }")
        rule_buttons_layout.addWidget(self.reset_rules_btn)
        self.clear_all_rules_btn = QPushButton("清空所有规则")
        self.clear_all_rules_btn.clicked.connect(self.clear_all_rules)
        self.clear_all_rules_btn.setStyleSheet("QPushButton { background-color: #ff9800; color: white; }")
        rule_buttons_layout.addWidget(self.clear_all_rules_btn)
        rule_buttons_layout.addStretch()
        rules_manage_layout.addLayout(rule_buttons_layout)

        # 规则编辑区域 (折叠面板)
        self.rules_scroll_area = QScrollArea()
        self.rules_widget = QWidget()
        self.rules_layout = QVBoxLayout(self.rules_widget)
        self.rules_scroll_area.setWidget(self.rules_widget)
        self.rules_scroll_area.setWidgetResizable(True)
        rules_manage_layout.addWidget(self.rules_scroll_area)
        splitter.addWidget(rules_manage_group)

        # 分类规则预览区域
        preview_group = QGroupBox("分类规则预览")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_scroll_area = QScrollArea()
        self.preview_widget = QWidget()
        self.preview_layout = QVBoxLayout(self.preview_widget)
        self.preview_scroll_area.setWidget(self.preview_widget)
        self.preview_scroll_area.setWidgetResizable(True)
        preview_layout.addWidget(self.preview_scroll_area)
        splitter.addWidget(preview_group)

        splitter.setSizes([400, 250])
        self.tab_widget.addTab(rules_tab, "规则管理")

    def init_log_tab(self):
        """初始化日志选项卡"""
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)

        # 日志区域
        log_group = QGroupBox("分类日志")
        log_group_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_group_layout.addWidget(self.log_text)

        # 日志操作按钮
        log_buttons_layout = QHBoxLayout()
        clear_log_btn = QPushButton("清空日志")
        clear_log_btn.clicked.connect(self.log_text.clear)
        log_buttons_layout.addWidget(clear_log_btn)
        save_log_btn = QPushButton("保存日志")
        save_log_btn.clicked.connect(self.save_log)
        log_buttons_layout.addWidget(save_log_btn)
        log_buttons_layout.addStretch()
        log_group_layout.addLayout(log_buttons_layout)

        log_layout.addWidget(log_group)
        self.tab_widget.addTab(log_tab, "操作日志")

    def apply_settings(self):
        """应用加载的设置到UI"""
        self.move_files_cb.setChecked(self.settings_manager.get_bool('move_files'))
        self.recursive_cb.setChecked(self.settings_manager.get_bool('recursive'))
        self.preserve_structure_cb.setChecked(self.settings_manager.get_bool('preserve_structure'))
        self.remove_empty_folders_cb.setChecked(self.settings_manager.get_bool('remove_empty_folders'))
        font = self.font()
        font.setPointSize(self.settings_manager.get_int('font_size'))
        self.setFont(font)
        self.log_text.document().setMaximumBlockCount(self.settings_manager.get_int('max_log_lines'))

    def save_log(self):
        """保存日志到文件"""
        file_path, _ = QFileDialog.getSaveFileName(self, "保存日志",
                                                   f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                                                   "Text files (*.txt)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                QMessageBox.information(self, "保存成功", "日志已成功保存")
            except Exception as e:
                QMessageBox.warning(self, "保存失败", f"保存日志失败: {str(e)}")

    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu('文件(&F)')
        import_action = QAction('导入规则...', self)
        import_action.triggered.connect(self.import_rules)
        file_menu.addAction(import_action)
        export_action = QAction('导出规则...', self)
        export_action.triggered.connect(self.export_rules)
        file_menu.addAction(export_action)
        file_menu.addSeparator()
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 编辑菜单
        edit_menu = menubar.addMenu('编辑(&E)')
        add_rule_action = QAction('添加规则...', self)
        add_rule_action.triggered.connect(self.add_rule)
        edit_menu.addAction(add_rule_action)
        reset_action = QAction('重置规则', self)
        reset_action.triggered.connect(self.reset_rules)
        edit_menu.addAction(reset_action)

        # 选项菜单
        options_menu = menubar.addMenu('选项(&O)')
        settings_action = QAction('设置...', self)
        settings_action.triggered.connect(self.open_settings)
        options_menu.addAction(settings_action)

        # 工具菜单
        tools_menu = menubar.addMenu('工具(&T)')
        stats_action = QAction('统计信息', self)
        stats_action.triggered.connect(self.show_stats)
        tools_menu.addAction(stats_action)

        # 帮助菜单
        help_menu = menubar.addMenu('说明(&H)')
        donate_action = QAction('💰 捐赠', self)
        donate_action.triggered.connect(lambda: webbrowser.open("https://github.com/xuyouer/"))
        help_menu.addAction(donate_action)
        contact_action = QAction('📧 联系', self)
        contact_action.triggered.connect(lambda: webbrowser.open("https://github.com/xuyouer/"))
        help_menu.addAction(contact_action)
        homepage_action = QAction('🏠 首页', self)
        homepage_action.triggered.connect(lambda: webbrowser.open("https://github.com/xuyouer/"))
        help_menu.addAction(homepage_action)
        help_menu.addSeparator()
        about_action = QAction('关于...', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def open_settings(self):
        """打开设置对话框"""
        dialog = SettingsDialog(self.settings_manager, self)
        if dialog.exec_() == QDialog.Accepted:
            self.apply_settings()
            QMessageBox.information(self, "设置", "设置已保存并应用")

    def show_about(self):
        """显示关于对话框"""
        dialog = AboutDialog(self)
        dialog.exec_()

    def show_stats(self):
        """显示统计信息"""
        total_rules = len(self.classifier.categories)
        categories = set(self.classifier.categories.values())

        stats_text = f"""
规则统计信息:
- 总规则数: {total_rules}
- 分类数量: {len(categories)}
- 支持的分类: {', '.join(sorted(categories))}
        """

        QMessageBox.information(self, "统计信息", stats_text.strip())

    def import_rules(self):
        """导入规则"""
        # file_path, _ = QFileDialog.getOpenFileName(self, "导入规则", "", "JSON files (*.json)")
        file_path, _ = QFileDialog.getOpenFileName(self, "导入规则", "", "YAML files (*.yaml *.yml)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    # imported_rules = json.load(f)
                    data = yaml.safe_load(f)
                    imported_rules = data.get('categories', {})
                self.classifier.categories.update(imported_rules)
                if self.settings_manager.get_bool('auto_save'):
                    self.classifier.save_rules()
                self.update_rules_management()
                self.update_rules_preview()
                QMessageBox.information(self, "导入成功", f"成功导入 {len(imported_rules)} 条规则")
            except Exception as e:
                QMessageBox.warning(self, "导入失败", f"导入规则失败: {str(e)}")

    def export_rules(self):
        """导出规则"""
        # file_path, _ = QFileDialog.getSaveFileName(self, "导出规则", "rules.json", "JSON files (*.json)")
        file_path, _ = QFileDialog.getSaveFileName(self, "导出规则", "rules.yaml", "YAML files (*.yaml *.yml)")
        if file_path:
            try:
                data_to_export = {'categories': self.classifier.categories}
                with open(file_path, 'w', encoding='utf-8') as f:
                    # json.dump(self.classifier.categories, f, ensure_ascii=False, indent=2)
                    yaml.dump(data_to_export, f, indent=2, allow_unicode=True)
                QMessageBox.information(self, "导出成功", "规则已成功导出")
            except Exception as e:
                QMessageBox.warning(self, "导出失败", f"导出规则失败: {str(e)}")

    def filter_rules(self):
        """过滤规则显示"""
        search_text = self.search_input.text().lower().strip()

        # 遍历所有规则组
        for i in range(self.rules_layout.count()):
            item = self.rules_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()

                # 检查是否为QCollapsibleGroupBox类型的widget
                if isinstance(widget, QCollapsibleGroupBox):
                    # 获取组标题(去除括号中的数量信息)
                    title = widget.title()
                    category_name = title.split('(')[0].strip().lower()
                    # 检查分类名称是否匹配
                    category_match = search_text in category_name
                    # extensions = [k for k, v in self.classifier.categories.items() if v.lower() == title]
                    # extension_match = any(search_text in ext.lower() for ext in extensions)
                    # widget.setVisible(not search_text or category_match or extension_match)
                    # 检查扩展名是否匹配
                    extension_match = False
                    # 从分类器中获取该分类下的所有扩展名
                    for ext, cat in self.classifier.categories.items():
                        if cat.lower() == category_name:
                            if search_text in ext.lower():
                                extension_match = True
                                break
                    # 显示或隐藏规则组
                    is_visible = not search_text or category_match or extension_match
                    widget.setVisible(is_visible)
                    # 如果有搜索文本且匹配, 展开该组
                    if search_text and is_visible:
                        widget.setChecked(True)

    def clear_search(self):
        """清空搜索框并显示所有规则"""
        self.search_input.clear()
        # 显示所有规则组
        for i in range(self.rules_layout.count()):
            item = self.rules_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, QCollapsibleGroupBox):
                    widget.setVisible(True)

    def clear_all_rules(self):
        """清空所有规则"""
        reply = QMessageBox.question(
            self, "确认清空",
            "确定要清空所有分类规则吗？这将删除所有规则(包括默认规则)",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.classifier.categories.clear()
            if self.settings_manager.get_bool('auto_save'): self.classifier.save_rules()
            self.update_rules_management()
            self.update_rules_preview()
            QMessageBox.information(self, "清空完成", "所有规则已清空")

    def add_rule(self):
        """添加新规则"""
        dialog = RuleEditDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            category, extensions = dialog.get_data()
            if category and extensions:
                ext_list = [ext.strip() for ext in extensions.split(',') if ext.strip()]
                for ext in ext_list:
                    self.classifier.add_category_rule(ext, category)
                self.update_rules_management()
                self.update_rules_preview()
                QMessageBox.information(self, "添加成功", f"已添加 {len(ext_list)} 条规则到分类 '{category}'")

    def reset_rules(self):
        """重置为默认规则"""
        reply = QMessageBox.question(
            self, "确认重置",
            "确定要重置为默认规则吗？这将清除所有自定义规则",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.classifier.categories = self.classifier.default_categories.copy()
            if self.settings_manager.get_bool('auto_save'): self.classifier.save_rules()
            self.update_rules_management()
            self.update_rules_preview()
            QMessageBox.information(self, "重置完成", "规则已重置为默认设置")

    def update_rules_management(self):
        """更新规则管理区域"""
        # 清除现有控件
        # while self.rules_layout.count(): self.rules_layout.takeAt(0).widget().deleteLater()
        for i in reversed(range(self.rules_layout.count())):
            child = self.rules_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        # 按分类组织规则
        categories_dict = {}
        for ext, category in self.classifier.categories.items():
            # categories_dict.setdefault(category, []).append(ext)
            if category not in categories_dict:
                categories_dict[category] = []
            categories_dict[category].append(ext)

        # 为每个分类创建折叠面板
        for category, extensions in sorted(categories_dict.items()):
            group = QCollapsibleGroupBox(f"{category} ({len(extensions)}条规则)", category_name=category)
            group.rule_toggled.connect(self.on_rule_toggled)
            group_layout = QVBoxLayout(group)
            # 扩展名显示
            ext_text = ', '.join(sorted(extensions))
            ext_label = QLabel(f"扩展名: {ext_text}")
            ext_label.setWordWrap(True)
            group_layout.addWidget(ext_label)
            # 操作按钮
            button_layout = QHBoxLayout()
            edit_btn = QPushButton("编辑")
            edit_btn.clicked.connect(lambda checked, c=category, e=ext_text: self.edit_rule(c, e))
            button_layout.addWidget(edit_btn)
            delete_btn = QPushButton("删除")
            delete_btn.clicked.connect(lambda checked, c=category: self.delete_category(c))
            delete_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; }")
            button_layout.addWidget(delete_btn)
            button_layout.addStretch()
            group_layout.addLayout(button_layout)
            self.rules_layout.addWidget(group)

    def edit_rule(self, category, extensions):
        """编辑规则"""
        dialog = RuleEditDialog(category, extensions, self, edit_mode=True)
        if dialog.exec_() == QDialog.Accepted:
            new_category, new_extensions = dialog.get_data()
            if new_category and new_extensions:
                # 删除旧规则
                old_extensions = [ext.strip() for ext in extensions.split(',')]
                for ext in old_extensions:
                    self.classifier.remove_category_rule(ext)
                # 添加新规则
                new_ext_list = [ext.strip() for ext in new_extensions.split(',') if ext.strip()]
                for ext in new_ext_list:
                    self.classifier.add_category_rule(ext, new_category)
                self.update_rules_management()
                self.update_rules_preview()
                QMessageBox.information(self, "编辑成功", "规则已更新")

    def on_rule_toggled(self, category_name, enabled):
        """处理规则组的启用/禁用"""
        if enabled:
            # 重新启用该分类的规则
            # 从默认规则中恢复该分类的规则
            for ext, cat in self.classifier.default_categories.items():
                if cat == category_name:
                    self.classifier.categories[ext] = cat

            self.log_text.append(f"已启用分类规则: {category_name}")
        else:
            # 禁用该分类的规则(临时移除)
            extensions_to_remove = [ext for ext, cat in self.classifier.categories.items() if cat == category_name]
            for ext in extensions_to_remove:
                del self.classifier.categories[ext]

            self.log_text.append(f"已禁用分类规则: {category_name}")

        # 保存规则并更新预览
        self.classifier.save_rules()
        self.update_rules_preview()

    def delete_category(self, category):
        """删除整个分类"""
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除分类 '{category}' 的所有规则吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 找到所有属于该分类的扩展名并删除
            extensions_to_remove = [ext for ext, cat in self.classifier.categories.items() if cat == category]
            for ext in extensions_to_remove:
                self.classifier.remove_category_rule(ext)

            self.update_rules_management()
            self.update_rules_preview()
            QMessageBox.information(self, "删除成功", f"已删除分类 '{category}' 的 {len(extensions_to_remove)} 条规则")

    def update_rules_preview(self):
        """更新分类规则预览"""
        # 清除现有控件
        # while self.preview_layout.count(): self.preview_layout.takeAt(0).widget().deleteLater()
        for i in reversed(range(self.preview_layout.count())):
            child = self.preview_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        # 按分类组织显示规则
        categories_dict = {}
        for ext, category in self.classifier.categories.items():
            # categories_dict.setdefault(category, []).append(ext)
            if category not in categories_dict:
                categories_dict[category] = []
            categories_dict[category].append(ext)

        for category, extensions in sorted(categories_dict.items()):
            rule_text = f"📁 {category}: {', '.join(sorted(extensions))}"
            rule_label = QLabel(rule_text)
            rule_label.setWordWrap(True)
            rule_label.setStyleSheet("padding: 5px; border: 1px solid #ddd; border-radius: 4px; margin: 2px;")
            self.preview_layout.addWidget(rule_label)

    def browse_source_directory(self):
        """选择要分类的源目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择要分类的源目录")
        if directory:
            self.dir_input.setText(directory)

    def browse_output_directory(self):
        """选择输出目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if directory:
            self.output_dir_input.setText(directory)

    def start_classification(self):
        """开始文件分类"""
        src_dir = self.dir_input.text().strip()
        output_dir = self.output_dir_input.text().strip() or None

        if not src_dir:
            QMessageBox.warning(self, "警告", "请先选择要分类的目录")
            return
        if not os.path.exists(src_dir):
            QMessageBox.warning(self, "警告", "选择的目录不存在")
            return

        # 获取选项
        recursive = self.recursive_cb.isChecked()
        preserve_structure = self.preserve_structure_cb.isChecked()

        # 检查目录中是否有文件
        if recursive:
            # 递归检查所有子目录
            files = []
            for root, dirs, file_list in os.walk(src_dir):
                files.extend([os.path.join(root, f) for f in file_list])
        else:
            # 只检查当前目录
            files = [f for f in os.listdir(src_dir)
                     if os.path.isfile(os.path.join(src_dir, f))]

        if not files:
            QMessageBox.information(self, "信息", "选择的目录中没有文件需要分类")
            return

        # 确认操作
        move_files = self.move_files_cb.isChecked()
        action = "移动" if move_files else "复制"
        recursive_text = "(包含子文件夹)" if recursive else ""

        # 检查设置中是否需要确认
        if self.settings_manager.get_bool('confirm_action'):
            reply = QMessageBox.question(
                self,
                "确认操作",
                f"确定要{action}目录中的 {len(files)} 个文件吗？{recursive_text}",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        # 开始分类
        self.log_text.clear()
        self.log_text.append(f"开始{action}文件...")
        self.log_text.append(f"源目录: {src_dir}")
        self.log_text.append(f"输出目录: {'自动创建' if not output_dir else output_dir}")
        self.log_text.append(f"递归处理: {'是' if recursive else '否'}")
        self.log_text.append(f"文件数量: {len(files)}")
        self.log_text.append("-" * 50)

        # 设置UI状态
        self.classify_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在分类...")

        # 创建并启动分类线程
        self.classification_thread = ClassificationThread(
            self.classifier, src_dir, output_dir, move_files, recursive, preserve_structure
        )
        self.classification_thread.progress_updated.connect(self.update_progress)
        self.classification_thread.classification_finished.connect(self.classification_complete)
        self.classification_thread.start()

    def stop_classification(self):
        """停止文件分类"""
        if self.classification_thread and self.classification_thread.isRunning():
            self.classification_thread.terminate()
            self.classification_thread.wait()
            self.reset_ui_state()
            self.log_text.append("\n分类已被用户取消")
            self.status_label.setText("已取消")

    def update_progress(self, current, total, filename):
        """更新进度"""
        if total > 0:
            progress = int((current / total) * 100)
            self.progress_bar.setValue(progress)
            self.status_label.setText(f"正在处理: {filename} ({current}/{total})")
            # 根据日志级别显示详细信息
            if self.settings_manager.get('log_level') in ["详细", "调试"]:
                self.log_text.append(f"处理文件: {filename}")

    def classification_complete(self, success_count, failed_files, total_files, output_dir):
        """分类完成"""
        self.reset_ui_state()

        # 显示结果
        self.log_text.append("-" * 50)
        self.log_text.append(f"分类完成")
        self.log_text.append(f"文件已分类至: {output_dir}")
        self.log_text.append(f"总文件数: {total_files}")
        self.log_text.append(f"成功分类: {success_count}")
        self.log_text.append(f"失败数量: {len(failed_files)}")

        if failed_files:
            self.log_text.append("\n失败详情:")
            for failed in failed_files:
                self.log_text.append(f"  - {failed}")

        self.status_label.setText(f"完成 - 成功: {success_count}, 失败: {len(failed_files)}")

        # 保存规则
        if self.settings_manager.get_bool('auto_save'):
            self.classifier.save_rules()

        # 显示完成对话框
        msg_title = "分类部分完成" if failed_files else "分类成功"
        msg_text = f"分类完成\n成功: {success_count}\n失败: {len(failed_files)}\n输出目录:\n{output_dir}\n\n详情请查看日志" if failed_files else f"所有文件分类成功\n共处理 {success_count} 个文件"
        # QMessageBox.information(self, msg_title, msg_text)
        if failed_files:
            QMessageBox.warning(self, msg_title, msg_text)
        else:
            QMessageBox.information(self, msg_title, msg_text)

    def reset_ui_state(self, classifying=False):
        """重置UI状态"""
        self.classify_btn.setEnabled(not classifying)
        self.stop_btn.setEnabled(classifying)
        self.progress_bar.setVisible(classifying)
        self.progress_bar.setValue(0)

    def closeEvent(self, event):
        """关闭事件处理"""
        if self.classification_thread and self.classification_thread.isRunning():
            reply = QMessageBox.question(
                self, "确认退出",
                "分类正在进行中, 确定要退出吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.stop_classification()
                event.accept()
            else:
                event.ignore()
        else:
            if self.settings_manager.get_bool('auto_save'): self.classifier.save_rules()
            event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setApplicationName("文件自动分类器")
    app.setApplicationVersion("1.0.1")
    app.setOrganizationName("xuyou & xiaomizha")
    window = FileClassifierGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
