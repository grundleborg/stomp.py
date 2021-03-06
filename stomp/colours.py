"""Colour 'constants' used by the command line client.
"""

import platform


if platform.system().lower() != 'windows':
    GREEN = "\33[32m"
    RED = "\33[31m"
    NO_COLOUR = "\33[0m"

    BOLD = "\33[1m"
else:
    GREEN = ""
    NO_COLOUR = ""
    RED = ""

    BOLD = ""
