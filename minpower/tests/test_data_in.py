from minpower.tests.test_utils import (user_config, istest, 
    with_setup, reset_config)
from minpower.get_data import parsedir
import os


basedir = os.path.split(__file__)[0]

@istest
@with_setup(teardown=reset_config)
def check_pmin():
    user_config.directory = os.path.join(basedir, 'uc')
    data_tup = parsedir()
    generators = data_tup[0]
    data = data_tup[-1]
    
    assert(data['generators'].pmin.tolist() == \
        map(lambda gen: gen.pmin, generators))