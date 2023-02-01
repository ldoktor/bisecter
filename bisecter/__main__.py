"""
Main entry point when called by 'python -m'.
"""

import sys

from bisecter import Bisecter

if __name__ == '__main__':
    APP = Bisecter()
    sys.exit(APP())

