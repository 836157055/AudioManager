import sys
import os
import pygame
import librosa
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QLabel, QSlider, QHBoxLayout, QLineEdit, QDialog, QFormLayout
from PyQt5.QtCore import Qt, QTimer, QMimeData
from PyQt5.QtGui import QDrag

from extract_features import extract_features
from calculate_similarity import calculate_similarity

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.layout = QFormLayout()
        self.audio_library_path_input = QLineEdit()
        self.layout.addRow("Audio Library Path:", self.audio_library_path_input)
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_settings)
        self.layout.addWidget(self.save_button)
        self.setLayout(self.layout)
        self.load_settings()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(0)
        self.slider.sliderMoved.connect(self.set_position)
        self.layout.addWidget(self.slider)

    def load_settings(self):
        if os.path.exists("config.txt"):
            with open("config.txt", "r") as file:
                path = file.readline().strip()
                self.audio_library_path_input.setText(path)

    def save_settings(self):
        path = self.audio_library_path_input.text()
        with open("config.txt", "w") as file:
            file.write(path)
        self.accept()

class AudioManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio Library Manager")
        self.setGeometry(100, 100, 1000, 800)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        self.drag_area = QLabel("Drag Audio Files Here")
        self.drag_area.setAlignment(Qt.AlignCenter)
        self.drag_area.setStyleSheet("border: 2px dashed #aaa;")
        self.layout.addWidget(self.drag_area)

        self.upload_button = QPushButton("Upload Reference Audio")
        self.upload_button.clicked.connect(self.upload_reference_audio)
        self.layout.addWidget(self.upload_button)

        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.open_settings)
        self.layout.addWidget(self.settings_button)

        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(4)
        self.table_widget.setHorizontalHeaderLabels(["File Name", "Path", "Similarity", "Play"])
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.layout.addWidget(self.table_widget)

        self.progress_label = QLabel("Progress: 00:00 / 00:00")
        self.layout.addWidget(self.progress_label)

        self.figure, self.ax = plt.subplots(figsize=(10, 2))  # Adjust the height of the waveform
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)

        pygame.mixer.init()
        self.currently_playing = None
        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.update_progress)
        self.similar_files = []

        self.load_settings()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(0)
        self.slider.sliderMoved.connect(self.set_position)
        self.layout.addWidget(self.slider)

        self.canvas.mpl_connect('button_press_event', self.on_waveform_click)

    def load_settings(self):
        if os.path.exists("config.txt"):
            with open("config.txt", "r") as file:
                self.audio_library_path = file.readline().strip()
        else:
            self.audio_library_path = ""

    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec_():
            self.audio_library_path = dialog.audio_library_path_input.text()

    def upload_reference_audio(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Reference Audio", "", "Audio Files (*.wav *.mp3)")
        if file_path:
            self.process_audio(file_path)

    def process_audio(self, file_path):
        ref_mfcc = extract_features(file_path)
        self.similar_files = []
        for root, dirs, files in os.walk(self.audio_library_path):
            for file in files:
                if file.endswith(".wav"):
                    audio_path = os.path.join(root, file)
                    lib_mfcc = extract_features(audio_path)
                    similarity = calculate_similarity(ref_mfcc, lib_mfcc)
                    self.similar_files.append((file, audio_path, similarity))
        self.similar_files.sort(key=lambda x: x[2])
        self.display_results()

    def display_results(self):
        self.table_widget.setRowCount(0)
        for idx, (file, path, similarity) in enumerate(self.similar_files):
            self.table_widget.insertRow(idx)
            self.table_widget.setItem(idx, 0, QTableWidgetItem(file))
            self.table_widget.setItem(idx, 1, QTableWidgetItem(path))
            self.table_widget.setItem(idx, 2, QTableWidgetItem(str(similarity)))
            play_button = QPushButton("Play/Pause")
            play_button.clicked.connect(lambda _, p=path: self.on_play_button_click(p))
            self.table_widget.setCellWidget(idx, 3, play_button)

    def on_play_button_click(self, file_path):
        if self.currently_playing == file_path:
            pygame.mixer.music.stop()
            self.currently_playing = None
            self.timer.stop()
        else:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            self.currently_playing = file_path
            self.timer.start()
            self.plot_waveform(file_path)
            pygame.mixer.music.set_endevent(pygame.USEREVENT)
            self.installEventFilter(self)

    def eventFilter(self, source, event):
        if event.type() == pygame.USEREVENT:
            self.on_playback_complete()
        return super().eventFilter(source, event)

    def on_playback_complete(self):
        self.timer.stop()
        self.currently_playing = None
        self.progress_label.setText("Progress: 00:00 / 00:00")

    def set_position(self, position):
        if self.currently_playing:
            total_time = librosa.get_duration(path=self.currently_playing)
            pos = int((position / 100) * total_time * 1000)
            pygame.mixer.music.play(0, pos / 1000)
            self.update_progress()  # 更新进度显示
            self.plot_waveform(self.currently_playing, pos / 1000)  # 更新波形图

    def update_progress(self):
        if self.currently_playing:
            current_time = pygame.mixer.music.get_pos() / 1000
            total_time = librosa.get_duration(path=self.currently_playing)
            progress = int((current_time / total_time) * 100)
            self.progress_label.setText(f"Progress: {self.format_time(current_time)} / {self.format_time(total_time)}")
            self.slider.setValue(progress)
            self.plot_waveform(self.currently_playing, current_time)

    def plot_waveform(self, file_path, current_time=0):
        y, sr = librosa.load(file_path)
        total_time = librosa.get_duration(y=y, sr=sr)
        current_samples = int(current_time * sr)


        self.ax.clear()
        self.ax.plot(np.arange(len(y)) / sr, y, color="gray")
        if current_samples > 0:
            self.ax.plot(np.arange(current_samples) / sr, y[:current_samples], color="blue")
        self.ax.set_title("Waveform")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Amplitude")
        self.canvas.draw()  # 在这里更新画布

        def on_click(event):
            if event.inaxes == self.ax:
                click_time = event.xdata
                position = (click_time / total_time) * 100
                self.set_position(position)

        self.canvas.mpl_connect('button_press_event', on_click)

    def format_time(self, seconds):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02}:{secs:02}"

    def plot_waveform(self, file_path, current_time=0):
        y, sr = librosa.load(file_path)
        total_time = librosa.get_duration(y=y, sr=sr)
        current_samples = int(current_time * sr)
        self.ax.clear()
        self.ax.plot(np.arange(len(y)) / sr, y, color="gray")
        self.ax.plot(np.arange(current_samples) / sr, y[:current_samples], color="blue")
        self.ax.set_title("Waveform")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Amplitude")
        self.ax.text(0.95, 0.01, f"{self.format_time(current_time)} / {self.format_time(total_time)}",
                     verticalalignment='bottom', horizontalalignment='right',
                     transform=self.ax.transAxes, color='green', fontsize=12)
        self.canvas.draw()

    def on_waveform_click(self, event):
        if self.currently_playing:
            y, sr = librosa.load(self.currently_playing)
            total_time = librosa.get_duration(y=y, sr=sr)
            click_time = event.xdata
            if click_time is not None:
                pygame.mixer.music.play(0, click_time)
                self.update_progress()

    def format_time(self, seconds):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02}:{secs:02}"

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.startDrag(event)

    def startDrag(self, event):
        index = self.table_widget.indexAt(event.pos())
        if index.isValid():
            path = self.table_widget.item(index.row(), 1).text()
            mimeData = QMimeData()
            mimeData.setUrls([Qt.QUrl.fromLocalFile(path)])
            drag = QDrag(self)
            drag.setMimeData(mimeData)
            drag.exec_(Qt.CopyAction | Qt.MoveAction)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AudioManager()
    window.show()
    sys.exit(app.exec_())