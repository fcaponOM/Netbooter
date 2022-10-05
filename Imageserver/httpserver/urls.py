from django.urls import path
from django.contrib import admin
from rest_framework.urlpatterns import format_suffix_patterns
from . import views

urlpatterns = [
    path('images/', views.ImageList.as_view()),
    path('images/<slug:version>/', views.ImageDetail.as_view()),
    path('', admin.site.urls)
]

urlpatterns = format_suffix_patterns(urlpatterns)