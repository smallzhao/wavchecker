# -*- coding:utf-8 -*-

import os
import sys
import fnmatch
import six


def get_matchfn(pattern, ignorecase):
    # syntax sugar, converts string to a tuple with one element
    if isinstance(pattern, six.string_types):
        pattern = (pattern, )
    # defines the function anymatch
    if pattern:
        if ignorecase:
            pattern = [p.lower() for p in pattern]
            matchfn = lambda s, p: fnmatch.fnmatch(s.lower(), p)
        else:
            matchfn = fnmatch.fnmatchcase
        # test if there was any one matched a pattern in the list
        anymatch = lambda s: any([matchfn(s, p) for p in pattern])
    else:
        # returns True always
        anymatch = lambda s: True
    return anymatch

def ivisit(src, dst=None, pattern=None, ignorecase=True):
    """
    A iterator to find all files in path `src` and match the Unix shell-like
    `pattern` if provided. The value of `pattern` could be a string or a tuple,
    and would perform a case-sensitive comparision if `ignorecase` was set
    to False.

    Details for unix shell-like wildcards can be seen from:
        https://docs.python.org/2/library/fnmatch.html#module-fnmatch

    If `dst` was provided, returns a pair consists of source path and
    destination with sub-directories. For example, if `src` was set to '/a'
    `dst` was set to '/b', while a file was located at '/a/c/d.txt', will
    yield a tuple ('/a/c/d.txt', '/b/c/d.txt')
    """
    anymatch = get_matchfn(pattern, ignorecase)

    # traverse the source path
    for dirpath, dirnames, filenames in os.walk(src):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if anymatch(filepath):
                # if `dst` was set, returns a pair
                if dst != None:
                    relpath = os.path.relpath(filepath, src)
                    yield (filepath, os.path.join(dst, relpath))
                else:
                    yield filepath




WINDOWS_LINE_ENDING = b'\r\n'
UNIX_LINE_ENDING = b'\n'

if __name__ == "__main__":
    # root = sys.argv[1]
    # for file_path in ivisit(root, pattern=("*.sh", "*.pl", "*.py")):
    file_path = r'E:\wavchecker\wavcheck\run-server'
    print("Converting %s ..." % file_path)
    with open(file_path, 'rb') as open_file:
        content = open_file.read()
    content = content.replace(WINDOWS_LINE_ENDING, UNIX_LINE_ENDING)

    with open(file_path, 'wb') as open_file:
        open_file.write(content)
