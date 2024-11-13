import shutil
import sys
import os
import pygame
import librosa
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QFileDialog, QTableWidget, \
    QTableWidgetItem, QHeaderView, QAbstractItemView, QLabel, QProgressBar, QHBoxLayout, QSlider, QMenuBar, QMenu, \
    QAction, QStyle
from PyQt5.QtCore import Qt, QTimer, QThread, QMimeData, QUrl
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QFont, QMouseEvent, QDrag

from DraggableTableWidget import DraggableTableWidget
from extract_features import extract_features
from calculate_similarity import calculate_similarity
from SettingsDialog import SettingsDialog
from AudioProcessor import AudioProcessor

class AudioManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("音频库管理器")
        self.setGeometry(100, 100, 1000, 800)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        self.menu_bar = QMenuBar(self)
        self.setMenuBar(self.menu_bar)
        self.settings_menu = QMenu("菜单", self)
        self.menu_bar.addMenu(self.settings_menu)

        self.upload_action = QAction("上传参考音频", self)
        self.upload_action.triggered.connect(self.upload_reference_audio)
        self.settings_menu.addAction(self.upload_action)

        self.settings_action = QAction("打开设置", self)
        self.settings_action.triggered.connect(self.open_settings)
        self.settings_menu.addAction(self.settings_action)

        self.reference_control_layout = QHBoxLayout()
        self.reference_label = QLabel("参考音频: 无")
        self.reference_control_layout.addWidget(self.reference_label)
        self.play_pause_button = QPushButton("播放")
        self.play_pause_button.clicked.connect(self.play_pause_reference)
        self.reference_control_layout.addWidget(self.play_pause_button)
        self.layout.addLayout(self.reference_control_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { background-color: yellow; }")
        self.layout.addWidget(self.progress_bar)

        self.log_layout = QHBoxLayout()
        self.log_label = QLabel("释放鼠标以加载参考文件")
        self.log_label.setAlignment(Qt.AlignCenter)
        self.log_label.setStyleSheet("background-color: yellow; font-size: 16px;")
        self.log_label.setVisible(False)
        self.log_layout.addWidget(self.log_label)

        self.close_log_button = QPushButton("X")
        self.close_log_button.setFixedSize(20, 20)
        self.close_log_button.clicked.connect(self.close_log)
        self.close_log_button.setVisible(False)
        self.log_layout.addWidget(self.close_log_button)
        self.layout.addLayout(self.log_layout)

        self.table_widget = DraggableTableWidget()
        self.table_widget.setColumnCount(4)
        self.table_widget.setHorizontalHeaderLabels(["文件", "路径", "相似度", "播放"])
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Make the table read-only
        self.layout.addWidget(self.table_widget)
        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.show_context_menu)

        self.progress_label = QLabel("进度: 00:00 / 00:00")
        self.layout.addWidget(self.progress_label)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.sliderMoved.connect(self.set_position)
        self.slider.mousePressEvent = self.slider_mouse_press_event
        self.layout.addWidget(self.slider)

        self.overlay = QLabel(self.central_widget)
        self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 128);")
        self.overlay.setVisible(False)
        self.overlay.setGeometry(0, 0, self.width(), self.height())

        pygame.mixer.init()
        self.currently_playing = None
        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.update_progress)
        self.similar_files = []
        self.new_time = 0

        self.load_settings()

        self.setAcceptDrops(True)
        self.is_setting_position = False

        self.table_widget.setDragEnabled(True)
        self.table_widget.setDragDropMode(QAbstractItemView.DragOnly)

        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.show_context_menu)


    def load_settings(self):
        self.audio_library_paths = []
        self.refresh_rate = 500
        if os.path.exists("config.txt"):
            with open("config.txt", "r") as file:
                lines = file.readlines()
                self.audio_library_paths = [line.strip() for line in lines[:-1]]
                try:
                    self.refresh_rate = int(lines[-1].strip())
                except ValueError:
                    self.refresh_rate = 500  # Default value if the last line is not an integer
        self.timer.setInterval(self.refresh_rate)

    def save_settings(self):
        with open("config.txt", "w") as file:
            for path in self.audio_library_paths:
                file.write(f"{path}\n")
            file.write(f"{self.refresh_rate}\n")

    def import_settings(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "导入设置", "", "配置文件 (*.txt)")
        if file_path:
            with open(file_path, "r") as file:
                lines = file.readlines()
                self.audio_library_paths = [line.strip() for line in lines[:-1]]
                self.refresh_rate = int(lines[-1].strip())
            self.save_settings()
            self.timer.setInterval(self.refresh_rate)

    def export_settings(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "导出设置", "", "配置文件 (*.txt)")
        if file_path:
            with open(file_path, "w") as file:
                for path in self.audio_library_paths:
                    file.write(f"{path}\n")
                file.write(f"{self.refresh_rate}\n")

    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec_():
            self.audio_library_paths = [dialog.audio_library_paths_list.item(i).text() for i in range(dialog.audio_library_paths_list.count())]
            self.refresh_rate = dialog.get_selected_refresh_rate()
            self.save_settings()
            self.timer.setInterval(self.refresh_rate)

    def upload_reference_audio(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "打开参考音频", "", "音频文件 (*.wav *.mp3)")
        if file_path:
            self.process_reference_audio(file_path)

    def process_reference_audio(self, file_path):
        self.reference_label.setText(f"参考音频: {os.path.basename(file_path)}")
        self.reference_file_path = file_path
        self.process_audio(file_path)

    def process_audio(self, file_path):
        try:
            self.progress_bar.setVisible(True)
            self.log_label.setText("加载参考音频...")
            self.log_label.setVisible(True)
            self.close_log_button.setVisible(True)
            self.overlay.setVisible(True)
            self.set_elements_enabled(False)
            self.table_widget.setRowCount(0)
            self.ref_mfcc = extract_features(file_path)
            self.similar_files = []
            self.thread = QThread()
            self.worker = AudioProcessor(self.audio_library_paths, self.ref_mfcc)
            self.worker.moveToThread(self.thread)
            self.worker.progress.connect(self.update_progress_bar)
            self.worker.finished.connect(self.display_results)
            self.thread.started.connect(self.worker.run)
            self.thread.start()
        except Exception as e:
            self.log_label.setText(f"错误: {str(e)}")
            self.log_label.setStyleSheet("background-color: red; font-size: 16px;")
            self.log_label.setVisible(True)
            self.close_log_button.setVisible(True)

    def update_progress_bar(self, value, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(value)

    def display_results(self, similar_files):
        try:
            self.similar_files = similar_files
            self.table_widget.setRowCount(0)
            for idx, (file, path, similarity) in enumerate(self.similar_files):
                self.table_widget.insertRow(idx)
                self.table_widget.setItem(idx, 0, QTableWidgetItem(file))
                self.table_widget.setItem(idx, 1, QTableWidgetItem(path))
                self.table_widget.setItem(idx, 2, QTableWidgetItem(str(similarity)))
                play_button = QPushButton("播放")
                play_button.clicked.connect(lambda _, p=path, b=play_button: self.on_play_button_click(p, b))
                self.table_widget.setCellWidget(idx, 3, play_button)
                self.table_widget.setDragEnabled(True)
                self.table_widget.setDragDropMode(QAbstractItemView.DragOnly)
            self.progress_bar.setVisible(False)
            self.log_label.setVisible(False)
            self.close_log_button.setVisible(False)
            self.overlay.setVisible(False)
            self.set_elements_enabled(True)
            self.thread.quit()
        except Exception as e:
            self.log_label.setText(f"错误: {str(e)}")
            self.log_label.setStyleSheet("background-color: red; font-size: 16px;")
            self.log_label.setVisible(True)
            self.close_log_button.setVisible(True)

    def startDrag(self, supportedActions):
        item = self.table_widget.currentItem()
        if item:
            mimeData = QMimeData()
            file_path = self.table_widget.item(self.table_widget.currentRow(), 1).text()
            url = QUrl.fromLocalFile(file_path)
            mimeData.setUrls([url])
            drag = QDrag(self)
            drag.setMimeData(mimeData)
            drag.exec_(Qt.CopyAction | Qt.MoveAction)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.play_pause_reference()
        super().keyPressEvent(event)

    def play_pause_reference(self):
        try:
            if self.currently_playing == self.reference_file_path:
                pygame.mixer.music.stop()
                self.currently_playing = None
                self.timer.stop()
                self.play_pause_button.setText("播放")
            else:
                pygame.mixer.music.load(self.reference_file_path)
                pygame.mixer.music.play()
                self.currently_playing = self.reference_file_path
                self.timer.start()
                pygame.mixer.music.set_endevent(pygame.USEREVENT)
                self.installEventFilter(self)
                self.play_pause_button.setText("暂停")
        except Exception as e:
            self.log_label.setText(f"错误: {str(e)}")
            self.log_label.setStyleSheet("background-color: red; font-size: 16px;")
            self.log_label.setVisible(True)
            self.close_log_button.setVisible(True)

    def on_play_button_click(self, file_path, button):
        try:
            if self.currently_playing == file_path:
                pygame.mixer.music.stop()
                self.currently_playing = None
                self.timer.stop()
                button.setText("播放")
            else:
                if self.currently_playing:
                    self.on_playback_complete()
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play()
                self.currently_playing = file_path
                self.timer.start()
                pygame.mixer.music.set_endevent(pygame.USEREVENT)
                self.installEventFilter(self)
                button.setText("暂停")
        except Exception as e:
            self.log_label.setText(f"错误: {str(e)}")
            self.log_label.setStyleSheet("background-color: red; font-size: 16px;")
            self.log_label.setVisible(True)
            self.close_log_button.setVisible(True)

    def eventFilter(self, source, event):
        if event.type() == pygame.USEREVENT:
            self.on_playback_complete()
        return super().eventFilter(source, event)

    def on_playback_complete(self):
        self.timer.stop()
        self.new_time = 0
        self.currently_playing = None
        self.progress_label.setText("进度: 00:00 / 00:00")
        self.play_pause_button.setText("播放")
        # self.progress_label.setText(f"进度: {self.format_time(0)} / {self.format_time(0)}")
        self.slider.setValue(int(0))
        for idx in range(self.table_widget.rowCount()):
            play_button = self.table_widget.cellWidget(idx, 3)
            if play_button:
                play_button.setText("播放")

    def set_position(self, position):
        try:
            if self.currently_playing:
                self.is_setting_position = True  # Set the flag
                total_time = librosa.get_duration(path=self.currently_playing)
                self.new_time = (position / 100) * total_time
                pygame.mixer.music.stop()
                pygame.mixer.music.load(self.currently_playing)
                pygame.mixer.music.play()
                pygame.mixer.music.set_pos(self.new_time)
                self.slider.setValue(position)
                self.progress_label.setText(f"进度: {self.format_time(self.new_time)} / {self.format_time(total_time)}")
                self.is_setting_position = False  # Reset the flag
                self.timer.start()  # Ensure the timer is running to update progress

                # Create a QTimer to forcefully synchronize after 500 milliseconds
                QTimer.singleShot(500, lambda: self.force_sync_position())
        except Exception as e:
            self.log_label.setText(f"错误: {str(e)}")
            self.log_label.setStyleSheet("background-color: red; font-size: 16px;")
            self.log_label.setVisible(True)
            self.close_log_button.setVisible(True)

    def force_sync_position(self):
        try:
            if self.currently_playing:
                total_time = librosa.get_duration(path=self.currently_playing)
                self.progress_label.setText(f"进度: {self.format_time(self.new_time)} / {self.format_time(total_time)}")
                self.slider.setValue(int((self.new_time / total_time) * 100))
        except Exception as e:
            self.log_label.setText(f"错误: {str(e)}")
            self.log_label.setStyleSheet("background-color: red; font-size: 16px;")
            self.log_label.setVisible(True)
            self.close_log_button.setVisible(True)

    def update_progress(self):
        try:
            if self.currently_playing and not self.is_setting_position:  # Check the flag
                current_time = pygame.mixer.music.get_pos() / 1000
                if current_time < 0:
                    current_time = 0
                total_time = librosa.get_duration(path=self.currently_playing)
                actual_time = self.new_time + current_time

                self.progress_label.setText(f"进度: {self.format_time(actual_time)} / {self.format_time(total_time)}")
                self.slider.setValue(int((actual_time / total_time) * 100))

                if actual_time >= total_time or current_time == 0:
                    self.on_playback_complete()
        except Exception as e:
            self.log_label.setText(f"错误: {str(e)}")
            self.log_label.setStyleSheet("background-color: red; font-size: 16px;")
            self.log_label.setVisible(True)
            self.close_log_button.setVisible(True)

    def slider_mouse_press_event(self, event: QMouseEvent):
        pos = event.pos()
        value = QStyle.sliderValueFromPosition(self.slider.minimum(), self.slider.maximum(), pos.x(), self.slider.width())
        self.slider.setValue(value)
        self.set_position(value)

    def format_time(self, seconds):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02}:{secs:02}"

    def dragEnterEvent(self, event: QDragEnterEvent):
        try:
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
                self.log_label.setText("释放鼠标以加载参考文件")
                self.log_label.setVisible(True)
                self.close_log_button.setVisible(True)
                self.overlay.setVisible(True)
                self.set_elements_enabled(False, exclude=[self.progress_bar, self.log_label, self.close_log_button])
        except Exception as e:
            self.log_label.setText(f"错误: {str(e)}")
            self.log_label.setStyleSheet("background-color: red; font-size: 16px;")
            self.log_label.setVisible(True)
            self.close_log_button.setVisible(True)

    def dragLeaveEvent(self, event):
        try:
            self.log_label.setVisible(False)
            self.close_log_button.setVisible(False)
            self.overlay.setVisible(False)
            self.set_elements_enabled(True)
        except Exception as e:
            self.log_label.setText(f"错误: {str(e)}")
            self.log_label.setStyleSheet("background-color: red; font-size: 16px;")
            self.log_label.setVisible(True)
            self.close_log_button.setVisible(True)

    def dropEvent(self, event: QDropEvent):
        try:
            self.log_label.setVisible(False)
            self.close_log_button.setVisible(False)
            self.overlay.setVisible(False)
            self.set_elements_enabled(True)
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.endswith(('.wav', '.mp3')):
                    self.process_reference_audio(file_path)
                    break
        except Exception as e:
            self.log_label.setText(f"错误: {str(e)}")
            self.log_label.setStyleSheet("background-color: red; font-size: 16px;")
            self.log_label.setVisible(True)
            self.close_log_button.setVisible(True)

    def set_elements_enabled(self, enabled, exclude=[]):
        elements = [
            self.reference_label, self.play_pause_button,
            self.table_widget, self.progress_label, self.slider
        ]
        for element in elements:
            if element not in exclude:
                element.setEnabled(enabled)

    def close_log(self):
        self.log_label.setVisible(False)
        self.close_log_button.setVisible(False)

    def show_context_menu(self, position):
        menu = QMenu()
        copy_action = QAction("复制文件路径", self)
        copy_action.triggered.connect(self.copy_file_path)
        menu.addAction(copy_action)
        menu.exec_(self.table_widget.viewport().mapToGlobal(position))

    def copy_file_path(self):
        item = self.table_widget.currentItem()
        if item:
            file_path = self.table_widget.item(self.table_widget.currentRow(), 1).text()
            destination_path, _ = QFileDialog.getSaveFileName(self, "保存文件", file_path)
            if destination_path:
                shutil.copy(file_path, destination_path)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 设置默认字体为支持中文的字体
    font = QFont("SimSun", 12)  # SimSun 是宋体的字体名称
    app.setFont(font)

    window = AudioManager()
    window.show()
    sys.exit(app.exec_())