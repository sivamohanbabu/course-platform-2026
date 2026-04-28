from django.db import models
from django.contrib.auth.models import User


class Course(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="courses")
    name = models.CharField(max_length=255)
    total_units = models.IntegerField()
    completed_units = models.IntegerField(default=0)

    @property
    def progress_percentage(self):
        if self.total_units <= 0:
            return 0
        return (self.completed_units / self.total_units) * 100

    def __str__(self):
        return self.name


class SubjectDocument(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="subject_documents/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Spaced Repetition Fields
    next_review_date = models.DateField(null=True, blank=True)
    review_streak = models.IntegerField(default=0)

    def __str__(self):
        return self.title

    @property
    def is_due(self):
        if not self.next_review_date:
            return False
        return self.next_review_date <= timezone.now().date()


class TodayTask(models.Model):
    PRIORITY_CHOICES = [
        ('H', 'High'),
        ('M', 'Medium'),
        ('L', 'Low'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tasks")
    task_description = models.TextField()
    is_done = models.BooleanField(default=False)
    priority = models.CharField(max_length=1, choices=PRIORITY_CHOICES, default='M')
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.task_description[:50]


class StudySession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="study_sessions")
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name="sessions")
    duration_minutes = models.IntegerField()
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.date} ({self.duration_minutes} min)"


class ProgressLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="progress_logs")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="progress_logs")
    units_added = models.IntegerField(default=1)
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.course.name} (+{self.units_added})"


class DocumentReview(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    document = models.OneToOneField(SubjectDocument, on_delete=models.CASCADE, related_name="review")
    takeaways = models.TextField(blank=True)
    ai_summary = models.TextField(blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Review: {self.document.title}"


class StudyReminder(models.Model):
    RECURRENCE_CHOICES = [
        ('D', 'Daily'),
        ('W', 'Weekly'),
        ('M', 'Monthly'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reminders")
    subject_name = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    recurrence = models.CharField(max_length=1, choices=RECURRENCE_CHOICES, default='D')

    def __str__(self):
        return f"{self.subject_name} ({self.user.username})"
