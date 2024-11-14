import librosa
import numpy as np
from pydub import AudioSegment

def extract_features(file_path, n_mfcc=20, max_pad_len=400):
    audio = AudioSegment.from_file(file_path)
    y = np.array(audio.get_array_of_samples(), dtype=np.float32)  # Convert to float32
    sr = audio.frame_rate
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)

    # Pad or truncate MFCC features to have the same shape
    if mfccs.shape[1] < max_pad_len:
        pad_width = max_pad_len - mfccs.shape[1]
        mfccs = np.pad(mfccs, pad_width=((0, 0), (0, pad_width)), mode='constant')
    else:
        mfccs = mfccs[:, :max_pad_len]

    return mfccs