import numpy as np
import matplotlib.pyplot as plt
from filters.base import Filter

import logging
logger = logging.getLogger(__name__)


class EnergyLost(Filter):
    normal_prop = 0.75
    error_prop = 0.70
    filter_type = 'energylost'

    def get_spectrum(self, wavobj):
        "获取能量矩阵"
        def get_NFFT(framesize):
            # 找到与当前framesize最接近的2的正整数次方
            n = 0
            while framesize != 0:
                framesize = int(framesize / 2)
                n += 1
            return 2**n

        framelength = 0.025  # 帧长20~30ms
        framesize = framelength * wavobj.sample_rate  # 每帧点数 N = t*fs,通常情况下值为256或512,要与NFFT相等\
        framesize = get_NFFT(framesize)
        NFFT = framesize  # NFFT必须与时域的点数framsize相等，即不补零的FFT

        overlapSize = 1.0 / 3 * framesize  # 重叠部分采样点数overlapSize约为每帧点数的1/3~1/2，做帧移
        overlapSize = int(round(overlapSize))  # 取整
        # 音频矩阵归一化
        waveData = np.fromstring(wavobj.data, dtype=np.short)
        wavedata = waveData * 1.0/max(abs(waveData))
        # 获取到能量矩阵
        spectrum, _, _, _ = plt.specgram(wavedata, NFFT=NFFT, Fs=wavobj.sample_rate, window=np.hanning(M=framesize),
                                                 noverlap=overlapSize, mode='default', scale_by_freq=True,
                                                 sides='default', scale='dB', xextent=None)
        return spectrum

    def get_state(self, spectrum):
        "获取音频状态"
        # 求能量矩阵每一行低于这一行平均能量的值的比例
        energy_props = []
        for j in range(len(spectrum)):
            mean = np.mean(spectrum[j])
            count = 0
            for k in range(len(spectrum[j])):
                if spectrum[j][k] / mean < 1:
                    count += 1
            energy_props.append(round(float(count) / len(spectrum[j]), 2))

        # 计算音频状态，连续一段时间内5个已上同状态以上才可以确认音频状态
        n_error = 0
        n_normal = 0
        n_mid = 0
        label = self.normal
        for energy_prop in energy_props:
            if energy_prop < self.error_prop:
                n_error += 1
                if n_error > 2:
                    n_mid = 0
                    n_normal = 0
                if n_error > 5:
                    label = self.abnormal
                    break
            if self.normal_prop > energy_prop >= self.error_prop:
                n_mid += 1
                if n_mid > 2:
                    n_error = 0
                    n_normal = 0
                if n_mid > 5:
                    label = self.not_known
                    break
            if energy_prop >= self.normal_prop:
                n_normal += 1
                if n_normal > 2:
                    n_error = 0
                    n_mid = 0
        return label

    def check(self, wavobj):
        logger.info("Start check energylost {}".format(wavobj.path))
        spectrum = self.get_spectrum(wavobj)
        label = self.get_state(spectrum)
        logger.info("Check energylost over")
        return {self.filter_type: label}


        # for j in range(len(spectrum)):
        #     count = 0
        #     sum = 0
        #     lineData = [0 for i in range(len(spectrum[j]))]
        #     for k in range(len(spectrum[j])):
        #         sum = sum + spectrum[j][k]
        #     # print sum
        #     for k in range(len(spectrum[j])):
        #         tmp = sum / len(spectrum[j])
        #         lineData[k] = spectrum[j][k] / tmp
        #
        #     for k in range(len(lineData)):
        #         # print lineData[k]
        #         if lineData[k] < 1:
        #             count = count + 1
        #     lieStaticData[j] = round(float(count) / len(lineData), 2)
