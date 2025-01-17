import os
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal
from extract_features import extract_features
from calculate_similarity import calculate_similarity

class AudioProcessor(QObject):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)  # Add this line to define the error signal

    def __init__(self, paths, ref_mfcc, cache):
        super().__init__()
        self.paths = paths
        self.ref_mfcc = ref_mfcc
        self.cache = cache

    def run(self):
        similar_files = []
        total_files = sum(len(files) for path in self.paths for _, _, files in os.walk(path) if any(file.endswith(".wav") for file in files))
        processed_files = 0
        for path in self.paths:
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith(".wav"):
                        audio_path = os.path.join(root, file)
                        try:
                            if audio_path in self.cache:
                                lib_mfcc = np.array(self.cache[audio_path])
                            else:
                                lib_mfcc = extract_features(audio_path)
                                self.cache[audio_path] = lib_mfcc.tolist()
                            similarity = calculate_similarity(self.ref_mfcc, lib_mfcc)
                            similar_files.append((file, audio_path, similarity))
                        except Exception as e:
                            self.error.emit(f"Error processing {audio_path}: {e}")  # Emit error signal
                        processed_files += 1
                        self.progress.emit(processed_files, total_files)
        similar_files.sort(key=lambda x: x[2])
        self.finished.emit(similar_files)