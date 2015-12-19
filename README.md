# irctest

This project aims at testing interoperability of software using the
IRC protocol, by running them against test suites and making different
software communicate with each other.

It is very young and does not contain a lot of test cases yet.

## The big picture

This project contains:

* IRC protocol test cases (only for clients for the moment)
* small wrappers around existing software to run tests on them
  (only Limnoria and Sopel for the moment)

## How to use it

First, install dependencies:

```
pip3 install --user -r requirements.txt
```

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
