# -*- coding: utf-8 -*-
import numpy as np
import wave
import os
import math
import configparser
import platform

import logging
logger = logging.getLogger(__name__)

model_path = os.path.dirname(os.path.abspath(__file__))

def get_configure_info(info_path):
    conf = dict()
    cp = configparser.ConfigParser()
    cp.read(info_path, encoding='utf-8')
    try:
        conf = {
            'db_threshold': cp.get('db', 'db_threshold'),
            'sox_low_threshold': cp.get('low', 'sox_low_threshold'),
            'sox_high_threshold': cp.get('high', 'sox_high_threshold'),
            'sox_echo_threshold': cp.get('echo', 'sox_echo_threshold'),
            'mean_low_threshold1': cp.get('low', 'mean_low_threshold1'),
            'mean_low_threshold2': cp.get('low', 'mean_low_threshold2'),
            'mean_high_threshold1': cp.get('high', 'mean_high_threshold1'),
            'mean_high_threshold2': cp.get('high', 'mean_high_threshold2'),
            'mean_echo_threshold': cp.get('echo', 'mean_echo_threshold')
        }
    except configparser.Error as e:
        logger.error('Error: {}'.format(e))
    except ValueError as e:
        logger.error('Error: {}'.format(e))
    return conf


configure = get_configure_info(os.path.join(model_path, 'conf.txt'))


def read_wav(wav_file, category):
    fw = wave.open(wav_file, "rb")
    params = fw.getparams()
    if category == 'int16':
        dtype = np.int16
    elif category == 'short':
        dtype = np.short
    else:
        dtype = np.float

    nchannels, sampwidth, framerate, nframes = params[:4]
    str_data = fw.readframes(nframes)
    wavedata = np.fromstring(str_data, dtype=dtype)
    fw.close()
    return wavedata
# calculate volume


# method 2: 10 times log10 of square sum
def calVolumeDB(waveData, frameSize, overLap):
    wlen = len(waveData)
    step = frameSize - overLap
    frameNum = int(math.ceil(wlen*1.0/step))
    volume = np.zeros((frameNum, 1))
    for i in range(frameNum):
        curFrame = waveData[np.arange(i*step, min(i*step+frameSize, wlen))]
        curFrame = curFrame - np.mean(curFrame)
        if 0 not in curFrame:
            volume[i] = 10*np.log10(np.sum(curFrame*curFrame))
    return volume


def db_mean(waveData):
    frameSize = 256
    overLap = 128
    wav_length = len(waveData)
    step = frameSize - overLap
    frameNum = int(math.ceil(wav_length * 1.0 / step))
    end_30 = frameNum - 128
    volume12 = calVolumeDB(waveData, frameSize, overLap)
    total = 0
    mean = 0
    for data_b in volume12[0:128]:
        total = total + data_b

    for data_b in volume12[end_30:frameNum]:
        total = total + data_b
        mean = total/256
    return mean

def sox_wav(in_path, category):
    name, _ = os.path.splitext(os.path.basename(in_path))
    out_path = os.path.join(model_path, 'mid_wav', name + '_demo.wav')
    dir_path = os.path.dirname(out_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    def get_sox():
        if platform.system() == 'Windows':
            sox_cmd = os.path.join(model_path, 'sox', 'sox.exe')
        else:
            sox_cmd = 'sox'
        return sox_cmd
    sox_cmd = get_sox()
    if category == 'low':
        cmd = '{} {} -r 16k -b 16 {} sinc {}'.format(sox_cmd,in_path, out_path, configure.get('sox_low_threshold'))
    elif category == 'high':
        cmd = '{} {} -r 16k -b 16 {} sinc {}'.format(sox_cmd, in_path, out_path, configure.get('sox_high_threshold'))
    elif category == 'echo':
        cmd = '{} {} -r 16k -b 16 {} sinc {}'.format(sox_cmd, in_path, out_path, configure.get('sox_echo_threshold'))
    else:
        logger.error("The check type must in 'low, high, echo'")
        return None
    if not os.path.exists(out_path):
        os.system(cmd)
    return out_path


def calEnergy(wav_data):
    ene = []
    total = 0
    for i in range(len(wav_data)):
        total = total + (int(wav_data[i]) * int(wav_data[i]))
        if (i + 1) % 256 == 0:
            ene.append(total)
            total = 0
        elif i == len(wav_data) - 1:
            ene.append(total)
    return ene


def energy_mean(ene):
    s = 0
    for i in ene:
        s = s + i
    b = len(ene)
    m = s/b
    return m


class NoiseDetect(object):
    label = {}

    def __init__(self, wavpath):
        self.wavpath = wavpath
        self.label = 'normal'

    def detect(self, type):
        sox_file = sox_wav(self.wavpath, type)
        detect_wav_data = read_wav(sox_file, 'short')
        wav_ene = calEnergy(detect_wav_data)
        wav_mean = energy_mean(wav_ene)
        os.remove(sox_file)
        return wav_mean

    def high_detect(self):
        high_mean = self.detect('high')
        if high_mean < int(configure.get('mean_high_threshold1')):
            self.label = 'high frequency loss'
        elif high_mean < int(configure.get('mean_high_threshold2')):
            self.label = 'need manual detect'
        else:
            self.label = 'normal'

    def echo_detect(self):
        echo_mean = self.detect('echo')
        if echo_mean > int(configure.get('mean_echo_threshold')):
            self.label = 'continue noise'
        else:
            self.label = 'normal'

    def low_detect(self):
        low_mean = self.detect('low')
        if low_mean > int(configure.get('mean_low_threshold1')):
            self.label = 'DC offset'
        elif low_mean > int(configure.get('mean_low_threshold2')):
            self.label = 'continue noise'
        else:
            self.label = 'normal'

    def bottom_noise_detect(self):
        detect_wav_data = read_wav(self.wavpath, 'int16')
        wav_mean = db_mean(detect_wav_data)
        if wav_mean > int(configure.get('db_threshold')):
            self.label = 'continue noise'
        else:
            self.label = 'normal'

    def handle(self):
        for checker in [self.high_detect, self.echo_detect, self.low_detect, self.bottom_noise_detect]:
            if self.label == 'normal':
                try:
                    checker()
                except Exception as e:
                    self.label = 'audio damage'
                    logger.error("The audio {} is damage, please check it".format(self.wavpath))

            else:
                break