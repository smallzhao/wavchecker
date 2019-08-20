
class Filter():
    filter_type = None
    normal = 'pass'
    # 需要人工质检
    not_known = 'uncertain'
    abnormal = 'nopass'

    def __init__(self, args):
        self.args = args

    def check(self, wavobj):
        raise NotImplementedError("The subclass must has this function")