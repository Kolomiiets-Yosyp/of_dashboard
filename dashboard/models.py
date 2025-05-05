from django.db import models

class Users(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)  # ➕ ім'я користувача
    login = models.CharField(max_length=100)
    password = models.CharField(max_length=100)

    class Meta:
        db_table = 'users'
        managed = True  # Якщо хочемо, щоб Django управляв цією таблицею

    def __str__(self):
        return str(self.name)
class Notification(models.Model):
    notification_type = models.CharField(max_length=50)
    user = models.ForeignKey(Users, on_delete=models.CASCADE)  # Використовуємо ForeignKey для зв'язку
    username = models.CharField(max_length=255)
    content = models.TextField(null=True, blank=True)
    notification_time = models.DateTimeField()
    recorded_at = models.DateTimeField()

    class Meta:
        db_table = 'notifications'
        managed = True  # Якщо хочемо, щоб Django управляв цією таблицею

class PostStatistic(models.Model):
    date = models.DateField()
    user = models.ForeignKey(Users, on_delete=models.CASCADE)  # Використовуємо ForeignKey для зв'язку
    post_count = models.IntegerField()
    recorded_at = models.DateTimeField()

    class Meta:
        db_table = 'post_statistics'
        managed = True  # Якщо хочемо, щоб Django управляв цією таблицею

class ScheduledPost(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE)  # Використовуємо ForeignKey для зв'язку
    date = models.DateField()
    post_count = models.IntegerField()
    recorded_at = models.DateTimeField()

    def __str__(self):
        return str(self.post_count)  # Повертаємо тільки постійне число постів
    class Meta:
        db_table = 'scheduled_posts'
        managed = True  # Якщо хочемо, щоб Django управляв цією таблицею

# Додамо нову модель для тегів у пості
class PostTags(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    post_text = models.TextField()
    tag_username = models.CharField(max_length=255)
    post_time = models.DateTimeField()
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'post_tags'
        managed = True


from django.db import models


class Assistant(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True)  # Додано індекс

    class Meta:
        managed = False
        db_table = 'dashboard_assistant'
        ordering = ['-id']  # Сортування за замовчуванням
    def __str__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True)
    # Додаємо ManyToManyField з явним вказівником through
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