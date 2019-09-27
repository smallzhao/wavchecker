import numpy as np

from filters.base import Filter
from filters.utils import vad


import contextlib
import wave
import array
import os
import subprocess
import collections
import configparser
from pydub import AudioSegment, exceptions


import logging
logger = logging.getLogger(__name__)


model_path = os.path.dirname(os.path.abspath(__file__))
# import sys
# ffmpeg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg', 'bin')
# sys.path.append(ffmpeg_path)


def mkdirs(dirpath):
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)


class AMDetect(Filter):
    filter_type = 'am_detect'

    parter = ('.wav')

    def parser(self):
        high_energy, high_persent, low_energy, low_persent = self.args
        return int(high_energy), float(high_persent), int(low_energy), float(low_persent)

    def check(self, wavobj):
        logger.info("Start check am_detect {}".format(wavobj.path))
        vadobj = vad.VAD()
        frames = vadobj.frame_generator(wavobj)
        voiced_frames = vadobj.total_vad_frames_collector(wavobj, frames)
        # logger.info("Voiced frames {}".format(len(voiced_frames)))
        crests = self.get_crest_frames(voiced_frames)
        if len(crests) == 0:
            logger.error("Can't find voiced frames in {}".format(wavobj.path))
            return {self.filter_type: 'damage'}
        label = self.get_label(crests)
        logger.info("Check am_detect over")
        return {self.filter_type: label}

    def get_crest_frames(self, voiced_frames):
        """获取所有波峰值"""

        crests = []
        for voiced_frames in voiced_frames:
            # make check crests with duration 10ms
            # check_frames = list(self.frame_generator(self.check_frame_duration, voiced_frames, sample_rate, sample_width))
            check_frames = array.array('h', voiced_frames)
            for i in range(1, len(check_frames)-1):
                # left, mid, right = aver(check_frames[i-1]), aver(check_frames[i]), aver(check_frames[i+1])
                left, mid, right = abs(check_frames[i-1]), abs(check_frames[i]), abs(check_frames[i+1])
                # import pdb;pdb.set_trace()
                if mid > left and mid > right:
                    crests.append(mid)
        return crests

    def get_label(self, crests):
        high_count = 0
        low_count = 0
        high_label = 'invalid'
        low_label = 'invalid'

        high_energy, high_persent, low_energy, low_persent = self.parser()

        for frame in crests:
            if frame > high_energy:
                high_count += 1
            if frame > low_energy:
                low_count += 1
        # draw(crests)
        if (float(high_count) / float(len(crests))) > high_persent:
            high_label = 'valid'
        if (float(low_count) / float(len(crests))) > low_persent:
            low_label = 'valid'
        return high_label+'/'+low_label
