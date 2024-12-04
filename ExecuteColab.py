# -*- coding: utf-8 -*-
"""Untitled22.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1W5AzjcB2x9z08WpKX9wVb7Za7vMYzxaS
"""

import os
import whisper
import librosa
import numpy as np
from sklearn.preprocessing import LabelEncoder
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv1D, MaxPooling1D, Flatten, Dense, Dropout
from sklearn.model_selection import train_test_split
from tqdm import tqdm
import soundfile as sf
import tensorflow as tf  # 추가
from gtts import gTTS
from pydub import AudioSegment

# Whisper 모델 불러오기
model = whisper.load_model("base")

# 디렉토리 경로
train_audio_folder = '/content/drive/MyDrive/audio_data/data/1.Training/data/D01/J01'
train_label_folder = '/content/drive/MyDrive/audio_data/data/1.Training/labelingdata/D01/J01'
output_audio_folder = '/content/drive/MyDrive/audio_data/predicted_audio'

# 출력 디렉토리 생성
if not os.path.exists(output_audio_folder):
    os.makedirs(output_audio_folder)

for i in range(1, 9):
    output_subfolder = os.path.join(output_audio_folder, f'S00000{i}')
    if not os.path.exists(output_subfolder):
        os.makedirs(output_subfolder)

def load_training_data(audio_folder_path, label_folder_path):
    train_audios = []
    train_labels = []

    for i in range(1, 9):
        audio_subfolder = os.path.join(audio_folder_path, f'S00000{i}')
        label_subfolder = os.path.join(label_folder_path, f'S00000{i}')

        audio_files = sorted([os.path.join(audio_subfolder, f) for f in os.listdir(audio_subfolder) if f.endswith('.wav')])
        label_files = sorted([os.path.join(label_subfolder, f) for f in os.listdir(label_subfolder) if f.endswith('.txt')])

        for audio_file, label_file in zip(audio_files, label_files):
            train_audios.append(audio_file)
            train_labels.append(label_file)

    return train_audios, train_labels

def spectral_subtraction(y, sr, noise_frames=6, alpha=1.0, beta=0.15):
    # Compute the STFT of the noisy signal
    D = librosa.stft(y)
    magnitude, phase = np.abs(D), np.angle(D)

    # Estimate the noise power spectrum
    noise_power = np.mean(magnitude[:, :noise_frames], axis=1, keepdims=True)

    # Subtract the noise power spectrum from the noisy power spectrum
    magnitude_clean = np.maximum(magnitude - alpha * noise_power, beta * noise_power)

    # Reconstruct the clean signal using the original phase
    D_clean = magnitude_clean * np.exp(1j * phase)
    y_clean = librosa.istft(D_clean)

    return y_clean

def calculate_cer(predicted, actual):
    # Initialize the matrix
    d = np.zeros((len(actual) + 1, len(predicted) + 1), dtype=np.uint8)

    # Fill the matrix
    for i in range(len(actual) + 1):
        for j in range(len(predicted) + 1):
            if i == 0:
                d[i][j] = j
            elif j == 0:
                d[i][j] = i
            elif actual[i - 1] == predicted[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + 1)

    # Calculate the CER
    distance = d[len(actual)][len(predicted)]
    cer = distance / len(actual)
    return cer, distance

def text_to_speech(text, output_file, speed=1.0):
    tts = gTTS(text, lang='ko')  # 한국어로 설정
    temp_file = "temp_tts.mp3"
    tts.save(temp_file)

    # 음성 속도를 변경
    sound = AudioSegment.from_file(temp_file)
    sound_with_changed_speed = sound._spawn(sound.raw_data, overrides={
         "frame_rate": int(sound.frame_rate * speed)
    }).set_frame_rate(sound.frame_rate)

    sound_with_changed_speed.export(output_file, format="mp3")

# Load training data
train_audio_files, train_label_files = load_training_data(train_audio_folder, train_label_folder)

