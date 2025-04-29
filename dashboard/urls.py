from . import views
from django.urls import path
from .views import general_dashboard, create_user, run_script

app_name = 'dashboard'

urlpatterns = [
    path('', general_dashboard, name='general_dashboard'),
    path('user/<int:user_id>/dashboard/', views.user_dashboard, name='user_dashboard'),
    path('dashboard/create_user/', create_user, name='create_user'),
    path('run_script/', run_script, name='run_script'),
    path('user/<int:user_id>/change-password/', views.change_password, name='change_password'),
    path('user/<int:user_id>/delete-user/', views.delete_user, name='delete_user'),

]
