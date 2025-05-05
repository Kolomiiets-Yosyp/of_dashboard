from . import views
from django.urls import path
from .views import *

app_name = 'dashboard'

urlpatterns = [
    path('', general_dashboard, name='general_dashboard'),
    path('user/<int:user_id>/dashboard/', views.user_dashboard, name='user_dashboard'),
    path('dashboard/create_user/', create_user, name='create_user'),
    path('run_script/', run_script, name='run_script'),
    path('user/<int:user_id>/change-password/', views.change_password, name='change_password'),
    path('user/<int:user_id>/delete-user/', views.delete_user, name='delete_user'),
    path('assistants/', assistants_view, name='assistants'),
    path('assistant/delete/<int:assistant_id>/', delete_assistant, name='delete_assistant'),
    path('assistant/edit/<int:assistant_id>/', edit_assistant, name='edit_assistant'),
    path('tag/delete/<int:tag_id>/', delete_tag, name='delete_tag'),
    path('tag/edit/<int:tag_id>/', edit_tag, name='edit_tag'),
]