# Process each training sample
for train_audio_file, train_label_file in zip(train_audio_files, train_label_files):
    # Load audio file
    y, sr = librosa.load(train_audio_file, sr=None)

    # Apply spectral subtraction for noise reduction
    y_denoised = spectral_subtraction(y, sr)

    # Save denoised audio to a temporary file
    temp_output_path = "temp_noisy_reduced.wav"
    sf.write(temp_output_path, y_denoised, sr)

    # Use Whisper model to transcribe audio file
    try:
        result = model.transcribe(temp_output_path)
        predicted_label = result["text"]
    except Exception as e:
        print(f"Failed to transcribe {train_audio_file}: {str(e)}")
        continue

    # Check if the predicted label is empty
    if not predicted_label.strip():
        print(f"No text predicted for {train_audio_file}. Skipping...")
        continue

    # Load true label from file
    with open(train_label_file, 'r') as file:
        true_label = file.read().strip()

    # Compute CER between predicted and true labels
    cer, distance = calculate_cer(predicted_label, true_label)

    # Only convert to speech if CER is less than 0.3

    if cer < 0.3:

        subfolder_name = os.path.basename(os.path.dirname(train_audio_file))
        output_subfolder = os.path.join(output_audio_folder, subfolder_name)
        if not os.path.exists(output_subfolder):
            os.makedirs(output_subfolder)


        output_speech_file = os.path.join(output_subfolder, os.path.basename(train_audio_file).replace('.wav', '_predicted.mp3'))
        text_to_speech(predicted_label, output_speech_file, speed=1.5)  # 속도를 1.5배로 설정
        print("Saved TTS output to:", output_speech_file)

    # Print results
    print("Train Audio File:", train_audio_file)
    print("Predicted label:", predicted_label)
    print("True label:", true_label)
    print("CER:", cer)
    print("Edit distance:", distance)
    print("---------------------------------------")

import os
import whisper
import librosa
import numpy as np
import soundfile as sf
from gtts import gTTS
from pydub import AudioSegment
from spleeter.separator import Separator
import matplotlib.pyplot as plt
import librosa.display

# Whisper 모델 불러오기
model = whisper.load_model("base")

# 파일 경로
audio_file_path = '/content/drive/MyDrive/01_08_724723_220730_0002_NV.wav'
output_audio_folder = '/content/drive/MyDrive/predicted_long'
if not os.path.exists(output_audio_folder):
    os.makedirs(output_audio_folder)

def spectral_subtraction(y, sr, noise_frames=6, alpha=1.0, beta=0.15):
    # Compute the STFT of the noisy signal
    D = librosa.stft(y)
    magnitude, phase = np.abs(D), np.angle(D)

    # Estimate the noise power spectrum
    noise_power = np.mean(magnitude[:, :noise_frames], axis=1, keepdims=True)

    # Subtract the noise power spectrum from the noisy power spectrum
    magnitude_clean = np.maximum(magnitude - alpha * noise_power, beta * noise_power)

    # Reconstruct the clean signal using the original phase
    D_clean = magnitude_clean * np.exp(1j * phase)
    y_clean = librosa.istft(D_clean)

    return y_clean

def text_to_speech(text, output_file, speed=1.0):
    tts = gTTS(text, lang='ko')  # 한국어로 설정
    temp_file = "temp_tts.mp3"
    tts.save(temp_file)

    # pydub를 사용하여 음성 속도를 변경
    sound = AudioSegment.from_file(temp_file)
    sound_with_changed_speed = sound._spawn(sound.raw_data, overrides={
         "frame_rate": int(sound.frame_rate * speed)
    }).set_frame_rate(sound.frame_rate)

    sound_with_changed_speed.export(output_file, format="mp3")


y, sr = librosa.load(audio_file_path, sr=None)


y_denoised = spectral_subtraction(y, sr)

# Save denoised audio to a temporary file and final output folder
temp_output_path = '/content/drive/MyDrive/temp_noisy_reduced.wav'

denoised_output_path = os.path.join(output_audio_folder, os.path.basename(audio_file_path).replace('.wav', '_denoised.wav'))
sf.write(temp_output_path, y_denoised, sr)
sf.write(denoised_output_path, y_denoised, sr)

