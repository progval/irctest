# Contributing

## Code style

### Syntax

Any color you like as long as it's [Black](https://github.com/psf/black).
In short:

* 88 columns
* double quotes
* avoid backslashes at line breaks (use parentheses)
* closing brackets/parentheses/... go on the same indent level as the line
  that opened them

We also use `isort` to order imports (in short: just
[follow PEP 8](https://www.python.org/dev/peps/pep-0008/#imports))

You can use [pre-commit](https://pre-commit.com/) to automatically run them
when you create a git commit.
Alternatively, run `pre-commit run -a`


### Naming

[Follow PEP 8](https://www.python.org/dev/peps/pep-0008/#naming-conventions),
with these exceptions:

* assertion methods (eg. `assertMessageMatch` are mixedCase to be consistent
  with the unittest module)
* other methods defined in `cases.py` are also mixedCase for consistency with
  the former, for now
* test names are also mixedCase for the same reason

Additionally:

* test module names should be snake\_case and match the name of the
  specification they are testing (if IRCv3), or the feature they are
  testing (if RFC or just common usage)


## What to test

**All tests should have a docstring** pointing to a reference document
(eg. RFC, IRCv3 specification, or modern.ircdocs.horse).
If there is no reference, documentation can do.

If the behavior being tested is not documented, then **please document it
outside** this repository (eg. at modern.ircdocs.horse),
and/or get it specified through IRCv3.

"That's just how everyone does it" is not good justification.
Linking to an external document saying "Here is how everyone does it" is.

If reference documents / documentations are long or not trivial,
**try to quote the specific part being tested**.
See `irctest/server_tests/test_channel_operations.py` for example.

Tests for **pending/draft specifications are welcome**.

Note that irctest also welcomes implementation-specific tests for
functional testing; for now only Oragono.
This does not relax the requirement on documentating tests.


## Writing tests

**Use unittest-style assertions** (`self.assertEqual(x, y)` instead of
pytest-style (`assert x == y`). This allows consistency with the assertion
methods we define, such as `assertMessageMatch`.

Always **add an error message in assertions**.
`irctest` should show readable errors to people unfamiliar with the
codebase.
Ideally, explain what happened and what should have happened instead.

All tests should be tagged with
`@cases.mark_specifications`.


## Continuous integration

We run automated tests on all commits and pull requests, to check that tests
accept existing implementations.

If an implementation cannot pass a test, that test should be excluded using
the `-k` argument of pytest, in both `README.md` and `.github/workflows/`.
If it is a bug, please open a bug report to the affected software if possible,
and link to the bug report in a comment.
