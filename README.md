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
pip3 install --user -r requirements.txt pyxmpp2-scram
python3 setup.py install --user
```

Add `~/.local/bin/` (and/or `~/.local/bin/` for Oragono)
to your `PATH` if it is not.

```
export PATH=$HOME/.local/bin/:$HOME/go/bin/:$PATH
```

## Using pytest

irctest is invoked using the pytest test runner / CLI.

You can usually invoke it with `python3 -m pytest` command; which can often
be called by the `pytest` or `pytest-3` commands (if not, alias them if you
are planning to use them often).

The rest of this README assumes `pytest` works.

## Test selection

A major feature of pytest that irctest heavily relies on is test selection.
Using the `-k` option, you can select and deselect tests based on their names
and/or markers (listed in `pytest.ini`).
For example, you can run `LUSERS`-related tests with `-k lusers`.
Or only tests based on RFC1459 with `-k rfc1459`.

By default, all tests run; even niche ones. So you probably always want to
use these options: `-k 'not Oragono and not deprecated and not strict`.
This excludes:

* `Oragono`-specific tests (included as Oragono uses irctest as its official
  integration test suite)
* tests for deprecated specifications, such as the IRCv3 METADATA
  specification
* tests that check for a strict interpretation of a specification, when
  the specification is ambiguous.

## Run tests

To run (server) tests on Oragono:

```
cd /tmp/
git clone https://github.com/oragono/oragono.git
cd oragono/
make build
make install
cd ~/irctest
pytest --controller irctest.controllers.oragono -k 'not deprecated'
```

To run (server) tests on Solanum:

```
cd /tmp/
git clone https://github.com/solanum-ircd/solanum.git
cd charybdis
./autogen.sh
./configure --prefix=$HOME/.local/
make -j 4
make install
pytest --controller irctest.controllers.solanum -k 'not Oragono and not deprecated and not strict'
```

To run (server) tests on Charybdis::

```
cd /tmp/
git clone https://github.com/atheme/charybdis.git
cd charybdis
./autogen.sh
./configure --prefix=$HOME/.local/
make -j 4
make install
cd ~/irctest
pytest --controller irctest.controllers.charybdis -k 'not Oragono and not deprecated and not strict'
```

To run (server) tests on InspIRCd:

```
cd /tmp/
git clone https://github.com/inspircd/inspircd.git
cd inspircd

# optional, makes tests run considerably faster
patch src/inspircd.cpp < ../irctest/inspircd_mainloop.patch

./configure --prefix=$HOME/.local/ --development
make -j 4
make install
cd ~/irctest
pytest --controller irctest.controllers.inspircd -k 'not Oragono and not deprecated and not strict'
```

To run (server) tests on Mammon:

```
pip3 install --user git+https://github.com/mammon-ircd/mammon.git
cd ~/irctest
pytest --controller irctest.controllers.mammon -k 'not Oragono and not deprecated and not strict'
```

To run (client) tests on Limnoria:

```
pip3 install --user limnoria pyxmpp2-scram
cd ~/irctest
pytest --controller  irctest.controllers.limnoria
```

To run (client) tests on Sopel:

```
pip3 install --user sopel
mkdir ~/.sopel/
cd ~/irctest
pytest --controller irctest.controllers.sopel
```

## What `irctest` is not

A formal proof that a given software follows any of the IRC specification,
or anything near that.

At best, `irctest` can help you find issues in your software, but it may
still have false positives (because it does not implement itself a
full-featured client/server, so it supports only “usual” behavior).
Bug reports for false positives are welcome.

