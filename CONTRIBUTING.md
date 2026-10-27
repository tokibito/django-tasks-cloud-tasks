# Contributing

Thanks for your interest in django-tasks-cloud-tasks.

Issues and pull requests are welcome at
<https://github.com/tokibito/django-tasks-cloud-tasks>. Everything that lands
in the repository — code, comments, docstrings, commit messages, pull request
descriptions and documentation — is written in English.

## Getting set up

Python 3.12 or newer and Django 6.0 or newer. The tests need no Google Cloud
project, no credentials and no Cloud Tasks emulator.

```bash
git clone https://github.com/tokibito/django-tasks-cloud-tasks.git
cd django-tasks-cloud-tasks

python -m venv venv
venv/bin/pip install -e ".[dev]"
```

## Running the tests

```bash
venv/bin/pytest
```

Tests use pytest-django with the settings in `tests/settings.py`, which
configure the backend with a fixed project, location and handler host. The
tests that enqueue a task patch `CloudTasksClient`, so no request reaches
Google Cloud; the tests that run a task post its payload to the execute
view, or hand it to the executor, the way Cloud Tasks would. The detection
tests set the environment variables they need and patch the metadata server
lookup.

One lookup is not patched: with `OIDC_SERVICE_ACCOUNT_EMAIL` unset, the
backend asks the metadata server for the default service account when it is
created. Outside Google Cloud the name `metadata.google.internal` does not
resolve and the lookup gives up at once. On a machine where it resolves but
does not answer, each lookup waits for its 2 second timeout, so the suite is
slow there, but it still passes.

Each test module passes when run on its own, so you can run part of the
suite:

```bash
venv/bin/pytest tests/test_backends.py
venv/bin/pytest tests/test_views.py
venv/bin/pytest -k "detect"
```

CI runs the suite against Python 3.12 to 3.14 and Django 6.0 and 6.1. To
catch Django's deprecations early, run it once with them turned into
errors:

```bash
venv/bin/pytest -W error::DeprecationWarning
```

## Linting and formatting

```bash
venv/bin/ruff check .
venv/bin/ruff format .
```

Both have to pass; CI runs `ruff format --check`, which fails on unformatted
code rather than fixing it. The `dev` extra pins the Ruff version CI uses, so
a fresh `pip install -e ".[dev]"` gives you the same one. The Markdown files
are outside Ruff's scope, so the code blocks in the README keep the layout
they were written with.

## Making a change

A few things are easy to forget:

- **The changelog.** Add a line to the *Unreleased* section of
  `CHANGELOG.md`, under *Added*, *Changed*, *Deprecated*, *Removed*, *Fixed*
  or *Documentation*, saying what a user of the package will notice. Leave
  `version` in `pyproject.toml` and `__version__` in
  `django_tasks_cloud_tasks/__init__.py` alone; releases are cut separately.

- **The README.** New options, settings, environment variables and
  endpoints are documented there. Its diagrams are mermaid, rendered by
  GitHub. The sample project has its own walkthrough in
  `examples/README.md`; a change to an option or to the endpoint usually
  shows up in both.

- **The task payload.** The JSON body the backend gives Cloud Tasks is what
  the execute endpoint reads back, possibly much later: a queue can hold a
  task for days, and retries it for as long as its retry configuration
  allows. A change to a field in the payload needs a path for tasks that
  were enqueued by the previous version and are still in the queue when the
  service is upgraded.

### Backwards compatibility

Projects depend on the keys in `OPTIONS` and their defaults, the top-level
settings such as `CLOUD_TASKS_OIDC_AUDIENCE`, the environment variables the
auto-detection reads, and the URL of the execute endpoint, so a change to
any of them needs a path that keeps working for someone who upgrades without
reading the release notes. Where something has to go, deprecate it first:
keep it working with a `DeprecationWarning` that names the version it is
removed in. A new option defaults to the behaviour the package had without
it.

Authentication deserves the most care. A change that makes the execute
endpoint accept a request it rejected before, for any configuration, is
treated as a breaking change.

The tests are the safety net for this. When a refactor leaves the existing
tests passing unmodified, that is the evidence that behaviour did not change.

## Trying it against a real service

The sample project in `examples/` is the place to run a change end to end
against something other than the test suite: a development server with a
page that enqueues tasks, against a Cloud Tasks queue in a Google Cloud
project, and the execute endpoint that can be called by hand with `curl` the
way Cloud Tasks would call it. `examples/README.md` walks through it.

## Pull requests

- Branch off `main`.
- **One purpose per pull request.** See below.
- Say what the change is for. A description that explains the problem is worth
  more than one that restates the diff.
- Keep the tests and the linters green.
- Add tests for a behaviour change. A bug fix wants the test that fails
  without it.

### Split by purpose

A pull request should answer one question, so that a reviewer can hold that
question in their head while reading all of it. Several purposes in one branch
means none of them gets read properly, and the risky part hides among the safe
parts.

Split it when a branch contains any of these:

- **A refactor and the feature it makes possible.** Send the refactor first,
  where the existing tests passing unmodified is the whole argument, and build
  on it afterwards. Mixed together, that evidence is gone.
- **A fix for something you noticed on the way.** Worth having, and worth
  having on its own, where it can be reviewed and reverted by itself.
- **Mechanical churn beside a real change.** Reformatting, renaming, tidying
  imports and dependency bumps drown the few lines that matter.
- **Steps that make sense in sequence.** A change to the payload, the
  executor that reads it, the option that exposes it and the documentation
  can each be a pull request, each mergeable and reviewable on its own.

This holds however the change was produced, including with the help of an AI
tool. A branch that grew in one sitting still has to arrive as the sequence of
changes a reviewer can follow; splitting it afterwards is part of the work, not
an optional tidy-up.

A change that genuinely is one purpose can still be large, and that is fine.
The test is whether the description needs the word "and".
