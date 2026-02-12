# irctest

This project aims at testing interoperability of software using the
IRC protocol, by running them against common test suites.

It is also used while editing [the "Modern" specification](https://modern.ircdocs.horse/)
to check behavior of a large selection of servers at once.

## The big picture

This project contains:

* IRC protocol test cases, primarily checking conformance to
  [the "Modern" specification](https://modern.ircdocs.horse/) and
  [IRCv3 extensions](https://ircv3.net/irc/), but also
  [RFC 1459](https://datatracker.ietf.org/doc/html/rfc1459) and
  [RFC 2812](https://datatracker.ietf.org/doc/html/rfc2812).
  Most of them are for servers but also some for clients.
  Only the client-server protocol is tested; server-server protocols are out of scope.
* Small wrappers around existing software to run tests on them.
  So far this is restricted to headless software (servers, service packages,
  and clients bots).

Wrappers run software in temporary directories, so running `irctest` should
have no side effect.

Test results for the latest version of each supported software, and respective logs,
are [published daily](https://dashboard.irctest.limnoria.net/).

## Prerequisites

Install irctest and dependencies:

```
sudo apt install faketime  # Optional, but greatly speeds up irctest/server_tests/list.py
cd ~
git clone https://github.com/progval/irctest.git
cd irctest
pip3 install --user -r requirements.txt
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

After installing `pytest-xdist`, you can also pass `pytest` the `-n 10` option
to run `10` tests in parallel.

The rest of this README assumes `pytest` works.

## Test selection

A major feature of pytest that irctest heavily relies on is test selection.
Using the `-k` option, you can select and deselect tests based on their names
For example, you can run `LUSERS`-related tests with `-k lusers`.

Using the `-m` option, you can select and deselect and them based on their markers
(listed in `pytest.ini`).
For example, you can run only tests based on RFC1459 with `-m rfc1459`.

By default, all tests run; even niche ones. So you probably always want to
use these options: `-m 'not Ergo and not deprecated and not strict`.
This excludes:

* `Ergo`-specific tests (included as Ergo uses irctest as its official
  integration test suite)
* tests for deprecated specifications, such as the IRCv3 METADATA
  specification
* tests that check for a strict interpretation of a specification, when
  the specification is ambiguous.

## Running tests

This list is non-exhaustive, see `workflows.yml` for software not listed here.
If software you want to test is not listed their either, please open an issue
or pull request to add support for it.

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

#### InspIRCd:

```
cd /tmp/
git clone https://github.com/inspircd/inspircd.git
cd inspircd

# Optional, makes tests run considerably faster.
export CXXFLAGS=-DINSPIRCD_UNLIMITED_MAINLOOP

./configure --prefix=$HOME/.local/ --development
make -j 4
make install
cd ~/irctest
pytest --controller irctest.controllers.inspircd -k 'not Ergo and not deprecated and not strict'
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

Besides Ergo (that has built-in services) and Sable (that ships its own services),
most server controllers can optionally run service packages.

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

