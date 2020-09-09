# irctest

This is the integration test suite for Oragono, ultimately derived from [ProgVal/irctest](https://github.com/ProgVal/irctest), which is a general-purpose IRC protocol compatibility testing suite.

Some of these tests may be applicable to other projects (we attempt to mark the tests that are only applicable to Oragono).

This suite needs more test cases. Contributions are welcome and are a great way to help the Oragono project!

## Installing

Clone the repo and install the relevant dependencies:

```
virtualenv ./venv
source ./venv/bin/activate
pip install -r requirements.txt
```

## Running Tests

Make sure the version of `oragono` you want to test is on your PATH. Then run `make`.
