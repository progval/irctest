# irctest

This project aims at testing interoperability of software using the
IRC protocol, by running them against common test suites.

## The big picture

This project contains:

* IRC protocol test cases
* small wrappers around existing software to run tests on them

Wrappers run software in temporary directories, so running `irctest` should
have no side effect.

## Prerequisites

Install irctest and dependencies:

```
cd ~
git clone https://github.com/ProgVal/irctest.git
cd irctest
pip3 install --user -r requirements.txt
python3 setup.py install --user
```

Add `~/.local/bin/` (and/or `~/go/bin/` for Ergo)
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
use these options: `-k 'not Ergo and not deprecated and not strict`.
This excludes:

* `Ergo`-specific tests (included as Ergo uses irctest as its official
  integration test suite)
* tests for deprecated specifications, such as the IRCv3 METADATA
  specification
* tests that check for a strict interpretation of a specification, when
  the specification is ambiguous.

## Running tests

### Servers

#### Ergo:

```
cd /tmp/
git clone https://github.com/ergochat/ergo.git
cd ergo/
make install
cd ~/irctest
pytest --controller irctest.controllers.ergo -k 'not deprecated'
```

#### Solanum:

```
cd /tmp/
git clone https://github.com/solanum-ircd/solanum.git
cd solanum
./autogen.sh
./configure --prefix=$HOME/.local/
make -j 4
make install
pytest --controller irctest.controllers.solanum -k 'not Ergo and not deprecated and not strict'
```

#### Charybdis:

```
cd /tmp/
git clone https://github.com/atheme/charybdis.git
cd charybdis
./autogen.sh
./configure --prefix=$HOME/.local/
make -j 4
make install
cd ~/irctest
pytest --controller irctest.controllers.charybdis -k 'not Ergo and not deprecated and not strict'
```

#### InspIRCd:

```
cd /tmp/
git clone https://github.com/inspircd/inspircd.git
cd inspircd

# optional, makes tests run considerably faster
patch src/inspircd.cpp < ~/irctest/inspircd_mainloop.patch

./configure --prefix=$HOME/.local/ --development
make -j 4
make install
cd ~/irctest
pytest --controller irctest.controllers.inspircd -k 'not Ergo and not deprecated and not strict'
```

#### Mammon:

```
pip3 install --user git+https://github.com/mammon-ircd/mammon.git
cd ~/irctest
pytest --controller irctest.controllers.mammon -k 'not Ergo and not deprecated and not strict'
```

#### UnrealIRCd:

```
cd /tmp/
git clone https://github.com/unrealircd/unrealircd.git
cd unrealircd
./Config  # This will ask a few questions, answer them.
make -j 4
make install
cd ~/irctest
pytest --controller irctest.controllers.unreal -k 'not Ergo and not deprecated and not strict'
```


### Servers with services

Besides Ergo (that has built-in services), most server controllers can optionally run
service packages.

#### Atheme:

You can install it with

```
sudo apt install atheme-services
```

and add this to the `pytest` call:

```
--services-controller irctest.controllers.atheme_services
```

#### Anope:

Build with:

```
cd /tmp/
git clone https://github.com/anope/anope.git
cd anope
./Config  # This will ask a few questions, answer them.
make -C build -j 4
make -C build install
```

and add this to the `pytest` call:

```
--services-controller irctest.controllers.anope_services
```


### Clients

#### Limnoria:

```
pip3 install --user limnoria pyxmpp2-scram
cd ~/irctest
pytest --controller  irctest.controllers.limnoria
```

#### Sopel:

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

