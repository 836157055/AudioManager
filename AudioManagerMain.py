import sys
import os
import pygame
import librosa
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QLabel, QFormLayout, QLineEdit, QDialog, QProgressBar, QHBoxLayout, QListWidget, QListWidgetItem, QStackedLayout, QSpinBox
from PyQt5.QtCore import Qt, QTimer, QMimeData, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QDragEnterEvent, QDropEvent

from extract_features import extract_features
from calculate_similarity import calculate_similarity
from SettingsDialog import SettingsDialog
from AudioProcessor import AudioProcessor

class AudioManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio Library Manager")
        self.setGeometry(100, 100, 1000, 800)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        self.reference_control_layout = QHBoxLayout()
        self.reference_label = QLabel("Reference Audio: None")
        self.reference_control_layout.addWidget(self.reference_label)
        self.play_pause_button = QPushButton("Play/Pause")
        self.play_pause_button.clicked.connect(self.play_pause_reference)
        self.reference_control_layout.addWidget(self.play_pause_button)
        self.layout.addLayout(self.reference_control_layout)

        self.upload_button = QPushButton("Upload Reference Audio")
        self.upload_button.clicked.connect(self.upload_reference_audio)
        self.layout.addWidget(self.upload_button)

        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.open_settings)
        self.layout.addWidget(self.settings_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.layout.addWidget(self.progress_bar)

        self.log_label = QLabel("Release mouse to load reference file")
        self.log_label.setAlignment(Qt.AlignCenter)
        self.log_label.setStyleSheet("background-color: yellow; font-size: 16px;")
        self.log_label.setVisible(False)
        self.layout.addWidget(self.log_label)

        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(4)
        self.table_widget.setHorizontalHeaderLabels(["File Name", "Path", "Similarity", "Play"])
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Make the table read-only
        self.layout.addWidget(self.table_widget)

        self.progress_label = QLabel("Progress: 00:00 / 00:00")
        self.layout.addWidget(self.progress_label)

        self.figure, self.ax = plt.subplots(figsize=(10, 4))  # Adjust the height of the waveform
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)

        self.overlay = QLabel(self.central_widget)
        self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 128);")
        self.overlay.setVisible(False)
        self.overlay.setGeometry(0, 0, self.width(), self.height())

        self.refresh_rate_spinbox = QSpinBox()
        self.refresh_rate_spinbox.setRange(100, 5000)
        self.refresh_rate_spinbox.setValue(500)
        self.refresh_rate_spinbox.valueChanged.connect(self.update_refresh_rate)
        self.layout.addWidget(QLabel("Waveform Refresh Rate (ms):"))
        self.layout.addWidget(self.refresh_rate_spinbox)

        pygame.mixer.init()
        self.currently_playing = None
        self.timer = QTimer(self)
        self.timer.setInterval(self.refresh_rate_spinbox.value())
        self.timer.timeout.connect(self.update_progress)
        self.similar_files = []

        self.load_settings()

        self.canvas.mpl_connect('button_press_event', self.on_waveform_click)

        self.setAcceptDrops(True)

    def load_settings(self):
        self.audio_library_paths = []
        if os.path.exists("config.txt"):
            with open("config.txt", "r") as file:
                self.audio_library_paths = [line.strip() for line in file.readlines()]

    def save_settings(self):
        with open("config.txt", "w") as file:
            for path in self.audio_library_paths:
                file.write(f"{path}\n")

    def import_settings(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Settings", "", "Config Files (*.txt)")
        if file_path:
            with open(file_path, "r") as file:
                self.audio_library_paths = [line.strip() for line in file.readlines()]
            self.save_settings()

    def export_settings(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Settings", "", "Config Files (*.txt)")
        if file_path:
            with open(file_path, "w") as file:
                for path in self.audio_library_paths:
                    file.write(f"{path}\n")

    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec_():
            self.audio_library_paths = [dialog.audio_library_paths_list.item(i).text() for i in range(dialog.audio_library_paths_list.count())]
            self.save_settings()

    def upload_reference_audio(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Reference Audio", "", "Audio Files (*.wav *.mp3)")
        if file_path:
            self.process_reference_audio(file_path)

    def process_reference_audio(self, file_path):
        self.reference_label.setText(f"Reference Audio: {os.path.basename(file_path)}")
        self.reference_file_path = file_path
        self.process_audio(file_path)

    def process_audio(self, file_path):
        self.progress_bar.setVisible(True)
        self.log_label.setText("Loading reference audio...")
        self.log_label.setVisible(True)
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

    def update_progress_bar(self, value, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(value)

    def display_results(self, similar_files):
        self.similar_files = similar_files
        self.table_widget.setRowCount(0)
        for idx, (file, path, similarity) in enumerate(self.similar_files):
            self.table_widget.insertRow(idx)
            self.table_widget.setItem(idx, 0, QTableWidgetItem(file))
            self.table_widget.setItem(idx, 1, QTableWidgetItem(path))
            self.table_widget.setItem(idx, 2, QTableWidgetItem(str(similarity)))
            play_button = QPushButton("Play/Pause")
            play_button.clicked.connect(lambda _, p=path: self.on_play_button_click(p))
            self.table_widget.setCellWidget(idx, 3, play_button)
        self.progress_bar.setVisible(False)
        self.log_label.setVisible(False)
        self.overlay.setVisible(False)
        self.set_elements_enabled(True)
        self.thread.quit()

    def play_pause_reference(self):
        if self.currently_playing == self.reference_file_path:
            pygame.mixer.music.stop()
            self.currently_playing = None
            self.timer.stop()
        else:
            pygame.mixer.music.load(self.reference_file_path)
            pygame.mixer.music.play()
            self.currently_playing = self.reference_file_path
            self.timer.start()
            self.plot_waveform(self.reference_file_path)
            pygame.mixer.music.set_endevent(pygame.USEREVENT)
            self.installEventFilter(self)

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

    def update_progress(self):
        if self.currently_playing:
            current_time = pygame.mixer.music.get_pos() / 1000
            total_time = librosa.get_duration(path=self.currently_playing)
            self.progress_label.setText(f"Progress: {self.format_time(current_time)} / {self.format_time(total_time)}")
            self.plot_waveform(self.currently_playing, current_time)

    def plot_waveform(self, file_path, current_time=0):
        y, sr = librosa.load(file_path, sr=None, mono=False)
        total_time = librosa.get_duration(y=y, sr=sr)
        current_samples = int(current_time * sr)
        bit_rate = 16  # Assuming 16-bit audio

        # Downsample for performance
        downsample_factor = max(1, len(y) // 10000)
        y = y[::downsample_factor]
        sr = sr // downsample_factor

        self.ax.clear()
        if y.ndim == 1:
            self.ax.plot(np.arange(len(y)) / sr, y, color="gray")
            if current_samples > 0:
                self.ax.plot(np.arange(current_samples) / sr, y[:current_samples], color="blue")
        else:
            self.ax.plot(np.arange(len(y[0])) / sr, y[0], color="gray", label="Left Channel")
            self.ax.plot(np.arange(len(y[1])) / sr, y[1], color="red", label="Right Channel")
            if current_samples > 0:
                self.ax.plot(np.arange(current_samples) / sr, y[0][:current_samples], color="blue")
                self.ax.plot(np.arange(current_samples) / sr, y[1][:current_samples], color="orange")
            self.ax.legend()

        self.ax.set_title(f"Waveform (Sample Rate: {sr} Hz, Bit Rate: {bit_rate} bits, Channels: {'Mono' if y.ndim == 1 else 'Stereo'})")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Amplitude")
        self.ax.text(0.95, 0.01, f"{self.format_time(current_time)} / {self.format_time(total_time)}",
                     verticalalignment='bottom', horizontalalignment='right',
                     transform=self.ax.transAxes, color='green', fontsize=12)
        self.canvas.draw()

    def on_waveform_click(self, event):
        if self.currently_playing:
            click_time = event.xdata
            if click_time is not None:
                pygame.mixer.music.play(0, click_time)
                self.update_progress()

    def format_time(self, seconds):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02}:{secs:02}"

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.log_label.setText("Release mouse to load reference file")
            self.log_label.setVisible(True)
            self.overlay.setVisible(True)
            self.set_elements_enabled(False, exclude=[self.progress_bar, self.log_label])

    def dragLeaveEvent(self, event):
        self.log_label.setVisible(False)
        self.overlay.setVisible(False)
        self.set_elements_enabled(True)

    def dropEvent(self, event: QDropEvent):
        self.log_label.setVisible(False)
        self.overlay.setVisible(False)
        self.set_elements_enabled(True)
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith(('.wav', '.mp3')):
                self.process_reference_audio(file_path)
                break

    def set_elements_enabled(self, enabled, exclude=[]):
        elements = [
            self.reference_label, self.play_pause_button, self.upload_button,
            self.settings_button, self.table_widget, self.progress_label, self.canvas
        ]
        for element in elements:
            if element not in exclude:
                element.setEnabled(enabled)

    def update_refresh_rate(self):
        self.timer.setInterval(self.refresh_rate_spinbox.value())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AudioManager()
    window.show()
    sys.exit(app.exec_())