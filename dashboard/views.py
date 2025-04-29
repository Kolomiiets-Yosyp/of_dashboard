from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Sum, Max
from django.db.models.functions import TruncDate
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from .models import Notification, PostStatistic, ScheduledPost, Users, PostTags


def get_date_range(days=10):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date


def create_chart(df, title, y_label):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['value'], mode='lines+markers'))
    fig.update_layout(
        title=title,
        xaxis_title='Date',
        yaxis_title=y_label,
        template='plotly_white'
    )
    return fig.to_html(full_html=False)


def dashboard(request):
    start_date, end_date = get_date_range()

    # Posts statistics
    posts_stats = PostStatistic.objects.filter(
        date__range=[start_date.date(), end_date.date()]
    ).order_by('date')
    posts_df = pd.DataFrame(list(posts_stats.values('date', 'post_count')))
    if not posts_df.empty:
        posts_df.set_index('date', inplace=True)
        posts_df.rename(columns={'post_count': 'value'}, inplace=True)
        posts_chart = create_chart(posts_df, 'Posts Made Over Time', 'Number of Posts')
    else:
        posts_chart = None

    # Followers statistics
    followers = Notification.objects.filter(
        notification_type='subscribed',
        notification_time__range=[start_date, end_date]
    ).annotate(
        date=TruncDate('notification_time')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')

    followers_df = pd.DataFrame(list(followers))
    if not followers_df.empty:
        followers_df.set_index('date', inplace=True)
        followers_df.rename(columns={'count': 'value'}, inplace=True)
        followers_chart = create_chart(followers_df, 'New Followers Over Time', 'Number of Followers')
    else:
        followers_chart = None

    # Tags statistics
    tags = Notification.objects.filter(
        notification_type='tags',
        notification_time__range=[start_date, end_date]
    ).annotate(
        date=TruncDate('notification_time')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')

    tags_df = pd.DataFrame(list(tags))
    if not tags_df.empty:
        tags_df.set_index('date', inplace=True)
        tags_df.rename(columns={'count': 'value'}, inplace=True)
        tags_chart = create_chart(tags_df, 'Mentions Over Time', 'Number of Mentions')
    else:
        tags_chart = None

    # Today's statistics
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    posts_today = PostStatistic.objects.filter(date=today).first()
    posts_today = posts_today.post_count if posts_today else 0

    scheduled_yesterday = ScheduledPost.objects.filter(date=yesterday).first()
    scheduled_yesterday = scheduled_yesterday.post_count if scheduled_yesterday else 0

    posts_difference = posts_today - scheduled_yesterday
    if posts_difference < 0 or posts_difference == 0:
        posts_difference = scheduled_yesterday
    scheduled_posts = ScheduledPost.objects.filter(
        date__gte=today
    ).order_by('date')

    followers_today = Notification.objects.filter(
        notification_type='subscribed',
        notification_time__date=today
    ).count()

    followers_yesterday = Notification.objects.filter(
        notification_type='subscribed',
        notification_time__date=yesterday
    ).count()

    tags_today = Notification.objects.filter(
        notification_type='tags',
        notification_time__date=today
    ).count()

    context = {
        'posts_difference': posts_difference,
        'scheduled_posts': scheduled_posts,
        'followers_today': followers_today,
        'followers_yesterday': followers_yesterday,
        'tags_today': tags_today,
        'posts_chart': posts_chart,
        'followers_chart': followers_chart,
        'tags_chart': tags_chart,
    }

    return render(request, 'dashboard/dashboard.html', context)

def user_dashboard(request, user_id):
    print("&&&&&&&")
    user = get_object_or_404(Users, pk=user_id)
    start_date, end_date = get_date_range()
    # Posts statistics for the specific user
    posts_stats = PostStatistic.objects.filter(user=user, date__range=[start_date.date(), end_date.date()])
    posts_df = pd.DataFrame(list(posts_stats.values('date', 'post_count')))
    if not posts_df.empty:
        posts_df.set_index('date', inplace=True)
        posts_df.rename(columns={'post_count': 'value'}, inplace=True)
        posts_chart = create_chart(posts_df, f"Posts Made by {user.login} Over Time", 'Number of Posts')
    else:
        posts_chart = None

    # Followers statistics for the specific user
    followers = Notification.objects.filter(
        user=user,
        notification_type='subscribed',
        notification_time__range=[start_date, end_date]
    ).annotate(
        date=TruncDate('notification_time')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')

    followers_df = pd.DataFrame(list(followers))
    if not followers_df.empty:
        followers_df.set_index('date', inplace=True)
        followers_df.rename(columns={'count': 'value'}, inplace=True)
        followers_chart = create_chart(followers_df, f"New Followers of {user.login} Over Time", 'Number of Followers')
    else:
        followers_chart = None

    # Tags statistics for the specific user
    tags = Notification.objects.filter(
        user=user,
        notification_type='tags',
        notification_time__range=[start_date, end_date]
    ).annotate(
        date=TruncDate('notification_time')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')

    tags_df = pd.DataFrame(list(tags))
    if not tags_df.empty:
        tags_df.set_index('date', inplace=True)
        tags_df.rename(columns={'count': 'value'}, inplace=True)
        tags_chart = create_chart(tags_df, f"Mentions of {user.login} Over Time", 'Number of Mentions')
    else:
        tags_chart = None

    # Today's statistics for the specific user
    today = datetime.now().date()
    posts_today = PostStatistic.objects.filter(user=user, date=today).first()
    posts_today = posts_today.post_count if posts_today else 0

    scheduled_yesterday = ScheduledPost.objects.filter(user=user, date=today - timedelta(days=1)).first()
    scheduled_yesterday = scheduled_yesterday.post_count if scheduled_yesterday else 0

    posts_difference = posts_today - scheduled_yesterday
    if posts_difference < 0 or posts_difference == 0:
        posts_difference = scheduled_yesterday

    # Get scheduled posts data for the specific user
    scheduled_posts = ScheduledPost.objects.filter(user=user, date__gte=today).order_by('date')

    # Followers and Tags today
    followers_today = Notification.objects.filter(
        user=user,
        notification_type='subscribed',
        notification_time__date=today
    ).count()

    tags_today = Notification.objects.filter(
        user=user,
        notification_type='tags',
        notification_time__date=today
    ).count()
    post_tags = set(PostTags.objects.filter(user=user).values_list('tag_username', flat=True))
    notification_tags = set(Notification.objects.filter(
        user=user,
        notification_type='tags'
    ).values_list('username', flat=True))

    # Об'єднуємо всі теги і сортуємо їх
    post_tags_data = PostTags.objects.filter(user=user).values(
        'tag_username'
    ).annotate(
        last_time=Max('post_time')
    ).order_by('tag_username')

    # Отримуємо теги зі сповіщень з часом останньої появи
    notification_tags_data = Notification.objects.filter(
        user=user,
        notification_type='tags'
    ).values(
        'username'
    ).annotate(
        last_time=Max('notification_time')
    ).order_by('username')

    # Створюємо словники для швидкого доступу
    post_tags = {item['tag_username']: item['last_time'] for item in post_tags_data}
    notification_tags = {item['username']: item['last_time'] for item in notification_tags_data}

    # Об'єднуємо всі теги
    all_tags = sorted(set(post_tags.keys()).union(set(notification_tags.keys())))

    # Формуємо дані для таблиці
    tags_comparison = []
    for tag in all_tags:
        post_time = post_tags.get(tag)
        notification_time = notification_tags.get(tag)

        tags_comparison.append({
            'tag': tag,
            'post_time': post_time,
            'notification_time': notification_time,
            'post_class': 'bg-success' if post_time else '',
            'notification_class': 'bg-success' if notification_time else '',
            'post_missing': not post_time and notification_time,
            'notification_missing': post_time and not notification_time
        })
    context = {
        'user': user.name,
        'id': user.id,
        'posts_difference': posts_difference,
        'scheduled_posts': scheduled_posts,
        'followers_today': followers_today,
        'tags_today': tags_today,
        'posts_chart': posts_chart,
        'followers_chart': followers_chart,
        'tags_chart': tags_chart,
        'tags_comparison': tags_comparison,
        'post_tags_count': len(post_tags),
        'notification_tags_count': len(notification_tags),
        'common_tags_count': len(set(post_tags.keys()) & set(notification_tags.keys())),
    }

    return render(request, 'dashboard/user_dashboard.html', context)


def general_dashboard(request):
    start_date, end_date = get_date_range()
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    # Users statistics
    users = Users.objects.all()
    user_data = []

    for user in users:
        # Posts statistics
        posts_stats = PostStatistic.objects.filter(
            user=user, date__range=[start_date.date(), end_date.date()]
        ).order_by('date')
        posts_df = pd.DataFrame(list(posts_stats.values('date', 'post_count')))
        if not posts_df.empty:
            posts_df.set_index('date', inplace=True)
            posts_df.rename(columns={'post_count': 'value'}, inplace=True)
            posts_chart = create_chart(posts_df, f"Posts Made by {user.login} Over Time", 'Number of Posts')
        else:
            posts_chart = None

        # Followers statistics
        followers = Notification.objects.filter(
            user=user,
            notification_type='subscribed',
            notification_time__range=[start_date, end_date]
        ).annotate(
            date=TruncDate('notification_time')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')

        followers_df = pd.DataFrame(list(followers))
        if not followers_df.empty:
            followers_df.set_index('date', inplace=True)
            followers_df.rename(columns={'count': 'value'}, inplace=True)
            followers_chart = create_chart(followers_df, f"New Followers of {user.login} Over Time",
                                           'Number of Followers')
        else:
            followers_chart = None

        # Tags statistics
        tags = Notification.objects.filter(
            user=user,
            notification_type='tags',
            notification_time__range=[start_date, end_date]
        ).annotate(
            date=TruncDate('notification_time')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')

        tags_df = pd.DataFrame(list(tags))
        if not tags_df.empty:
            tags_df.set_index('date', inplace=True)
            tags_df.rename(columns={'count': 'value'}, inplace=True)
            tags_chart = create_chart(tags_df, f"Mentions of {user.login} Over Time", 'Number of Mentions')
        else:
            tags_chart = None

        # Today's statistics for the user
        posts_today = PostStatistic.objects.filter(user=user, date=today).first()
        posts_today = posts_today.post_count if posts_today else 0

        scheduled_yesterday = ScheduledPost.objects.filter(user=user, date=yesterday).first()
        scheduled_yesterday = scheduled_yesterday.post_count if scheduled_yesterday else 0

        posts_difference = posts_today - scheduled_yesterday
        if posts_difference < 0 or posts_difference == 0:
            posts_difference = scheduled_yesterday
        scheduled_posts = ScheduledPost.objects.filter(
            user=user, date__gte=today
        ).aggregate(total=Sum('post_count'))['total'] or 0

        followers_today = Notification.objects.filter(
            user=user,
            notification_type='subscribed',
            notification_time__date=today
        ).count()

        followers_yesterday = Notification.objects.filter(
            user=user,
            notification_type='subscribed',
            notification_time__date=yesterday
        ).count()

        tags_today = Notification.objects.filter(
            user=user,
            notification_type='tags',
            notification_time__date=today
        ).count()

        user_data.append({
            'username': user.name,
            'id': user.id,  # Переконайтеся, що передаєте id користувач
            'posts_difference': posts_difference,
            'scheduled_posts': scheduled_posts,
            'followers_today': followers_today,
            'followers_yesterday': followers_yesterday,
            'tags_today': tags_today,
            'posts_chart': posts_chart,
            'followers_chart': followers_chart,
            'tags_chart': tags_chart,
        })
        print("!!!", user.id)
    context = {'user_data': user_data}
    return render(request, 'dashboard/general_dashboard.html', context)

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from .forms import UserForm
from .models import Users

def create_user(request):
    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "The user has been successfully created!")
            return redirect('dashboard:general_dashboard')  # Повернення на головну панель
    else:
        form = UserForm()

    return render(request, 'dashboard/create_user.html', {'form': form})

import subprocess
from django.http import JsonResponse
from django.views.decorators.http import require_POST

@require_POST
def run_script(request):
    try:
        subprocess.Popen(['python', 'scr.py'])
        return JsonResponse({'status': 'success', 'message': 'Script started!'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import PasswordChangeForm


# Add this new view function
def change_password(request, user_id):
    user = get_object_or_404(Users, pk=user_id)

    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            user.password = new_password
            user.save()
            messages.success(request, 'Password changed successfully!')
            return redirect('dashboard:user_dashboard', user_id=user.id)
    else:
        form = PasswordChangeForm()

    context = {
        'form': form,
        'user': user,
    }
    return render(request, 'dashboard/change_password.html', context)

def delete_user(request, user_id):
    user = get_object_or_404(Users, pk=user_id)
    user.delete()
    messages.success(request, 'User deleted successfully!')
    return general_dashboard(request)

