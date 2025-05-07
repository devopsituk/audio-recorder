
import PySimpleGUI as sg
import sounddevice as sd
import soundfile as sf
import threading
import datetime
import os
import time
import numpy as np
import subprocess
from pathlib import Path

save_dir = Path.home() / "Documents" / "AudioRecorder"
save_dir.mkdir(parents=True, exist_ok=True)

samplerate = 44100
channels = 2
loop_duration = 3600

is_recording = False
start_time = None
mic_data = []
sys_data = []

def get_loopback_device():
    for device in sd.query_devices():
        if device['hostapi'] == 0 and 'loopback' in device['name'].lower():
            return device['index']
    return None

def record_sources(filename):
    global is_recording, mic_data, sys_data

    is_recording = True
    mic_data = []
    sys_data = []

    loopback_index = get_loopback_device()
    if loopback_index is None:
        sg.popup_error("⚠️ Устройство loopback не найдено. Включи 'Stereo Mix' или обнови драйверы.")
        is_recording = False
        return

    def callback_mic(indata, frames, time, status):
        if is_recording:
            mic_data.append(indata.copy())

    def callback_sys(indata, frames, time, status):
        if is_recording:
            sys_data.append(indata.copy())

    mic_stream = sd.InputStream(samplerate=samplerate, channels=channels, callback=callback_mic)
    sys_stream = sd.InputStream(samplerate=samplerate, channels=channels, callback=callback_sys, device=loopback_index)

    with mic_stream, sys_stream:
        while is_recording:
            time.sleep(0.1)

    mic_np = np.concatenate(mic_data, axis=0)
    sys_np = np.concatenate(sys_data, axis=0)
    mix = mic_np + sys_np
    mix = np.clip(mix, -1.0, 1.0)

    sf.write(filename, mix, samplerate)

def format_time(seconds):
    return time.strftime('%H:%M:%S', time.gmtime(seconds))

layout = [
    [sg.Text("Audio Recorder", font=("Helvetica", 16))],
    [sg.Text("⏱ 00:00:00", key='-TIMER-', size=(10,1))],
    [sg.Button("▶️ Старт", key="-START-", size=(10, 1)), sg.Button("⏹ Стоп", key="-STOP-", size=(10, 1))],
    [sg.Button("📁 Открыть папку", key="-OPEN-", size=(22, 1))],
    [sg.Exit("Выход")]
]

window = sg.Window("Запись микрофона + звука", layout, keep_on_top=True)

timer_running = False
thread = None

while True:
    event, values = window.read(timeout=1000)

    if event in (sg.WIN_CLOSED, "Выход"):
        is_recording = False
        break

    if event == "-START-" and not is_recording:
        now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = save_dir / f"recording_{now}.wav"
        thread = threading.Thread(target=record_sources, args=(filename,), daemon=True)
        thread.start()
        start_time = time.time()
        timer_running = True

    if event == "-STOP-" and is_recording:
        is_recording = False
        timer_running = False

    if event == "-OPEN-":
        subprocess.Popen(f'explorer "{save_dir}"')

    if timer_running and start_time:
        elapsed = int(time.time() - start_time)
        window["-TIMER-"].update(f"⏱ {format_time(elapsed)}")

window.close()
