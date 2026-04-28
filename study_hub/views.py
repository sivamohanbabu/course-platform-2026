from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
from django.views import View
from django.views.generic import TemplateView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.http import JsonResponse
from .models import Course, SubjectDocument, TodayTask, StudySession
from .forms import SubjectDocumentForm
from django.utils import timezone


class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = "registration/register.html"
    success_url = reverse_lazy('login')


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "study_hub/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # 1. Fetch current user's Courses
        context['courses'] = Course.objects.filter(user=user)
        
        # 2. 5 most recent Documents
        context['documents'] = SubjectDocument.objects.filter(
            course__user=user
        ).order_by('-uploaded_at')[:5]
        
        # 3. Today's Tasks sorted by priority (High, Medium, Low)
        # Using a case-based ordering if needed, but simple H, M, L string sort works for now 
        # or we can define a custom ordering.
        today = timezone.now().date()
        context['today_tasks'] = TodayTask.objects.filter(
            user=user, 
            date_created__date=today
        ).order_by('priority') # H < M < L alphabetically, so High comes first.
        
        # Total study time
        total_time = StudySession.objects.filter(user=user).aggregate(
            models.Sum('duration_minutes')
        )['duration_minutes__sum'] or 0
        context['total_study_time'] = total_time
        
        context['upload_form'] = SubjectDocumentForm()
        context['upload_form'].fields['course'].queryset = Course.objects.filter(user=user)
        return context


class DocumentUploadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = SubjectDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.cleaned_data['course']
            if course.user == request.user:
                form.save()
        return redirect('dashboard')


class IncrementalProgressView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        course = get_object_or_404(Course, pk=pk, user=request.user)
        if course.completed_units < course.total_units:
            course.completed_units += 1
            course.save()
            
            # Log progress for analytics
            ProgressLog.objects.create(user=request.user, course=course)
            
            return JsonResponse({
                'status': 'success',
                'completed_units': course.completed_units,
                'progress': course.progress_percentage
            })
        return JsonResponse({'status': 'error', 'message': 'Course already completed'}, status=400)


class TaskToggleView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        task = get_object_or_404(TodayTask, pk=pk, user=request.user)
        task.is_done = not task.is_done
        task.save()
        return JsonResponse({
            'status': 'success',
            'is_done': task.is_done
        })


class StudyStatView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        duration = request.POST.get('duration', 25)
        course_id = request.POST.get('course_id')
        
        session_data = {
            'user': request.user,
            'duration_minutes': int(duration)
        }
        if course_id:
            session_data['course'] = get_object_or_404(Course, id=course_id, user=request.user)
            
        StudySession.objects.create(**session_data)
        return JsonResponse({'status': 'success', 'message': 'Session logged'})


class AnalyticsView(LoginRequiredMixin, View):
    # ... existing implementation ...
    def get(self, request, *args, **kwargs):
        user = request.user
        today = timezone.now().date()
        
        # 1. Daily: Units completed today
        daily_units = ProgressLog.objects.filter(user=user, date=today).count()
        
        # 2. Weekly: Focus time vs previous week
        last_7_days = today - timezone.timedelta(days=7)
        prev_7_days = last_7_days - timezone.timedelta(days=7)
        
        current_week_time = StudySession.objects.filter(
            user=user, date__range=[last_7_days, today]
        ).aggregate(total=models.Sum('duration_minutes'))['total'] or 0
        
        prev_week_time = StudySession.objects.filter(
            user=user, date__range=[prev_7_days, last_7_days]
        ).aggregate(total=models.Sum('duration_minutes'))['total'] or 0
        
        # 3. Monthly Distribution (Doughnut Chart)
        subject_data = StudySession.objects.filter(user=user).values('course__name').annotate(
            total_time=models.Sum('duration_minutes')
        )
        
        subjects = [item['course__name'] or 'General' for item in subject_data]
        durations = [item['total_time'] for item in subject_data]
        
        # 4. Progress over time (Line Chart)
        last_30_days = [today - timezone.timedelta(days=i) for i in range(30)]
        progress_data = []
        for d in reversed(last_30_days):
            count = ProgressLog.objects.filter(user=user, date=d).count()
            progress_data.append(count)
            
        return JsonResponse({
            'daily_units': daily_units,
            'weekly_focus': {
                'current': current_week_time,
                'previous': prev_week_time,
                'growth': ((current_week_time - prev_week_time) / prev_week_time * 100) if prev_week_time > 0 else 100
            },
            'distribution': {
                'labels': subjects,
                'data': durations
            },
            'progress_line': {
                'labels': [d.strftime('%m-%d') for d in reversed(last_30_days)],
                'data': progress_data
            }
        })


