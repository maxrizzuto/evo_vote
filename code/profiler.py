"""
profiler.py
A profiler class using decorators
"""

import time
from collections import defaultdict


def profile(f):
    """ Convenience function to make decorator tags simpler:
        e.g. @profile instead of @Profiler.profile """
    return Profiler.profile(f)


class Profiler:
    calls = defaultdict(int)  # function_name ==> integer
    time = defaultdict(float)  # function_name ==> float

    @staticmethod
    def _add(function_name, sec):
        Profiler.calls[function_name] += 1
        Profiler.time[function_name] += sec

    @staticmethod
    def profile(f):
        """ The profiler decorator"""

        def wrapper(*args, **kwargs):
            function_name = str(f).split()[1]
            start = time.time_ns()
            val = f(*args, **kwargs)
            finish = time.time_ns()
            elapsed = (finish - start) / 10 ** 9
            Profiler._add(function_name, elapsed)
            return val

        return wrapper

    @staticmethod
    def report():
        """ Summarize # calls, total runtime, and time/call for each function """
        print("Function              Calls     TotSec   Sec/Call")
        for name, num in Profiler.calls.items():
            sec = Profiler.time[name]
            print(f'{name:20s} {num:6d} {sec:10.6f} {sec / num:10.6f}')
