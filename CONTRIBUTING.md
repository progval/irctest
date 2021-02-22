# Contributing

## Code style

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
