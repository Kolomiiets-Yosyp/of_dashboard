from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Sum, Max
from django.db.models.functions import TruncDate
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from .models import Notification, PostStatistic, ScheduledPost, Users, PostTags, TrackingLinkStats


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





from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Max, Q
from datetime import datetime, timedelta
from django.db.models.functions import TruncDate
import pandas as pd
from .models import Users, PostStatistic, Notification, ScheduledPost, PostTags, Assistant, Tag

def user_dashboard(request, user_id):
    # Отримуємо користувача
    user = get_object_or_404(Users, pk=user_id)
    start_date, end_date = get_date_range()

    # Статистика постів
    posts_stats = PostStatistic.objects.filter(
        user=user,
        date__range=[start_date.date(), end_date.date()]
    )
    posts_df = pd.DataFrame(list(posts_stats.values('date', 'post_count')))
    posts_chart = None
    if not posts_df.empty:
        posts_df.set_index('date', inplace=True)
        posts_df.rename(columns={'post_count': 'value'}, inplace=True)
        posts_chart = create_chart(posts_df, f"Posts Made by {user.login} Over Time", 'Number of Posts')

    # Статистика підписників
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
    followers_chart = None
    if not followers_df.empty:
        followers_df.set_index('date', inplace=True)
        followers_df.rename(columns={'count': 'value'}, inplace=True)
        followers_chart = create_chart(followers_df, f"New Followers of {user.login} Over Time", 'Number of Followers')

    # Статистика тегів
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
    tags_chart = None
    if not tags_df.empty:
        tags_df.set_index('date', inplace=True)
        tags_df.rename(columns={'count': 'value'}, inplace=True)
        tags_chart = create_chart(tags_df, f"Mentions of {user.login} Over Time", 'Number of Mentions')

    # Сьогоднішня статистика
    today = datetime.now().date()
    posts_today = PostTags.objects.filter(user=user,
                                          post_time__date=today).count()  # posts_today = posts_today.post_count if posts_today else 0
    #posts_today = posts_today.post_count if posts_today else 0


    posts_difference = posts_today


    # Заплановані пости
    scheduled_posts = ScheduledPost.objects.filter(
        user=user,
        date__gte=today
    ).order_by('date')

    # Підписники та теги за сьогодні
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

    # Отримуємо теги з постів
    post_tags_data = PostTags.objects.filter(user=user).values(
        'tag_username'
    ).annotate(
        last_time=Max('post_time')
    ).order_by('tag_username')

    # Отримуємо теги зі сповіщень з кількістю підписників
    notification_tags_data = Notification.objects.filter(
        user=user,
        notification_type='tags'
    ).values(
        'username'
    ).annotate(
        last_time=Max('notification_time')
    ).order_by('username')

    # Додаємо інформацію про нових підписників
    for tag in notification_tags_data:
        notification_time = tag['last_time']
        new_followers = Notification.objects.filter(
            user=user,
            notification_type='subscribed',
            notification_time__gte=notification_time,
            notification_time__lte=notification_time + timedelta(minutes=900)
        ).count()
        tag['new_followers'] = new_followers

    # Створюємо словники для швидкого доступу
    post_tags = {item['tag_username']: item['last_time'] for item in post_tags_data}
    notification_tags = {
        item['username']: {
            'last_time': item['last_time'],
            'new_followers': item['new_followers']
        }
        for item in notification_tags_data
    }

    # Об'єднуємо всі теги
    all_tags = sorted(set(post_tags.keys()).union(set(notification_tags.keys())))

    # Отримуємо всі теги з бази даних
    tags_from_db = Tag.objects.filter(name__in=all_tags).prefetch_related('assistants')

    # Створюємо словник для швидкого пошуку тегів та їх асистентів
    tag_assistants = {}
    for tag in tags_from_db:
        assistants = [assistant.name for assistant in tag.assistants.all()]
        tag_assistants[tag.name] = assistants

    # Отримуємо асистентів з тегами
    assistants_with_tags = Assistant.objects.filter(
        tags__name__in=all_tags
    ).distinct().prefetch_related('tags')

    # Групуємо теги по асистентах
    assistants_data = []
    for assistant in assistants_with_tags:
        assistant_tags = []
        for tag in assistant.tags.all():
            if tag.name in all_tags:
                post_time = post_tags.get(tag.name)
                notification_data = notification_tags.get(tag.name, {})
                notification_time = notification_data.get('last_time')
                new_followers = notification_data.get('new_followers')

                assistant_tags.append({
                    'name': tag.name,
                    'post_time': post_time,
                    'notification_time': notification_time,
                    'new_followers': new_followers,
                    'post_class': 'bg-success' if post_time else '',
                    'notification_class': 'bg-success' if notification_time else '',
                    'post_missing': not post_time and notification_time,
                    'notification_missing': post_time and not notification_time,
                })

        if assistant_tags:
            assistants_data.append({
                'assistant': assistant.name,
                'assistant_id': assistant.id,
                'tags': assistant_tags
            })

    # Теги без асистентів
    tags_without_assistants = []
    assistant_tags_set = {t['name'] for a in assistants_data for t in a['tags']}

    for tag in all_tags:
        if tag not in assistant_tags_set:
            post_time = post_tags.get(tag)
            notification_data = notification_tags.get(tag, {})
            notification_time = notification_data.get('last_time')
            new_followers = notification_data.get('new_followers')

            tags_without_assistants.append({
                'tag': tag,
                'post_time': post_time,
                'notification_time': notification_time,
                'new_followers': new_followers,
                'post_class': 'bg-success' if post_time else '',
                'notification_class': 'bg-success' if notification_time else '',
                'post_missing': not post_time and notification_time,
                'notification_missing': post_time and not notification_time,
                'has_assistant': False
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
        'post_tags_count': len(post_tags),
        'notification_tags_count': len(notification_tags),
        'common_tags_count': len(set(post_tags.keys()) & set(notification_tags.keys())),
        'assistants_data': assistants_data,
        'tags_without_assistants': tags_without_assistants,
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
        posts_today = PostTags.objects.filter(user=user, post_time__date=today).count()        #posts_today = posts_today.post_count if posts_today else 0

        #scheduled_yesterday = ScheduledPost.objects.filter(user=user, date=yesterday).first()
        #scheduled_yesterday = scheduled_yesterday.post_count if scheduled_yesterday else 0

        posts_difference = posts_today
        #if posts_difference < 0 or posts_difference == 0:
         #   posts_difference = scheduled_yesterday
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
        tracking_subscriptions = TrackingLinkStats.objects.filter(
            user=user
        ).aggregate(total_clicks=Sum('click_count'))['total_clicks']
        user_data.append({
            'username': user.name,
            'id': user.id,  # Переконайтеся, що передаєте id користувач
            'posts_difference': posts_difference,
            'scheduled_posts': scheduled_posts,
            'followers_today': followers_today,
            'followers_yesterday': followers_yesterday,
            'tags_today': tags_today,
            'tracking_subscriptions': tracking_subscriptions,
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
        subprocess.Popen(['python', 'scr_playwright.py'])
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


from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import Assistant, Tag, AssistantTag
from .forms import AssistantForm, TagForm

from django.core.paginator import Paginator
from django.db.models import Q


def assistants_view(request):
    # Пошук та фільтрація
    search_query = request.GET.get('search', '')
    page_number = request.GET.get('page', 1)

    # Базові запити
    assistants = Assistant.objects.all()
    tags = Tag.objects.all()

    # Фільтрація за пошуком
    if search_query:
        assistants = assistants.filter(name__icontains=search_query)
        tags = tags.filter(
            Q(name__icontains=search_query) |
            Q(assistants__name__icontains=search_query)
        ).distinct()

    # Пагінація
    assistants_paginator = Paginator(assistants.order_by('name'), 10)  # 20 елементів на сторінку
    tags_paginator = Paginator(tags.order_by('name'), 10)

    try:
        assistants_page = assistants_paginator.page(page_number)
        tags_page = tags_paginator.page(page_number)
    except:
        assistants_page = assistants_paginator.page(1)
        tags_page = tags_paginator.page(1)

    # Обробка форм
    if request.method == 'POST':
        if 'add_assistant' in request.POST:
            assistant_form = AssistantForm(request.POST)
            if assistant_form.is_valid():
                assistant_form.save()
                return redirect(reverse('dashboard:assistants') + '?search=' + search_query)

        elif 'add_tag' in request.POST:
            tag_form = TagForm(request.POST)
            if tag_form.is_valid():
                # Створюємо тег
                tag = tag_form.save()

                # Додаємо зв'язки через проміжну модель
                AssistantTag.objects.bulk_create([
                    AssistantTag(tag=tag, assistant=assistant)
                    for assistant in tag_form.cleaned_data['assistants']
                ])

                return redirect(reverse('dashboard:assistants') + '?search=' + search_query)
    else:
        assistant_form = AssistantForm()
        tag_form = TagForm()

    context = {
        'assistant_form': assistant_form,
        'tag_form': tag_form,
        'assistants': assistants_page,
        'tags': tags_page,
        'search_query': search_query,
    }
    return render(request, 'dashboard/assistants.html', context)


def delete_assistant(request, assistant_id):
    assistant = get_object_or_404(Assistant, id=assistant_id)
    assistant.delete()
    return redirect('dashboard:assistants')


def edit_assistant(request, assistant_id):
    assistant = get_object_or_404(Assistant, id=assistant_id)
    all_tags = Tag.objects.all()  # Отримуємо всі доступні теги

    if request.method == 'POST':
        form = AssistantForm(request.POST, instance=assistant)
        if form.is_valid():
            assistant = form.save()

            # Оновлюємо теги асистента
            selected_tags = request.POST.getlist('tags')
            current_tags = set(tag.id for tag in assistant.tags.all())
            new_tags = set(int(tag_id) for tag_id in selected_tags)

            # Видаляємо зв'язки, які були видалені
            for tag_id in current_tags - new_tags:
                AssistantTag.objects.filter(assistant=assistant, tag_id=tag_id).delete()

            # Додаємо нові зв'язки
            for tag_id in new_tags - current_tags:
                AssistantTag.objects.create(assistant=assistant, tag_id=tag_id)

            return redirect('dashboard:assistants')
    else:
        form = AssistantForm(instance=assistant)

    context = {
        'assistant': assistant,
        'form': form,
        'all_tags': all_tags,
    }
    return render(request, 'dashboard/edit_assistant.html', context)

def delete_tag(request, tag_id):
    tag = get_object_or_404(Tag, id=tag_id)
    tag.delete()
    return redirect('dashboard:assistants')


from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from .models import Tag, Assistant, AssistantTag


def edit_tag(request, tag_id):
    tag = get_object_or_404(Tag, id=tag_id)
    all_assistants = Assistant.objects.all()

    if request.method == 'POST':
        # Оновлюємо назву тегу
        tag.name = request.POST.get('name')
        tag.save()

        # Оновлюємо зв'язки з асистентами
        selected_assistants = request.POST.getlist('assistants')
        current_assistants = set(str(a.id) for a in tag.assistants.all())
        new_assistants = set(selected_assistants)

        # Видаляємо зв'язки, які були видалені
        for assistant_id in current_assistants - new_assistants:
            AssistantTag.objects.filter(tag=tag, assistant_id=assistant_id).delete()

        # Додаємо нові зв'язки
        for assistant_id in new_assistants - current_assistants:
            AssistantTag.objects.create(tag=tag, assistant_id=assistant_id)

        return redirect('dashboard:assistants')

    context = {
        'tag': tag,
        'all_assistants': all_assistants,
        'form': {'name': {'value': tag.name}},
    }
    return render(request, 'dashboard/edit_tag.html', context)