# Separate vocals and accompaniment using Spleeter
separator = Separator('spleeter:2stems')  
separator.separate_to_file(audio_file_path, output_audio_folder)


vocals_path = os.path.join(output_audio_folder, os.path.basename(audio_file_path).replace('.wav', '') + '/vocals.wav')
accompaniment_path = os.path.join(output_audio_folder, os.path.basename(audio_file_path).replace('.wav', '') + '/accompaniment.wav')


y_vocals, sr_vocals = librosa.load(vocals_path, sr=None)
y_accompaniment, sr_accompaniment = librosa.load(accompaniment_path, sr=None)


try:
    result = model.transcribe(vocals_path)
    predicted_label = result["text"]
except Exception as e:
    print(f"Failed to transcribe {audio_file_path}: {str(e)}")


if not predicted_label.strip():
    print(f"No text predicted for {audio_file_path}. Exiting...")
else:
    
    output_speech_file = os.path.join(output_audio_folder, os.path.basename(audio_file_path).replace('.wav', '_predicted.mp3'))
    text_to_speech(predicted_label, output_speech_file, speed=1.5)  # 속도를 1.5배로 설정
    print("Saved TTS output to:", output_speech_file)

    # Print results
    print("Audio File:", audio_file_path)
    print("Predicted label:", predicted_label)
    print("---------------------------------------")
    print("Denoised audio saved to:", denoised_output_path)
    print("Vocals audio saved to:", vocals_path)
    print("Accompaniment audio saved to:", accompaniment_path)

# Original, separated vocals and separated accompaniment waveform plot
def plot_waveform(ax, file_path, title):
    y, sr = librosa.load(file_path, sr=None)
    librosa.display.waveshow(y, sr=sr, ax=ax)
    ax.set_title(title)

fig, axs = plt.subplots(3, 1, figsize=(14, 12))

plot_waveform(axs[0], audio_file_path, 'Original Audio Waveform')
plot_waveform(axs[1], vocals_path, 'Separated Vocals Waveform')
plot_waveform(axs[2], accompaniment_path, 'Separated Accompaniment Waveform')

plt.tight_layout()
plt.show()

# Frequency spectrum comparison
def plot_spectrogram(ax, file_path, title):
    y, sr = librosa.load(file_path, sr=None)
    D = librosa.amplitude_to_db(np.abs(librosa.stft(y)), ref=np.max)
    img = librosa.display.specshow(D, sr=sr, x_axis='time', y_axis='log', ax=ax)
    ax.set_title(title)
    fig.colorbar(img, ax=ax, format='%+2.0f dB')

fig, axs = plt.subplots(3, 1, figsize=(14, 12))

plot_spectrogram(axs[0], audio_file_path, 'Original Audio Spectrogram')
plot_spectrogram(axs[1], vocals_path, 'Separated Vocals Spectrogram')
plot_spectrogram(axs[2], accompaniment_path, 'Separated Accompaniment Spectrogram')

plt.tight_layout()
plt.show()


## starhuber모델 사용시 
# checkpoint 파일 및 yaml 파일을 받아 주어진 컴퓨터 환경에 세팅 후 사용하실수 있습니다.


# checkpoint 파일을 로드

import os
os.chdir('/content/drive/MyDrive/ColabNotebooks/s3prl_root')

import torch

def load_checkpoint(ckpt_path):
    # 체크포인트 로드
    checkpoint = torch.load(ckpt_path, map_location=torch.device('cpu'))  

    # 모든 키 출력
    for key in checkpoint.keys():
        print(f"Key: {key}, Type: {type(checkpoint[key])}")

    return checkpoint

# 예시 실행
ckpt_path = "/content/drive/MyDrive/ColabNotebooks/s3prl_root/results/pretrain/STaRHuBERT-S.ckpt"
checkpoint = load_checkpoint(ckpt_path)

!python3 preprocess/generate_len_for_bucket.py \
  -i "/content/drive/MyDrive/ColabNotebooks/s3prl/db/LibriSpeech" \
  -a ".flac" \
  -n "len_for_bucket" \
  --n_jobs 4