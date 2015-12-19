import os
import unittest


def discover():
    ts = unittest.TestSuite()
    ts.addTests(unittest.defaultTestLoader.discover(os.path.dirname(__file__)))
    return ts
