import os
from filters import view


def main(input, result, args, taskinfos=None):
    checker = view.View(input, result, args)
    checker.handle()


if __name__ == '__main__':
    taskinfos = os.environ.get('taskinfos')
    args = os.environ.get('args')

    # input = r'C:\Users\Aorus\Desktop\空能量数据样例\9_3_能量缺失\不合格'
    # output = r'C:\Users\Aorus\Desktop\空能量数据样例\9_3_能量缺失'
    # args = 'energylost@noise@clip@snr@am_detect-3500-0.001-2500-0.08'
    main('/input', '/result', args, taskinfos=taskinfos)