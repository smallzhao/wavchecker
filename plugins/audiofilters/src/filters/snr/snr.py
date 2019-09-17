#coding=utf-8

import os
import math
import struct
import webrtcvad
from functools import reduce
from filters.base import Filter

import logging
logger = logging.getLogger(__name__)

FRAME_DURATION = 0.01
DEFAULT_PARAMS_OF_WEBRTC = {'Min_Silence': 0.1, 'Min_Speech': 0.05}


class SNR(Filter):
    filter_type = 'snr'

    def check(self, wavobj):
        logger.info("Start check snr {}".format(wavobj.path))
        sound_name = os.path.normpath(wavobj.path)
        assert os.path.exists(sound_name), 'Source sound file does not exist!'
        if not wavobj.data:
            print(sound_name)
            return ''
        bounds_of_speech = list(detect_spoken_frames_with_webrtc(wavobj.data, wavobj.sample_rate))  # 端点检测
        # print(bounds_of_speech)
        snr = calculate_SNR(wavobj.data, wavobj.sample_rate, bounds_of_speech)  # 信噪比计算
        logger.info("Check snr over")
        return {self.filter_type: snr}


#对有效音检测结果做平滑
def smooth_spoken_frames(spoken_frames, min_frames_in_silence, min_frames_in_speech):
    n_frames = len(spoken_frames)
    prev_speech_pos = -1
    for frame_ind in range(n_frames):
        if spoken_frames[frame_ind]:
            if prev_speech_pos >= 0:
                if (prev_speech_pos + 1) < frame_ind:
                    spoken_frames[(prev_speech_pos + 1):frame_ind] = [True] * (frame_ind - prev_speech_pos - 1)
            prev_speech_pos = frame_ind
        else:
            if prev_speech_pos >= 0:
                if (frame_ind - prev_speech_pos) > min_frames_in_silence:
                    prev_speech_pos = -1
    # if prev_speech_pos >= 0:
        # if (prev_speech_pos + 1) < n_frames:
            # spoken_frames[(prev_speech_pos + 1):n_frames] = [True] * (n_frames - prev_speech_pos - 1)
    speech_start = -1
    for frame_ind in range(n_frames):
        if spoken_frames[frame_ind]:
            if speech_start < 0:
                speech_start = frame_ind
        else:
            if speech_start >= 0:
                if (frame_ind - speech_start) >= min_frames_in_speech:
                    yield (speech_start, frame_ind)
                speech_start = -1
    # if speech_start >= 0:
        # if (n_frames - speech_start) >= min_frames_in_speech:
            # yield (speech_start, n_frames)

#使用webrtc算法检测有效帧
def detect_spoken_frames_with_webrtc(sound_data, sampling_frequency, params=DEFAULT_PARAMS_OF_WEBRTC):
    assert sampling_frequency in (8000, 16000, 32000, 48000), 'Sampling frequency is inadmissible!'
    n_data = len(sound_data)
    #print(n_data)
    assert (n_data > 0) and ((n_data % 2) == 0), 'Sound data are wrong!'
    # 分帧 10ms
    frame_size = int(round(FRAME_DURATION * float(sampling_frequency)))
    sound_duration = n_data / (2.0 * float(sampling_frequency))
    n_frames = int(round(n_data / (2.0 * float(frame_size))))
    #print(n_frames)
    spoken_frames = [False] * n_frames
    buffer_start = 0
    vad = webrtcvad.Vad(mode=3)
    for frame_ind in range(n_frames):
        if (buffer_start + frame_size * 2) <= n_data:
            if sampling_frequency == 22050:
                if vad.is_speech(sound_data[buffer_start:(buffer_start + frame_size * 2)],
                                sample_rate=16000):
                    spoken_frames[frame_ind] = True
            else:
                if vad.is_speech(sound_data[buffer_start:(buffer_start + frame_size * 2)],
                                sample_rate=sampling_frequency):
                    spoken_frames[frame_ind] = True
        buffer_start += (frame_size * 2)
    del vad
    min_frames_in_silence = int(round(params['Min_Silence'] * float(sampling_frequency) / frame_size))
    if min_frames_in_silence < 0:
        min_frames_in_silence = 0
    min_frames_in_speech = int(round(params['Min_Speech'] * float(sampling_frequency) / frame_size))
    if min_frames_in_speech < 0:
        min_frames_in_speech = 0
    for cur_speech_frame in smooth_spoken_frames(spoken_frames, min_frames_in_silence, min_frames_in_speech):
        init_time = cur_speech_frame[0] * FRAME_DURATION
        fin_time = cur_speech_frame[1] * FRAME_DURATION
        if fin_time > sound_duration:
            fin_time = sound_duration
        yield (init_time, fin_time)
    #yield (fin_time, sound_duration)
    del spoken_frames

#计算能量
def calculate_energy(sound_data):
    n_data = len(sound_data)
    assert (n_data > 0) and ((n_data % 2) == 0), 'Sound data are wrong!'
    n_samples = int(n_data / 2)
    total_energy = reduce(
        lambda energy, cur_sample: energy + cur_sample * cur_sample,
        map(
            lambda sample_ind: float(struct.unpack('<h', sound_data[(sample_ind * 2):(sample_ind * 2 + 2)])[0]),
            range(n_samples)
        ),
        0.0
    )
    return total_energy, n_samples

#计算信噪比
def calculate_SNR(sound_data, sampling_frequency, bounds_of_spoken_frames):
    n_data = len(sound_data)
    assert (n_data > 0) and ((n_data % 2) == 0), 'Sound data are wrong!'
    if len(bounds_of_spoken_frames) == 0:
        return None
    n_samples = int(n_data / 2)
    speech_energy = 0.0
    number_of_speech_samples = 0
    noise_energy = 0.0
    number_of_noise_samples = 0
    prev_speech_end = 0
    for bounds_of_cur_frame in bounds_of_spoken_frames:
        cur_speech_start = int(round(bounds_of_cur_frame[0] * sampling_frequency))
        cur_speech_end = int(round(bounds_of_cur_frame[1] * sampling_frequency))
        if cur_speech_start >= n_samples:
            break
        if cur_speech_end > n_samples:
            cur_speech_end = n_samples
        if cur_speech_start > prev_speech_end:
            frame_energy, samples_in_frame = calculate_energy(sound_data[(prev_speech_end * 2):(cur_speech_start * 2)])
            noise_energy += frame_energy
            number_of_noise_samples += samples_in_frame
        if cur_speech_end > cur_speech_start:
            frame_energy, samples_in_frame = calculate_energy(sound_data[(cur_speech_start * 2):(cur_speech_end * 2)])
            speech_energy += frame_energy
            number_of_speech_samples += samples_in_frame
        prev_speech_end = cur_speech_end
    if n_samples > prev_speech_end:
        frame_energy, samples_in_frame = calculate_energy(sound_data[(prev_speech_end * 2):(n_samples * 2)])
        noise_energy += frame_energy
        number_of_noise_samples += samples_in_frame
    if (number_of_noise_samples == 0) or (number_of_speech_samples == 0):
        return None
    speech_energy = speech_energy / float(number_of_speech_samples)
    noise_energy = noise_energy / float(number_of_noise_samples)
    return 10.0 * math.log10(speech_energy / noise_energy)
