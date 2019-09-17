import os
import base64
import json
from filters import view


def main(input, result, args, taskinfos=None):
    checker = view.View(input, result, args, taskinfos=taskinfos)
    checker.handle()


if __name__ == '__main__':
    # taskinfos = os.environ.get('taskinfos')
    # args = os.environ.get('args')
    #
    # main('/input', '/result', args, taskinfos=taskinfos)

    input = r'C:\Users\Aorus\Desktop\test\测试'
    output = r'C:\Users\Aorus\Desktop\test\测试'
    args = 'am_detect-3500-0.001-2500-0'
    #
    # groups = []
    # with open(r'C:\Users\Aorus\Desktop\test.csv', 'r') as f:
    #     for line in f.readlines():
    #         task_id, group = line.split(',')
    #         groups.append((task_id.strip(), group.strip()))
    # taskinfos = base64.b64encode(json.dumps(groups).encode())
    taskinfos = ''
    #
    main(input, output, args, taskinfos=taskinfos)