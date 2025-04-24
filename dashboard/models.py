from django.db import models

class Users(models.Model):
    name = models.CharField(max_length=100)  # ➕ ім'я користувача
    login = models.CharField(max_length=100)
    password = models.CharField(max_length=100)

    class Meta:
        db_table = 'users'
        managed = True  # Якщо хочемо, щоб Django управляв цією таблицею

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