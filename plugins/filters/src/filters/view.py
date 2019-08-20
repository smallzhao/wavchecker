from filters import base, fetcher
from filters.checker import noise_detect
from filters.energylost import energylost
from filters.export import Export

class View():
    filter_map = {
        'energylost': energylost.EnergyLost,
        'noise': noise_detect.NoiseDetect
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
            for taskinfo in self.taskinfos.split('\n'):
                task_id, group = taskinfo.split('\t')
                tasks_infos.append((task_id, group))
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
        fetch = fetcher.Fetcher(task_infos)
        wavs = []
        for wavfile in fetch.fetch(self.input):
            wavs.append(fetch.fetch_wavinfo(wavfile))
        # 音频检查
        self.check(wavs, filters)
        # 结果输出
        expoter = Export()
        expoter.dumps(self.output, wavs)


