import json
import base64
from filters import base, fetcher
from filters.noise import noise_detect
from filters.energylost import check
from filters.clip import clip
from filters.snr import snr
from filters.am_detect import am_detect
from filters.disturb_detect import detect
from filters.export import Export

import logging
logger = logging.getLogger(__name__)


class View():
    filter_map = {
        'energylost': check.EnergyLost,
        'noise': noise_detect.NoiseDetect,
        'clip': clip.ClippingDetection,
        'snr': snr.SNR,
        'am_detect': am_detect.AMDetect,
        'disturb_detect': detect.DisturbDetect
    }

    def __init__(self, input, output, args, taskinfos=None):
        self.input = input
        self.output = output
        self.args = args
        self.taskinfos = taskinfos

    def parser(self):
        "parse input args as json"
        args_json = {}
        for arg in self.args.split('@'):
            infos = arg.split('-')
            args_json.update({infos[0]: infos[1:]})

        tasks_infos = []
        if self.taskinfos:
            taskinfos = json.loads(base64.b64decode(self.taskinfos).decode('utf-8'))
            for task_id, group in taskinfos:
                tasks_infos.append((task_id, group))
        logger.info("Get gorpus {}".format(tasks_infos))
        return args_json, tasks_infos

    def check(self, wavs, filters):
        for wav in wavs:
            for filter in filters:
                label = filter.check(wav)
                wav.labels.update(label)

    def handle(self):
        args_json, task_infos = self.parser()
        # 检测器实例化
        filters = [self.filter_map[type](args) for type, args in args_json.items()]
        logger.info("Start fetch files with {} {}".format(args_json, task_infos))
        fetch = fetcher.Fetcher(task_infos)
        wavs = []
        for wavfile in fetch.fetch(self.input):
            wavs.append(fetch.fetch_wavinfo(wavfile))
        # 音频检查
        self.check(wavs, filters)
        # 结果输出
        expoter = Export()
        expoter.dumps(self.output, wavs)


