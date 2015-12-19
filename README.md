# irctest

This project aims at testing interoperability of software using the
IRC protocol, by running them against test suites and making different
software communicate with each other.

It is very young and does not contain a lot of test cases yet.

## The big picture

This project contains:

* IRC protocol test cases
* small wrappers around existing software to run tests on them
  (only Limnoria, Sopel, and InspIRCd for the moment)

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

To run tests with Limnoria:

```
pip3 install --user limnoria
python3 -m irctest irctest.controllers.limnoria
```

To run tests with Sopel:

```
pip3 install --user sopel
mkdir ~/.sopel/
python3 -m irctest irctest.controllers.sopel
```

To run tests with InspIRCd:

```
cd /tmp/
git clone https://github.com/inspircd/inspircd.git
cd inspircd
./configure --prefix=$HOME/.local/ --development
make -j 4
make install
python3 -m irctest irctest.controllers.inspircd
```

## What `irctest` is not

A formal proof that a given software follows any of the IRC specification,
or anything near that.

At best, `irctest` can help you find issues in your software, but it may
still have false positives (because it does not implement itself a
full-featured client/server, so it supports only “usual” behavior).
