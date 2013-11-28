"""Common setup code for logging."""

import os
import logging.config
import yaml


def log_setup(cfg_path='logging.cfg', level=logging.INFO, cfg_env='LOG_CFG'):
    """Sets up the logging based on the logging.cfg file. You can
    override the path using the LOG_CFG environment variable.

    """
    value = os.getenv(cfg_env, None)
    if value:
        cfg_path = value
    if os.path.exists(cfg_path):
        with open(cfg_path, 'r') as cfg_file:
            config = yaml.load(cfg_file.read())
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=level)