class SaveReviewView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        doc = get_object_or_404(SubjectDocument, pk=pk, course__user=request.user)
        takeaways = request.POST.get('takeaways', '')
        
        review, created = DocumentReview.objects.get_or_create(
            user=request.user,
            document=doc
        )
        review.takeaways = takeaways
        review.save()
        
        # Spaced Repetition Logic (Leitner System)
        doc.review_streak += 1
        intervals = {1: 1, 2: 3, 3: 7}
        days_to_add = intervals.get(doc.review_streak, 14) # Default to 14 days after streak 3
        
        doc.next_review_date = timezone.now().date() + timezone.timedelta(days=days_to_add)
        doc.save()
        
        return JsonResponse({
            'status': 'success', 
            'next_review': doc.next_review_date.strftime('%Y-%m-%d')
        })


class AddCourseView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        name = request.POST.get('name')
        total_units = request.POST.get('total_units', 10)
        if name:
            Course.objects.create(
                user=request.user,
                name=name,
                total_units=int(total_units)
            )
        return redirect('dashboard')


class GetReviewView(LoginRequiredMixin, View):
    def get(self, request, pk, *args, **kwargs):
        doc = get_object_or_404(SubjectDocument, pk=pk, course__user=request.user)
        review = DocumentReview.objects.filter(user=request.user, document=doc).first()
        
        return JsonResponse({
            'takeaways': review.takeaways if review else '',
            'ai_summary': review.ai_summary if review else '',
            'title': doc.title
        })


# Calendar Views
class CalendarEventsView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        reminders = StudyReminder.objects.filter(user=request.user)
        events = []
        for reminder in reminders:
            events.append({
                'id': reminder.id,
                'title': reminder.subject_name,
                'start': reminder.start_time.isoformat(),
                'end': reminder.end_time.isoformat(),
                'allDay': False,
            })
        return JsonResponse(events, safe=False)


class AddReminderView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        subject = request.POST.get('subject_name')
        start = request.POST.get('start_time')
        end = request.POST.get('end_time')
        if subject and start and end:
            StudyReminder.objects.create(
                user=request.user,
                subject_name=subject,
                start_time=start,
                end_time=end
            )
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error'}, status=400)


class UpdateReminderView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        reminder = get_object_or_404(StudyReminder, pk=pk, user=request.user)
        start = request.POST.get('start_time')
        end = request.POST.get('end_time')
        if start:
            reminder.start_time = start
        if end:
            reminder.end_time = end
        reminder.save()
        return JsonResponse({'status': 'success'})


class DeleteReminderView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        reminder = get_object_or_404(StudyReminder, pk=pk, user=request.user)
        reminder.delete()
        return JsonResponse({'status': 'success'})


# Keeping AddTaskView as it was useful for the dashboard UI
class AddTaskView(LoginRequiredMixin, View):
    # ... existing implementation ...
    def post(self, request, *args, **kwargs):
        description = request.POST.get('task_description')
        priority = request.POST.get('priority', 'M')
        if description:
            task = TodayTask.objects.create(
                user=request.user, 
                task_description=description,
                priority=priority
            )
            
            # Smart Schedule Logic
            if priority == 'H':
                now = timezone.now()
                start_time = now + timezone.timedelta(hours=1)
                end_time = start_time + timezone.timedelta(hours=1)
                StudyReminder.objects.create(
                    user=request.user,
                    subject_name=f"Focus: {description[:30]}",
                    start_time=start_time,
                    end_time=end_time
                )
        return redirect('dashboard')


class DeleteDocumentView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        doc = get_object_or_404(SubjectDocument, pk=pk, course__user=request.user)
        doc.delete()
        return JsonResponse({'status': 'success'})


class DeleteTaskView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        task = get_object_or_404(TodayTask, pk=pk, user=request.user)
        task.delete()
        return JsonResponse({'status': 'success'})
