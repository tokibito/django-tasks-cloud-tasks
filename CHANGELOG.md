# Changelog

## Unreleased

### Added

- Django 6.1 is supported and tested alongside Django 6.0, on Python 3.12
  to 3.14. ([#1](https://github.com/tokibito/django-tasks-cloud-tasks/pull/1))

### Fixed

- The source distribution carries the whole test suite. It had the test
  modules but not `tests/settings.py` and `tests/tasks.py`, so the tests in
  it could not run.

### Documentation

- The architecture diagram in the README shows the result of `enqueue()`
  in `READY`, the status the backend returns. It said `NEW`, which
  `TaskResultStatus` does not have.
  ([#21](https://github.com/tokibito/django-tasks-cloud-tasks/issues/21))
- `CONTRIBUTING.md`, covering the development setup, running the tests and
  the linters, and what a pull request needs.
  ([#23](https://github.com/tokibito/django-tasks-cloud-tasks/issues/23))
- This file, which is now included in the source distribution.
  ([#23](https://github.com/tokibito/django-tasks-cloud-tasks/issues/23))

## 0.1.0

Initial release: a task backend for Django 6.0's task framework on Google
Cloud Tasks. Tasks are enqueued as HTTP tasks carrying their arguments in
the payload and run by the `/cloudtasks/execute/` endpoint when Cloud Tasks
calls it, with optional OIDC token verification on that endpoint, delayed execution
through `run_after`, and detection of the project, location and handler
host on Cloud Run and App Engine.
