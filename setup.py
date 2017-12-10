#!/usr/bin/env python3

import os
import sys
from setuptools import setup

if sys.version_info < (3, 4, 0):
    sys.stderr.write("This script requires Python 3.4 or newer.")
    sys.stderr.write(os.linesep)
    sys.exit(-1)

with open(os.path.join(os.path.dirname(__file__), 'requirements.txt')) as fd:
    requirements = [x.split('#')[0]
                    for x in fd.readlines()]

setup(
    name='irctest',
    version='0.1.2',
    author='Valentin Lorentz',
    url='https://github.com/ProgVal/irctest/',
    author_email='progval+irctest@progval.net',
    description='A script to test interoperability of IRC software.',
    platforms=['linux', 'linux2'],
    long_description="""This script aims at testing interoperability of
    software using the IRC protocol, by running them against test suites
    and making different software communicate with each other.""",
    classifiers = [
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Communications :: Chat :: Internet Relay Chat',
        'Topic :: Software Development :: Testing',
        ],

    # Installation data
    packages=[
            'irctest',
            'irctest.client_tests',
            'irctest.controllers',
            'irctest.irc_utils',
            'irctest.server_tests',
            ],
    install_requires=requirements,
    )

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
