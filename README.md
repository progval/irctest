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


Install dependencies:

```
pip3 install --user -r requirements.txt
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
wget git clone git@github.com:inspircd/inspircd.git
cd inspircd
./configure --prefix=$HOME/.local/ --development
make -j 4
make install
python3 -m irctest irctest.controllers.inspircd
```
```
