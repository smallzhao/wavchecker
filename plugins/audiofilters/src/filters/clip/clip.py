# -*- coding:utf-8 -*-
# 我们参考 "Detection of Clipped Fragments in Speech Signals"（https://www.academia.edu/8803834/Detection_of_Clipped_Fragments_in_Speech_Signals）
# 对截幅和削波的检测方式进行了实现。在该篇论文中，作者对截幅和削波的检测采用了建立音频信号直方图，利用直方图算出Rcl系数来判断的方法，通过反复验证，证实当Rcl>0.55时，有大概100%的可能性检测出截幅和削波。
# 此外，经过作者的反复测试，得出结论当直方图的箱数K=301，采样点个数N=8000时，呈现最佳表现。

import numpy as np

from filters.base import Filter
from settings import DEFAULT_BINS_NUM, DEFAULT_WINDOW_WIDTH

import logging
logger = logging.getLogger(__name__)


class ClippingDetection(Filter):
    """
    Represents a clipping detection of audio data.
    """
    filter_type = 'clip'

    def __get_samples(self, wavobj):
        """
        Gets samples from a .wav file.
        Takes the path, and returns samples and the number of samples.
        """
        waveData = np.fromstring(wavobj.data, dtype=np.short)
        num_samples = int(len(waveData) / DEFAULT_WINDOW_WIDTH)
        return waveData, num_samples

    def __split_to_fragments(self, samples, num_samples, N=DEFAULT_WINDOW_WIDTH):
        """
        Splits samples to fragments.
        Takes samples, number of samples and window width, and returns fragments.
        """
        fragments = [samples[i * N:(i + 1) * N] for i in range(num_samples)]
        return fragments

    def __histogram_calculation(self, fragment, K=DEFAULT_BINS_NUM):
        """
        Creates histogram.
        Takes fragment and number of bins, and returns histogram(with the index of bins and the height of bins).
        """
        height_k, k = [0 for _ in range(K)], 0  # Initialize histogram('k' is the index of bin，'height_k' is the height of bin).

        signal_n = [i for i in fragment]  # The values of fragment.
        signal_min = min(fragment)
        signal_max = max(fragment)  # Find the maximum and minimum.

        # Traverse the values of fragment.
        for n in range(min(DEFAULT_WINDOW_WIDTH, len(signal_n))):
            k = int((signal_n[n] - int(signal_min)) / (int(signal_max) - int(signal_min)) * (K - 1))  # Calculate the index of bin.
            if (k < DEFAULT_WINDOW_WIDTH):
                height_k[k] += 1
            else:
                height_k[k - 1] += 1

        histogram = height_k[:]
        return histogram

    def __is_valid_fragments(self, fragments):
        """
        Determines if fragment is valid.
        Takes fragments, and returns the list of result(the value of every element only 0 or 1).
        """
        judge_fragments = []
        for fragment in fragments:
            signal_average = sum([abs(i) for i in fragment[:6000]]) / 6000
            judge_fragments.append(1 if signal_average > 100 else 0)
        return judge_fragments

    def get_clipping_coefficient(self, histogram):
        """
        Calculates the clipping coefficient("Rcl").
        Takes the histogram(with the index of bins and the height of bins).
        Returns a value as an indicator of the level of clipping
        varies from 0(no clipping) to 1(clipping with very high probability).
        """
        kl, kr = 0, DEFAULT_BINS_NUM - 1  # Find the index of the leftmost non-zero and rightmost non-zero bin.
        Denom = kr - kl
        yl0, yr0 = histogram[kl], histogram[kr]  # Set the starting bin on both sides.
        dl, dr = 0, 0  # Initialize distance from left and right.
        D_max = 0  # Initialize the max distance.
        while (kr > kl):
            kl += 1
            kr -= 1
            if (histogram[kl] <= yl0):
                dl += 1
            else:
                yl0 = histogram[kl]
                dl = 0
            if (histogram[kr] <= yr0):
                dr += 1
            else:
                yr0 = histogram[kr]
                dr = 0
            D_max = max(D_max, dl, dr)

        Rcl = 2 * D_max / Denom
        return Rcl

    def __is_clippings(self, fragments):
        """
        Determines if fragment is clipping.
        Takes fragments, and returns the list of result(the value of every element only 0 or 1).
        """
        judge_fragments = self.__is_valid_fragments(fragments)
        is_clippings = []
        for k, fragment in enumerate(fragments):
            if judge_fragments[k] == 1:
                histogram = self.__histogram_calculation(fragment)
                Rcl = self.get_clipping_coefficient(histogram)
                is_clippings.append(0 if Rcl < 0.55 else 1)
            else:
                is_clippings.append(0)
        return is_clippings

    def get_clipping_proportion(self, is_clippings, judge_fragments):
        """
        Takes the list of is_clippings and valid_fragments(the value of every element only 0 or 1)
        Returns the proportion of clipping.
        """
        clipping_proportion = is_clippings.count(1) / judge_fragments.count(1)
        return clipping_proportion

    def check(self, wavobj):
        """
        Takes the path of a .wav file, and returns the proportion of clipping.
        """
        logger.info("Start check clip {}".format(wavobj.path))
        samples, num_samples = self.__get_samples(wavobj)
        fragments = self.__split_to_fragments(samples, num_samples, N=DEFAULT_WINDOW_WIDTH)
        judge_fragments = self.__is_valid_fragments(fragments)
        is_clippings = self.__is_clippings(fragments)
        clipping_proportion = self.get_clipping_proportion(is_clippings, judge_fragments)
        logger.info("Check clip over")
        return {self.filter_type: clipping_proportion}

