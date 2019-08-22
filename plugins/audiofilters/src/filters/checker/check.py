
import os
import time
from collections import defaultdict
from functools import reduce

from checker.noise_detect import NoiseDetect
from checker.utils import dump_xlsx

import logging
logger = logging.getLogger(__name__)

SRCDATA = ''

model_path = os.path.dirname(os.path.abspath(__file__))


class Checker(object):
    wb_content = {
        '统计': [['任务ID', '号段', '总数', '正常', '需人工质检', '音频损坏', '直流偏移', '高频丢失', '合格率']],
        '明细': [['任务ID', '号段', '音频路径', '质检结果']]
    }

    # 检测错误字段
    count_info = {'normal': 0, 'continue noise': 0, 'audio damage': 0, 'DC offset': 0, 'high frequency loss': 0, 'need manual detect': 0}
    ext = ['.wav', '.mp3']

    def input_check(self, task_id, group):
        if not task_id.isdigit():
            logger.error("Taskid muset be int")
            return False
        return True

    def fetch(self):
        files = []
        def get_wavs(task_id, group, filepath):
            files = []
            for root, dirs, filenames in os.walk(filepath):
                for filename in filenames:
                    name, ext = os.path.splitext(filename)
                    if ext in self.ext:
                        files.append((task_id, group, os.path.join(root, filename)))
            return files
        # 输入号段
        if self.taskinfos:
            taskinfos = [taskinfo.split('\t') for taskinfo in self.taskinfos.split('\n')]
            for task_id, group in taskinfos:
                if not self.input_check(task_id, group):
                    continue
                filepath = os.path.join(SRCDATA, task_id, group)
                if not os.path.exists(filepath):
                    logger.error("The group {} is not exists, please check it".format(task_id + group))
                    continue
                wav_file = get_wavs(task_id, group, filepath)
                files.extend(wav_file)
        else:
            files = get_wavs('id', 'group', self.input)
        return files

    def detect(self, wav_file):
        checker = NoiseDetect(wav_file)
        # import pdb;pdb.set_trace()
        checker.handle()
        return checker.label

    def count(self, results):
        # 格式化以及统计检查结果
        result = defaultdict(dict)
        for task_id, group, url, label in results:
            if not label in self.count_info:
                print ('error label')
                continue
            if label in result[(task_id, group)]:
                result[(task_id, group)][label] += 1
            else:
                result[(task_id, group)].update(self.count_info)
                result[(task_id, group)][label] = 1

        count_result = []
        for task_info, results in result.items():
            total_count = reduce(lambda x, y: x + y, results.values())
            persent = float(results['normal']) / float(total_count)
            count_result.append([task_info[0], task_info[1], total_count, results['normal'], results['continue noise'], results['audio damage'],
                                 results['DC offset'], results['high frequency loss'], persent])
        return count_result

    def dump_result(self, results):
        day, now_time = time.strftime('%Y-%m-%d\t%H-%M-%S').split('\t')
        relpath = os.path.join(day, now_time + '.xlsx')
        dest_path = os.path.join(self.output, relpath)

        self.wb_content['明细'].extend(results)
        self.wb_content['统计'].extend(self.count(results))
        dir_path = os.path.dirname(dest_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        dump_xlsx(self.wb_content, dest_path)

    def run(self):
        results = []
        for task_id, group, file in self.fetch():
            label = self.detect(file)
            results.append([task_id, group, file, label])
        self.dump_result(results)
