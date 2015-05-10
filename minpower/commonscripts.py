"""
Short, commonly used scripts.
Many of them are one liners.
"""

import os
import sys
import csv
import logging
import itertools
import operator
import datetime
from contextlib import contextmanager

import numpy as np
import pandas as pd
from pandas import DataFrame, Series, date_range

from pprint import pprint
try:  # for development
    from ipdb import set_trace  # pudb
    import IPython
    from IPython.frontend.terminal.embed import InteractiveShellEmbed
#    from IPython.config.loader import Config
#
#    cfg = Config()
#    cfg.InteractiveShellEmbed.prompt_in1="myprompt [\\#]> "
#    cfg.InteractiveShellEmbed.prompt_out="myprompt [\\#]: "
#    cfg.InteractiveShellEmbed.profile=ipythonprofile
    ipython_shell = InteractiveShellEmbed(
    )  # config=cfg, user_ns=namespace, banner2=banner)
except:
    from pdb import set_trace


class StreamToLogger(object):

    """
    Fake file-like stream object that redirects writes to a logger instance.
    """

    def __init__(self, logger=logging, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())


@contextmanager
def not_quiet():
    yield


@contextmanager
def quiet():
    sys.stderr.flush()
    sys.stdout.flush()
    if sys.stdout != sys.__stdout__:
        # ipython notebook redirects std_out to some crazy special object
        # the rest of this stream redirection breaks the ipython notebook
        # so skip it
        yield
        return

    devnull = open(os.devnull, "w")
    sys.stdout = devnull
    sys.stderr = devnull

    logger = logging.getLogger()
    current_log_level = logger.level
    logger.setLevel(logging.CRITICAL)

    try:
        yield
    finally:
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        logger.setLevel(current_log_level)


def gen_time_dataframe(generators, times, values=()):
    kwargs = dict(columns=[str(g) for g in generators])
    try:
        kwargs['index'] = times.strings.index
    except AttributeError:
        kwargs['index'] = times

    if values:
        values = np.array(values)
        if values.shape != (len(times), len(generators)):
            values = values.T
        df = DataFrame(values, **kwargs)
    else:
        df = DataFrame(**kwargs)

    df.index.name = 'time'
    return df


def ts_from_csv(filename, index_col=0, squeeze=True, timezone=None, is_df=True, **kwargs):
    kwargs['header'] = 0 if is_df else None

    df = pd.read_csv(filename, index_col=index_col, squeeze=squeeze, **kwargs)
    df.index = pd.DatetimeIndex(df.index)
    if timezone is not None:
        # pandas seems to convert any stamps to UTC in the DatetimeIndex call
        df.index = df.index.tz_localize('UTC').tz_convert(timezone)
    return df


def bool_to_int(x):
    return 1 if x else 0


class DotDict(dict):

    '''a dict with dot notation access'''

    def __getattr__(self, attr):
        return self.get(attr)

    def copy(self):
        return DotDict(dict(self))

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

###### matrix stuff #######


def correct_status(status):
    # correct for strange solver values returned on resolve
    status[status > 0.99] = 1
    status[status < 0.01] = 0
    return status.astype(int)


def elementwiseAdd(La, Lb):
    return map(operator.add, La, Lb)


def transpose(listoflists):
    return map(None, *listoflists)


def flatten(listoflists):
    '''Flatten one level of nesting'''
    return list(itertools.chain.from_iterable(listoflists))


def within(x, val=0, eps=1e-3):
    return (val - eps) <= x <= (val + eps)


def replace_all(seq, obj, replacement):
    def with_index(seq):
        for i in xrange(len(seq)):
            yield i, seq[i]

    for i, elem in with_index(seq):
        if elem == obj:
            seq[i] = replacement
    return seq


def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return itertools.izip(a, b)

##### csv stuff #####


def writeCSV(fields, data, filename):
    with open(filename, 'w+') as f:
        writer = csv.writer(f)
        writer.writerow(fields)
        writer.writerows(data)

#################### string stuff ##################


def convert_str2num(s):
    s = s.strip()
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return s


def indexCaseSpaceInsensitive(L, s):
    return map(drop_case_spaces, L).index(drop_case_spaces(s))


def drop_case_spaces(s):
    '''get rid of spaces in a string and make lower case. will also work with list of strings'''
    try:
        return s.lower().replace(' ', '').replace('_', '')
    except AttributeError:
        if s is None:
            return None
        elif isinstance(s, list):
            return map(drop_case_spaces, s)


def to_percent(val, digits=0):
    return '{p:.{d}%}'.format(p=val, d=digits)


##################### file stuff ###########################
def splitFilename(fullPathFilenm):
    '''split a filename into its directory, filename, and extension'''
    (dirNm, fullFilenm) = os.path.split(fullPathFilenm)
    (fileNm, extNm) = os.path.splitext(fullFilenm)
    return dirNm, fileNm, extNm


def joindir(dir, file):
    return os.path.join(dir, file)

################### time stuff ###########################


def hours(t):
    try:
        return t.days * 24.0 + t.seconds / 3600.0  # t is a datetime object
    except AttributeError:
        return datetime.timedelta(hours=t)  # t is a number

####################### class stuff #######################


def getattrL(L, attribute='name'):
    '''get the attribute of each class instance in a list'''
    return [getattr(item, attribute) for item in L]


def update_attributes(instance, variables, exclude=['self'], include=None):
    """Update instance attributes

    For example, update(self, locals())

    instance: Instance to update via setattr()
    variables: Dictionary of variables
    exclude: Variables to explicitly exclude, defaults to ['self'].
    include: Variables to explicitly include. If set, include overides exclude.
    """
    if include is not None:
        [setattr(instance, k, v) for k, v in variables.items() if k in include]
    else:
        if 'self' not in exclude:
            exclude.append('self')
        [setattr(
            instance, k, v) for k, v in variables.items() if k not in exclude]


def debug_frame_unequal(left, right, tol=1e-5):
    diff = left - right
    different = diff[(diff < -tol) | (diff > tol)]
    cols = different.columns[different.any()]
    idx = different.ix[different.any(axis=1)].index

    print(left[cols].ix[idx])
    print(right[cols].ix[idx])
    return cols, idx
