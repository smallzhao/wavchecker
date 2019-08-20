import os
from filters import view


def main(input, result, args, taskinfos=None):
    checker = view.View(input, result, args)
    checker.handle()


if __name__ == '__main__':
    os.environ()
    args = 'energylost@noise'
    taskinfos = ''
    main('/input', '/output', args, taskinfos=taskinfos)