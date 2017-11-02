# irctest

This software intends to test IRC clients and servers, to ensure that they behave how they're expected to today.

The tests in this repo are based on [RFC 1459](https://tools.ietf.org/html/rfc1459), [RFC 2812](https://tools.ietf.org/html/rfc2812), the [Modern docs](http://modern.ircdocs.horse/) and generally-accepted software behaviour.

This project doesn't contain a lot of test cases. However, it's still useful and can highlight unexpected issues, particularly with newly-developed software.


## Installing

Clone the repo and install the relevant depdencies:

```
git clone https://github.com/DanielOaks/irctest.git
cd irctest
pip3 install --user -r requirements.txt
```


## Running Tests

For almost every client / server, all we require is that the software is installed and the binary is in the PATH.

Here are examples of how to install various software and run tests with them:


### Clients

To run tests on Limnoria:

```
pip3 install --user limnoria
./test.py irctest.controllers.limnoria
```

To run tests on Sopel:

```
pip3 install --user sopel
mkdir ~/.sopel/
./test.py irctest.controllers.sopel
```

To run tests on gIRC:

```
pip3 install --user girc
./test.py irctest.controllers.girc
```


### Servers

To run tests on InspIRCd:

```
cd /tmp/
git clone https://github.com/inspircd/inspircd.git
cd inspircd
./configure --prefix=$HOME/.local/ --development
make -j 4
make install
./test.py irctest.controllers.inspircd
```

To run tests on Mammon:

```
pip3 install --user git+https://github.com/mammon-ircd/mammon.git
./test.py irctest.controllers.mammon
```

To run tests on Hybrid:

```
cd /tmp/
git clone https://github.com/ircd-hybrid/ircd-hybrid.git
cd ircd-hybrid
./configure --prefix=$HOME/.local/
make -j 4
make install
./test.py irctest.controllers.hybrid
```

To run tests on Charybdis:

```
cd /tmp/
git clone https://github.com/atheme/charybdis.git
cd charybdis
./configure --prefix=$HOME/.local/
make -j 4
make install
./test.py irctest.controllers.charybdis
```

To run tests on Oragono:

Download [latest release](https://github.com/DanielOaks/oragono/releases/latest) and extract into your PATH, then:

```
./test.py irctest.controllers.oragono
```


## Program Help

For more complete help, run `./test --help`


## What this is not

This isn't a formal proof that a given piece of IRC software follows the IRC specs to the letter, or is definitely going to be interoperable with other software.

This is just intended to help you find issues with your software.
