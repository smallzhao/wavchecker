import sys
from checker import check


def main(input, result, taskinfos=''):
    checker = check.Checker(input, result, taskinfos)
    checker.run()


if __name__ == '__main__':
    if len(sys.argv) > 2:
        taskinfos = sys.argv[1]
    else:
        taskinfos = ''
    main('/input', '/result', taskinfos)