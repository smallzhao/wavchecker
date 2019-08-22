import os
from filters import view


def main(input, result, args, taskinfos=None):
    checker = view.View(input, result, args)
    checker.handle()


if __name__ == '__main__':
    taskinfos = os.environ.get('taskinfos', '')
    download = os.environ.get('download', '')
    if taskinfos:
        input = download
    else:
        input = '/input'
    args = os.environ.get('args')

    # input = r'C:\Users\Aorus\Desktop\空能量数据样例\9_3_能量缺失\不合格'
    # output = r'C:\Users\Aorus\Desktop\空能量数据样例\9_3_能量缺失'
    # args = 'energylost@noise@clip'

    taskinfos = ''
    main(input, '/output', args, taskinfos=taskinfos)