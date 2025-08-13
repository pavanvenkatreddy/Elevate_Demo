from django.urls import path
from . import views

urlpatterns = [
    path('quote/', views.quote_view, name='quote'),
    path('chat/', views.chat_view, name='chat'),
    path('status/', views.status_view, name='status'),
]
