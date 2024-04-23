from django.db import models
from django.contrib import admin
# Create your models here.


class Resource(models.Model):
    name = models.CharField(max_length=30)
    email = models.EmailField()

    def __str__(self):
        return self.name


class Project(models.Model):
    description = models.CharField(max_length=30)
    start_date = models.DateField()
    resources = models.ManyToManyField(Resource)

    def __str__(self):
        return self.description


class Workstream(models.Model):
    description = models.CharField(max_length=30)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return self.description


class Phase(models.Model):
    description = models.CharField(max_length=30)
    workstream = models.ForeignKey(
        Workstream, on_delete=models.CASCADE, related_name='phases')

    def __str__(self):
        return self.description


class Activity(models.Model):
    description = models.CharField(max_length=30)
    phase = models.ForeignKey(Phase, on_delete=models.CASCADE)

    def __str__(self):
        return self.description

    class Meta:
        verbose_name_plural = "Activities"


class Task(models.Model):
    description = models.CharField(max_length=30)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    owner = models.ForeignKey(Resource, on_delete=models.CASCADE)
    baseline_start = models.DateField(blank=True, null=True)
    baseline_finish = models.DateField(blank=True, null=True)
    actual_start = models.DateField(blank=True, null=True)
    actual_finish = models.DateField(blank=True, null=True)
    expected_finish = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.description

    @admin.display(description="Phase")
    def phase(self):
        return self.activity.phase.description

    @admin.display(description="Workstream")
    def workstream(self):
        return self.activity.phase.workstream.description

    @admin.display(description="Project")
    def project(self):
        return self.activity.phase.workstream.project.description
