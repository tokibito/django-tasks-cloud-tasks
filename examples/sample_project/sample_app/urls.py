"""Sample App URL configuration"""

from django.urls import path

from .views import (
    IndexView,
    EnqueueAddView,
    EnqueueNotifyView,
    EnqueueProcessView,
    EnqueueUrgentView,
    EnqueueContextView,
    EnqueueFailingView,
)

urlpatterns = [
    path("", IndexView.as_view(), name="index"),
    path("enqueue/add/", EnqueueAddView.as_view(), name="enqueue_add"),
    path("enqueue/notify/", EnqueueNotifyView.as_view(), name="enqueue_notify"),
    path("enqueue/process/", EnqueueProcessView.as_view(), name="enqueue_process"),
    path("enqueue/urgent/", EnqueueUrgentView.as_view(), name="enqueue_urgent"),
    path("enqueue/context/", EnqueueContextView.as_view(), name="enqueue_context"),
    path("enqueue/failing/", EnqueueFailingView.as_view(), name="enqueue_failing"),
]
