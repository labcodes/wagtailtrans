from django.urls import path

from wagtailtrans.views.translation import TranslationView

app_name = 'wagtailtrans'

urlpatterns = [
    path('<int:instance_id>/add/<str:language_code>/', TranslationView.as_view(), name='add'),
]
