# irctest

This project aims at testing interoperability of software using the
IRC protocol, by running them against test suites and making different
software communicate with each other.

It is very young and does not contain a lot of test cases yet.

## The big picture

This project contains:

* IRC protocol test cases
* small wrappers around existing software to run tests on them

Wrappers run software in temporary directories, so running `irctest` should
have no side effect, with [the exception of Sopel](https://github.com/sopel-irc/sopel/issues/946).

## Prerequisites

Install irctest and dependencies:

```
git clone https://github.com/ProgVal/irctest.git
cd irctest
pip3 install --user -r requirements.txt
python3 setup.py install --user
```

Add `~/.local/bin/` to your `PATH` if it is not.

```
export PATH=$HOME/.local/bin/:$PATH
```

## Run tests

To run (client) tests on Limnoria:

```
pip3 install --user limnoria
python3 -m irctest irctest.controllers.limnoria
```

To run (client) tests on Sopel:

```
pip3 install --user sopel
mkdir ~/.sopel/
python3 -m irctest irctest.controllers.sopel
```

To run (server) tests on InspIRCd:

```
cd /tmp/
git clone https://github.com/inspircd/inspircd.git
cd inspircd
./configure --prefix=$HOME/.local/ --development
make -j 4
make install
python3 -m irctest irctest.controllers.inspircd
```

To run (server) tests on Mammon:

```
pip3 install --user git+https://github.com/mammon-ircd/mammon.git
python3 -m irctest irctest.controllers.mammon
```

To run (server) tests on Charybdis::

```
cd /tmp/
git clone https://github.com/atheme/charybdis.git
cd charybdis
./configure --prefix=$HOME/.local/
make -j 4
make install
python3 -m irctest irctest.controllers.charybdis
```

## Full help

```
usage: python3 -m irctest [-h] [--show-io] [-v] [-s SPECIFICATION] [-l] module

positional arguments:
  module                The module used to run the tested program.

optional arguments:
  -h, --help            show this help message and exit
  --show-io             Show input/outputs with the tested program.
  -v, --verbose         Verbosity. Give this option multiple times to make it
                        even more verbose.
  -s SPECIFICATION, --specification SPECIFICATION
                        The set of specifications to test the program with.
                        Valid values: RFC1459, RFC2812, IRCv3.1, IRCv3.2. Use
                        this option multiple times to test with multiple
                        specifications. If it is not given, defaults to all.
  -l, --loose           Disables strict checks of conformity to the
                        specification. Strict means the specification is
                        unclear, and the most restrictive interpretation is
                        choosen.
```

## What `irctest` is not

A formal proof that a given software follows any of the IRC specification,
or anything near that.

At best, `irctest` can help you find issues in your software, but it may
still have false positives (because it does not implement itself a
full-featured client/server, so it supports only “usual” behavior).
Bug reports for false positives are welcome.

