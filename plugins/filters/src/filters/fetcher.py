import contextlib
import wave
import os
import array
import sys
import re
import json
import subprocess
import collections
import configparser
import getopt
from pydub import AudioSegment
from collections import defaultdict

import webrtcvad

import logging
logger = logging.getLogger(__name__)


class Frame():
    """Represents a "frame" of audio data."""
    def __init__(self, bytes, timestamp, duration):
        self.bytes = bytes
        self.timestamp = timestamp
        self.duration = duration


class Wav():
    def __init__(self, path, task_id, group, audio, sample_rate, sample_width):
        self.path = path
        self.task_id = task_id
        self.group = group
        self.data = audio
        self.sample_rate = sample_rate
        self.sample_width = sample_width
        self.labels = {}


class Fetcher():
    vadlevel = 3
    vad_frame_duration = 30
    vad_padding_duration = 300

    parter = ('.wav', '.WAV')

    def __init__(self, taskinfos):
        self.taskinfos = taskinfos

    def transform(self, src, dst):
        cmd_line = u'ffmpeg/bin/ffmpeg.exe -i "{src}" -acodec pcm_s16le -ar 16k -ac 1 -y "{dst}"'.format(src=src, dst=dst)
        try:
            subprocess.check_call(cmd_line, shell=False, stderr=open(os.devnull, 'w'))
        except Exception as e:
            print(e)
            logger.error("Can not transform audio {}".format(src))
            return '', '', '', ''
        audio, sample_rate, sample_width, num_channels = self.read_wave(dst)
        os.remove(dst)
        logger.info("Transform wav {} to the correct format".format(src))
        return audio, sample_rate, sample_width, num_channels

    def fetch_wavinfo(self, file):
        task_id, group, filepath = file
        audio, sample_rate, sample_width, num_channels = self.read_wave(filepath)
        if not (num_channels == 1 and sample_width == 2 and sample_rate in (8000, 16000, 32000, 48000)):
            dst = os.path.join(os.path.dirname(filepath), 'result.wav')
            audio, sample_rate, sample_width, num_channels = self.transform(filepath, dst)
        return Wav(filepath, task_id, group, audio, sample_rate, sample_width)

    def read_wave(self, path):
        try:
            wav = AudioSegment.from_file(path)
            pcm_data, sample_rate, sample_width, num_channels = wav._data, wav.frame_rate, wav.sample_width, wav.channels
        except Exception as e:
            logger.error("the file is damage {}".format(path))
            pcm_data, sample_rate, sample_width, num_channels = '', '', '', ''
        return pcm_data, sample_rate, sample_width, num_channels

    # def write_wave(self, path, audio, sample_rate):
    #     """Writes a .wav file.
    #
    #     Takes path, PCM audio data, and sample rate.
    #     """
    #     with contextlib.closing(wave.open(path, 'wb')) as wf:
    #         wf.setnchannels(1)
    #         wf.setsampwidth(2)
    #         wf.setframerate(sample_rate)
    #         wf.writeframes(audio)
    #     logger.info("Writes wav {} successfully".format(path))

    # def frame_generator(self, frame_duration_ms, audio, sample_rate, sample_width):
    #     """Generates audio frames from PCM audio data.
    #
    #     Takes the desired frame duration in milliseconds, the PCM data, and
    #     the sample rate.
    #
    #     Yields Frames of the requested duration.
    #     """
    #     n = int(sample_rate * (frame_duration_ms / 1000.0) * sample_width)
    #     offset = 0
    #     timestamp = 0.0
    #
    #     duration = (float(n) / sample_rate) / float(sample_width)
    #     while offset + n < len(audio):
    #         yield Frame(audio[offset:offset + n], timestamp, duration)
    #         timestamp += duration
    #         offset += n

    def fetch(self, root):
        def get_files(task_id, group, root):
            files = []
            for path, dirs, filenames in os.walk(os.path.join(root, task_id, group)):
                for filename in filenames:
                    name, ext = os.path.splitext(filename)
                    if ext in self.parter:
                        files.append((task_id, group, os.path.join(path, filename)))
            return files

        if self.taskinfos:
            files = []
            for task_id, group in self.taskinfos:
                files.extend(get_files(task_id, group, root))
        else:
            files = get_files('', '', root)
        return files