# Package

# TEsting

1. LWets review all the tests and try to remove unittest use wherever possible
- use pytest or pytest related packages (e.g. pytest-mock)

2. consider if the hypothesis testing package would provide any additional benefit

# Linting and Formatting

1. Lets use astrals ruff for formatting
- docs: https://docs.astral.sh/ruff/
- github: https://github.com/astral-sh/ruff

2. lets use astrals ty for linting and type checking
- docs: https://docs.astral.sh/ty/
- github: https://github.com/astral-sh/ty

# Misc

1. README updates for the new `configure()` API

2. cloufbuild and CI/CD planning
- how to setup cloud build
- how to install from cloud build when on a local machine using uv
- should we make this a public package and pass the client secrets so that this is the public entry into the auth side of everythiong on a client machine?