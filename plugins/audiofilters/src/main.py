import os
import base64
import json
from filters import view


def main(input, result, args, taskinfos=None):
    checker = view.View(input, result, args, taskinfos=taskinfos)
    checker.handle()


if __name__ == '__main__':
    taskinfos = os.environ.get('taskinfos')
    args = os.environ.get('args')
    if taskinfos == 'null':
        taskinfos = ''

    main('/input', '/result', args, taskinfos=taskinfos)

    # while 1:
    #     import time
    #     time.sleep(3)

    # input = r'C:\Users\Aorus\Desktop\空能量数据样例\9_2_空能量\不合格'
    # output = r'C:\Users\Aorus\Desktop\空能量数据样例\9_2_空能量'
    # args = 'energylost@disturb_detect'

    # groups = []
    # with open(r'C:\Users\Aorus\Desktop\test.csv', 'r') as f:
    #     for line in f.readlines():
    #         task_id, group = line.split(',')
    #         groups.append((task_id.strip(), group.strip()))
    # taskinfos = base64.b64encode(json.dumps(groups).encode())
    # taskinfos = ''
    #
    # main(input, output, args, taskinfos=taskinfos)