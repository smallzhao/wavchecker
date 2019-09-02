# -*- coding: utf-8 -*-

import codecs
import os
import math
import functools
import openpyxl as px


def make_dirs(path):
    if not os.path.exists(path):
        os.makedirs(path)


def path_exists(path):
    if os.path.exists(path):
        return True
    return False


def join_path(*args):
    return functools.reduce(lambda x, y: os.path.join(x, y), args)


def log_row(fn, mode='w', *args):
    with codecs.open(fn, mode, encoding='utf-8') as f:
        f.write('\n'.join(args).strip() + '\n')


def log_column(fn, mode='w', *args):
    with codecs.open(fn, mode, encoding='utf-8') as f:
        f.write('\t'.join(args).strip() + '\n')


def get_lines(txt):
    with codecs.open(txt, 'rb', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if len(line.strip()) > 0:
                yield line.strip()


def get_file_realpath(src, *tar):
    for root, _, files in os.walk(src):
        for fn in files:
            fn_name, fn_ext = os.path.splitext(fn)
            if fn_ext.lower() not in tar:
                continue

            yield os.path.join(root, fn)


def slice(sequence, num_chunk=10):
    num_piece = int(math.ceil(float(len(sequence)) / float(num_chunk)))
    return (sequence[num_chunk*n:num_chunk*(n+1)] for n in range(num_piece))



def dump_xlsx(workbook, filename, sheet_titles=[], columns=[], rows=[]):
    wb = px.Workbook()
    actived = False
    if isinstance(workbook, dict):
        for sheet_title, sheet_content in workbook.items():
            if sheet_titles and not sheet_title in sheet_titles:
                continue

            if actived:
                ws = wb.create_sheet(title=sheet_title)
            else:
                ws = wb.active  # have to call active in the first time to create sheet
                ws.title = sheet_title
                actived = True

            for row in sheet_content:
                ws.append(row)
    else:  # syntax sugar for one sheet
        ws = wb.active
        for row in workbook:
            ws.append(row)

    wb.save(filename=filename)
