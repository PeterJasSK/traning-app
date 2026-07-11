# core/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('trainer', 'Trainer'),
        ('trainee', 'Trainee'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='trainee')
    head_trainer = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trainees'
    )
    helpers = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        related_name='main_trainer'
    )

    def get_assigned_trainers(self):
        trainers = set()
        if self.head_trainer:
            trainers.add(self.head_trainer)
        trainers.update(self.main_trainer.all())
        return list(trainers)

    def __str__(self):
        return self.username

def user_directory_path(instance, filename):
    """
    Upload path: measurements/<username>/<date>_<filename>
    """
    # format date as YYYY-MM-DD
    date_str = instance.date.strftime("%Y-%m-%d") if instance.date else "no-date"
    return f"measurements/{instance.user.username}/{date_str}_{filename}"

class Measurement(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    date = models.DateField()
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    chest = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    waist = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    biceps = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    thigh = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    calf = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    photo = models.ImageField(upload_to=user_directory_path, null=True, blank=True)
    note = models.TextField(blank=True)

    def __str__(self):
        return f"Measurement for {self.user.username} on {self.date}"

class Goal(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    description = models.TextField()
    target_date = models.DateField()
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return self.description

class Message(models.Model):
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"From {self.sender.username} to {self.receiver.username}"