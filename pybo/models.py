from django.db import models

class Question(models.Model):
    subject = models.CharField(max_length=200)
    content = models.TextField()
    create_date = models.DateTimeField()

    def __str__(self):
        return self.subject


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    content = models.TextField()
    create_date = models.DateTimeField()


class Book(models.Model):
    title      = models.CharField(max_length=200)
    author     = models.CharField(max_length=100, blank=True)
    background = models.TextField(blank=True)   # 소개·배경
    summary    = models.TextField(blank=True)   # 요약
    cover      = models.ImageField(upload_to="covers/", blank=True)

    pub_date   = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.title
    
from django.db import models
from django.conf import settings

class DailyUsage(models.Model):
    user  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date  = models.DateField()
    count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'date')
        verbose_name = "일별 사용량"
        verbose_name_plural = "일별 사용량"

    def increment(self):
        self.count += 1
        self.save()