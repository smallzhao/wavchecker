import os
import time
from filters.utils.serialize import dump_xlsx
from settings import FILTERS

import logging
logger = logging.getLogger(__name__)


class Export():
    wb_content = {
        # '统计': [['任务ID', '号段', '总数', '正常', '异常', '需人工质检']],
        '明细': [['任务ID', '号段', '音频路径'] + FILTERS]
    }

    def get_rows(self, wavs):
        rows = []
        for wav in wavs:
            row = [wav.task_id, wav.group, wav.path]
            for type in FILTERS:
                row.append(wav.labels.get(type, ''))
            rows.append(row)
        return rows

    # def count(self, results):
    #     # 格式化以及统计检查结果
    #     result = defaultdict(dict)
    #     for task_id, group, url, label in results:
    #         if not label in self.count_info:
    #             print ('error label')
    #             continue
    #         if label in result[(task_id, group)]:
    #             result[(task_id, group)][label] += 1
    #         else:
    #             result[(task_id, group)].update(self.count_info)
    #             result[(task_id, group)][label] = 1
    #
    #     count_result = []
    #     for task_info, results in result.items():
    #         total_count = reduce(lambda x, y: x + y, results.values())
    #         persent = float(results['normal']) / float(total_count)
    #         count_result.append([task_info[0], task_info[1], total_count, results['normal'], results['continue noise'], results['audio damage'],
    #                              results['DC offset'], results['high frequency loss'], persent])
    #     return count_result

    def dumps(self, result, wavs):
        day, now_time = time.strftime('%Y-%m-%d\t%H-%M-%S').split('\t')
        relpath = os.path.join(day, now_time + '.xlsx')
        dest_path = os.path.join(result, relpath)

        # self.wb_content['明细'].extend(results)
        self.wb_content['明细'].extend(self.get_rows(wavs))
        dir_path = os.path.dirname(dest_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        dump_xlsx(self.wb_content, dest_path)
        logger.info("Dumps result successfully")