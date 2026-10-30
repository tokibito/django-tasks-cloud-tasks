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

- **`enqueue()` reuses one Cloud Tasks client per backend.** It created a
  `CloudTasksClient` on every call, opening a gRPC channel and loading
  credentials each time, and never closed the channels. The backend now
  creates the client on first use and keeps it, as the `client` property;
  Django keeps a backend per thread, so that is one client per thread.
  `close()` closes the channel, and the next enqueue opens a new one. A
  subclass or a test can replace the client by overriding the property.
  ([#12](https://github.com/tokibito/django-tasks-cloud-tasks/issues/12))

### Deprecated

- **`CLOUD_RUN_REGION`.** Cloud Run does not set this environment variable,
  and the region is now detected from the metadata server. It is still read
  for the location and the handler host, with a `DeprecationWarning`, and
  will not be read from 0.3.0. Set `CLOUD_TASKS_LOCATION` or `SERVICE_URL`
  instead. Existing projects need no change until then.
  ([#4](https://github.com/tokibito/django-tasks-cloud-tasks/issues/4))

### Fixed

- **On Cloud Run, the detected handler host did not exist.** Without
  `SERVICE_URL`, the host was built from the project ID, where Cloud Run's
  URL has the project number, and with the revision as a prefix, which is
  the URL of a traffic tag nobody created; and it was only built at all
  when `CLOUD_RUN_REGION`, which Cloud Run does not set, was set by hand.
  It is now `https://SERVICE-PROJECT_NUMBER.REGION.run.app`, from
  `K_SERVICE` and the project number and region from the metadata server.
  On Cloud Run the location is detected from the service's region too.
  Projects that set `TASK_HANDLER_HOST` or `SERVICE_URL` see no change; the
  README says how to pin tasks to a revision with a traffic tag.
  ([#4](https://github.com/tokibito/django-tasks-cloud-tasks/issues/4))
- **On App Engine, a service other than `default` enqueued tasks to the
  default service.** The detected `TASK_HANDLER_HOST` was built from
  `GAE_VERSION` and the project only, which is the default service's URL,
  so Cloud Tasks sent the tasks of, say, an `api` service to whatever runs
  as `default`. A non-default service now gets
  `https://VERSION-dot-SERVICE-dot-PROJECT.appspot.com`, as in
  django-database-task. Projects on the default service, and projects that
  set `TASK_HANDLER_HOST` or `SERVICE_URL`, see no change.
  ([#5](https://github.com/tokibito/django-tasks-cloud-tasks/issues/5))
- **A task whose function could not be imported left no trace but a
  generic error.** When the module was renamed, the function removed, or
  the revision serving the request ran older code than the one that
  enqueued the task, the endpoint logged `Task execution failed` with no
  task fields and answered `500` with the exception text. It is now
  reported like a task that raised: an `ERROR` record
  `Task could not be started: id=... path=... error=...`, with the
  traceback and the Cloud Tasks headers, and a `500` response in the usual
  failure shape, `{"status": "failed", "task_id": ..., "errors": [...]}`. A
  `task_path` that names something other than a task is handled the same
  way. The answer stays `500`, so Cloud Tasks keeps retrying and a revision
  that has the code can pick the task up. `task_started` and
  `task_finished` are not sent for it, since Django's own receivers need
  the task, as in django-database-task.
  ([#9](https://github.com/tokibito/django-tasks-cloud-tasks/issues/9))
- **A payload with a missing field answered `500`.** A body that parsed as
  JSON but lacked a required field, had one of the wrong type or was not an
  object raised inside the executor and was answered `500` with the
  exception text. The endpoint now checks the payload first and answers
  `400` with `{"error": "Invalid payload", "detail": ...}` naming the field,
  and logs an `ERROR` record with the cause, the task as far as it can be
  read, the payload's keys and the Cloud Tasks headers. Cloud Tasks retries
  a `400` as it does a `500`; the gain is the answer and the log, which now
  say what is wrong. Valid requests are unchanged.
  ([#10](https://github.com/tokibito/django-tasks-cloud-tasks/issues/10))
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

- The emulator steps in the README, `examples/README.md` and the sample
  project's page use
  [aertje/cloud-tasks-emulator](https://github.com/aertje/cloud-tasks-emulator).
  They described `gcloud beta emulators tasks` and
  `gcloud components install cloud-tasks-emulator`, which do not exist.
  ([#6](https://github.com/tokibito/django-tasks-cloud-tasks/issues/6))
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
