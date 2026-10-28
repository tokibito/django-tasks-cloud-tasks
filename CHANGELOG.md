# Changelog

## Unreleased

### Added

- Django 6.1 is supported and tested alongside Django 6.0, on Python 3.12
  to 3.14. ([#1](https://github.com/tokibito/django-tasks-cloud-tasks/pull/1))

### Changed

- **Security: the execute endpoint verifies the OIDC token whenever the
  backend has a service account.** Before, `POST /cloudtasks/execute/`
  checked a token only when the `CLOUD_TASKS_OIDC_AUDIENCE` Django setting
  was set, which the README did not mention: a project that followed the
  README's *OIDC Authentication* section had Cloud Tasks send a token that
  nobody checked, and an endpoint that ran any task for any request. On
  Cloud Run and App Engine the service account is detected from the
  metadata server, so that was every deployment there that did not set the
  setting. The endpoint now verifies the token whenever the `default`
  backend has `OIDC_SERVICE_ACCOUNT_EMAIL`, set or detected, against the
  backend's `OIDC_AUDIENCE`, the audience Cloud Tasks sends the token with.
  Requests from Cloud Tasks are unaffected. A request without a valid
  token, such as one sent by hand or by a scheduler, is now refused with
  `401`. `CLOUD_TASKS_OIDC_AUDIENCE` keeps working and takes precedence. A
  project whose Cloud Tasks backend is not the `default` alias names it
  with `ExecuteTaskView.as_view(backend_alias=...)`. Without a service
  account, as in local development, the endpoint stays open, as before.
  ([#7](https://github.com/tokibito/django-tasks-cloud-tasks/issues/7))

- **A failed task's traceback is no longer in the response of the execute
  endpoint.** The `500` response listed `errors[].traceback`, which Cloud
  Tasks does not keep and anyone who can reach the endpoint could read. The
  response now carries the exception class in `errors[].exception` and the
  `task_id`. The traceback is in the log, in the `ERROR` record of Django's
  `django.tasks` logger, as it was before; the README's *Logging* section
  says so and shows how to attach a handler to that logger, which Django's
  default configuration leaves without one when `DEBUG` is off. A caller
  that read the traceback from the response reads the log instead.
  ([#11](https://github.com/tokibito/django-tasks-cloud-tasks/issues/11))

### Fixed

- A token that failed OIDC verification was reported twice: once through
  the `django_tasks_cloud_tasks` logger and once more as a plain line on
  stderr, which Cloud Run and App Engine send to Cloud Logging. It is now
  logged once, through the logger. The README has a new *Logging* section
  naming the logger.
  ([#17](https://github.com/tokibito/django-tasks-cloud-tasks/issues/17))
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
- The README no longer lists priority as a feature or shows tasks with a
  priority. The backend has never supported it, since Cloud Tasks has no
  task priority, and Django rejects such a task when it is defined. The
  README now says so and points to a separate queue for urgent work.
  ([#3](https://github.com/tokibito/django-tasks-cloud-tasks/issues/3))
- This file, which is now included in the source distribution.
  ([#23](https://github.com/tokibito/django-tasks-cloud-tasks/issues/23))
- The README states google-cloud-tasks and google-auth as dependencies of
  the package. It showed them as a separate install, which installed
  nothing more.
  ([#22](https://github.com/tokibito/django-tasks-cloud-tasks/issues/22))

## 0.1.0

Initial release: a task backend for Django 6.0's task framework on Google
Cloud Tasks. Tasks are enqueued as HTTP tasks carrying their arguments in
the payload and run by the `/cloudtasks/execute/` endpoint when Cloud Tasks
calls it, with optional OIDC token verification on that endpoint, delayed execution
through `run_after`, and detection of the project, location and handler
host on Cloud Run and App Engine.
