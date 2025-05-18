from django.db import models

class Users(models.Model):
    id = models.AutoField(primary_key=True)
    login = models.CharField(max_length=100, db_index=True)  # Added index
    name = models.CharField(max_length=100)  # ➕ ім'я користувача
    password = models.CharField(max_length=100)

    class Meta:
        db_table = 'users'
        managed = False  # Якщо хочемо, щоб Django управляв цією таблицею

    def __str__(self):
        return str(self.name)

class Notification(models.Model):
    notification_type = models.CharField(max_length=50, db_index=True)  # Added index
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='notifications')  # Added related_name
    username = models.CharField(max_length=255, db_index=True)  # Added index
    content = models.TextField(null=True, blank=True)
    notification_time = models.DateTimeField(db_index=True)  # Added index
    recorded_at = models.DateTimeField()

    class Meta:
        db_table = 'notifications'
        managed = False  # Якщо хочемо, щоб Django управляв цією таблицею

class TrackingLinkStats(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='tracking_stats')  # Added related_name
    date = models.DateField(db_index=True)  # Added index
    click_count = models.IntegerField()
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tracking_link_stats'
        managed = False
        unique_together = (('user', 'date'),)  # Еквівалент UNIQUE(user_id, date) в SQLite

    def __str__(self):
        return f"{self.user.name} - {self.date}: {self.click_count} clicks"

class PostStatistic(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='post_statistics')  # Added related_name
    date = models.DateField(db_index=True)  # Added index
    post_count = models.IntegerField()
    recorded_at = models.DateTimeField()

    class Meta:
        db_table = 'post_statistics'
        managed = True  # Якщо хочемо, щоб Django управляв цією таблицею

class ScheduledPost(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='scheduled_posts')  # Added related_name
    date = models.DateField(db_index=True)  # Added index
    post_count = models.IntegerField()
    recorded_at = models.DateTimeField()

    def __str__(self):
        return str(self.post_count)  # Повертаємо тільки постійне число постів

    class Meta:
        db_table = 'scheduled_posts'
        managed = False  # Якщо хочемо, щоб Django управляв цією таблицею

# Додамо нову модель для тегів у пості
class PostTags(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='post_tags')  # Added related_name
    post_text = models.TextField()
    tag_username = models.CharField(max_length=255, db_index=True)  # Added index
    post_time = models.DateTimeField(db_index=True)  # Added index
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'post_tags'
        managed = False

class Assistant(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True)  # Додано індекс

    class Meta:
        managed = False
        db_table = 'dashboard_assistant'
        ordering = ['-id']  # Сортування за замовчуванням

    def __str__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True)  # Added index
    assistants = models.ManyToManyField(
        Assistant,
        through='AssistantTag',
        related_name='tags',
    )

    class Meta:
        managed = False
        db_table = 'dashboard_tag'
        ordering = ['name']

    def __str__(self):
        return self.name

class AssistantTag(models.Model):
    assistant = models.ForeignKey(Assistant, on_delete=models.CASCADE, db_column='assistant_id')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, db_column='tag_id')

    class Meta:
        managed = False
        db_table = 'dashboard_assistant_tags'
        indexes = [
            models.Index(fields=['assistant', 'tag']),
        ]