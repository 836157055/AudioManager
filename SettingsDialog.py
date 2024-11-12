from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QListWidget, QHBoxLayout, QFileDialog, QRadioButton, QLabel, QButtonGroup

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.audio_library_paths_list = QListWidget()
        self.layout.addWidget(self.audio_library_paths_list)

        self.add_button = QPushButton("添加路径")
        self.add_button.clicked.connect(self.add_path)
        self.layout.addWidget(self.add_button)

        self.remove_button = QPushButton("移除选定路径")
        self.remove_button.clicked.connect(self.remove_selected_path)
        self.layout.addWidget(self.remove_button)

        self.import_button = QPushButton("导入设置")
        self.import_button.clicked.connect(parent.import_settings)
        self.layout.addWidget(self.import_button)

        self.export_button = QPushButton("导出设置")
        self.export_button.clicked.connect(parent.export_settings)
        self.layout.addWidget(self.export_button)

        self.layout.addWidget(QLabel("界面刷新率:"))
        self.low_refresh_rate = QRadioButton("低")
        self.medium_refresh_rate = QRadioButton("中")
        self.high_refresh_rate = QRadioButton("高")
        self.refresh_rate_group = QButtonGroup()
        self.refresh_rate_group.addButton(self.low_refresh_rate)
        self.refresh_rate_group.addButton(self.medium_refresh_rate)
        self.refresh_rate_group.addButton(self.high_refresh_rate)
        self.layout.addWidget(self.low_refresh_rate)
        self.layout.addWidget(self.medium_refresh_rate)
        self.layout.addWidget(self.high_refresh_rate)

        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.accept)
        self.layout.addWidget(self.save_button)

        self.load_paths()
        self.load_refresh_rate()

    def load_paths(self):
        self.audio_library_paths_list.clear()
        for path in self.parent().audio_library_paths:
            self.audio_library_paths_list.addItem(path)

    def add_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择目录")
        if path:
            self.audio_library_paths_list.addItem(path)

    def remove_selected_path(self):
        for item in self.audio_library_paths_list.selectedItems():
            self.audio_library_paths_list.takeItem(self.audio_library_paths_list.row(item))

    def load_refresh_rate(self):
        refresh_rate = self.parent().refresh_rate
        if refresh_rate == 1000:
            self.low_refresh_rate.setChecked(True)
        elif refresh_rate == 500:
            self.medium_refresh_rate.setChecked(True)
        else:
            self.high_refresh_rate.setChecked(True)

    def get_selected_refresh_rate(self):
        if self.low_refresh_rate.isChecked():
            return 500
        elif self.medium_refresh_rate.isChecked():
            return 100
        else:
            return 1