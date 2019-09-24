import os
import re
import subprocess
from filters.base import Filter

import logging
logger = logging.getLogger(__name__)


class EnergyLost(Filter):
    filter_type = 'energylost'

    def process(self, wavobj):
        lossenergy = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'energylost/lossenergy')
        cmd_line = "{lossenergy} {wavpath}".format(lossenergy=lossenergy, wavpath=wavobj.path)
        try:
            result = subprocess.check_output(cmd_line, shell=True)
        except Exception as e:
            logger.error("Subporcess lossenergy commond faild {}".format(cmd_line))
            result = ''
        res = result.decode().strip()
        if res == 'ok':
            return 'valid'
        elif re.match('invalid\\t.*', res):
            return res.replace('invalid\t', '')
        else:
            logger.error(result)
            return 'damage'

    def check(self, wavobj):
        logger.info("Start check energylost {}".format(wavobj.path))
        label = self.process(wavobj)
        logger.info("Check energylost over")
        return {self.filter_type: label}


        # for j in range(len(spectrum)):
        #     count = 0
        #     sum = 0
        #     lineData = [0 for i in range(len(spectrum[j]))]
        #     for k in range(len(spectrum[j])):
        #         sum = sum + spectrum[j][k]
        #     # print sum
        #     for k in range(len(spectrum[j])):
        #         tmp = sum / len(spectrum[j])
        #         lineData[k] = spectrum[j][k] / tmp
        #
        #     for k in range(len(lineData)):
        #         # print lineData[k]
        #         if lineData[k] < 1:
        #             count = count + 1
        #     lieStaticData[j] = round(float(count) / len(lineData), 2)
