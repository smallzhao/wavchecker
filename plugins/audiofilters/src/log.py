import os
import logging.config

import yaml

model_path = os.path.dirname(os.path.abspath(__file__))

def setup_logging(default_path='conf/logging.yaml', default_level=logging.INFO, env_key='LOG_CFG'):
    """
    Setup logging configuration
    """
    logpath = os.path.join(os.path.dirname(model_path), default_path)
    if os.path.exists(logpath):
        with open(logpath, 'rt') as f:
            config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)
