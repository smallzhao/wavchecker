import os
import subprocess
from filters.base import Filter

import logging
logger = logging.getLogger(__name__)


class DisturbDetect(Filter):
    """干扰音检测"""
    filter_type = 'disturb_detect'

    def process(self, wavobj):
        disturb_detect = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'disturb_detect/disturb_detect')
        cmd_line = "{disturb_detect} {wavpath}".format(disturb_detect=disturb_detect, wavpath=wavobj.path)
        try:
            result = subprocess.check_output(cmd_line)
        except Exception as e:
            logger.error("Subporcess disturb_detect commond faild {}".format(cmd_line))
            result = ''
        if result.strip() == 'ok':
            return 'valid'
        elif result.strip().startswith('invalid'):
            return result.strip().strip('invalid:').strip()
        else:
            logger.error(result)
            return 'damage'

    def check(self, wavobj):
        logger.info("Start check disturb_detect {}".format(wavobj.path))
        label = self.process(wavobj)
        logger.info("Check disturb_detect over")
        return {self.filter_type: label}

