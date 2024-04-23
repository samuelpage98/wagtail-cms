from django.contrib import admin

# Register your models here.
from .models import Workstream, Phase, Activity, Task, Resource, Project
import nested_admin

# admin.site.register(Phase)
# admin.site.register(Activity)
# admin.site.register(Task)
# admin.site.register(Resource)


class TaskInline(nested_admin.NestedTabularInline):
    model = Task
    extra = 0
    classes = ['collapse']
    fieldsets = [
        (None, {"fields": ["description"]}),

        ('Owner', {"fields": ["owner"]}),
        ('Baseline', {"fields": ["baseline_start", "baseline_finish"]}),
    ]


class ActivityInline(nested_admin.NestedStackedInline):
    model = Activity
    extra = 0
    classes = ['collapse']
    fieldsets = [
        (None, {"fields": ["description"]}),
    ]
    inlines = [TaskInline]


class PhaseInline(nested_admin.NestedTabularInline):
    model = Phase
    extra = 0
    classes = ['collapse']
    fieldsets = [
        (None, {"fields": ["description"]}),
    ]
    inlines = [ActivityInline]


class WorkstreamInline(nested_admin.NestedStackedInline):
    model = Workstream
    extra = 0

    classes = ['collapse']
    fieldsets = [
        (None, {"fields": ["description"]})
    ]
    inlines = [PhaseInline]


class ProjectAdmin(nested_admin.NestedModelAdmin):
    fieldsets = [
        (None, {"fields": ["description"]}),
        ("Date information", {"fields": [
            "start_date"], "classes": ["collapse"]}),
        ("Resources", {"fields": [
            "resources"], "classes": ["collapse"]}),
    ]
    inlines = [WorkstreamInline]


class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "project", "workstream", "phase", "activity", 'description',  'owner', 'baseline_start')

    ordering = ('-owner',)


admin.site.register(Project, ProjectAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(Resource)
