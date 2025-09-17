from django.db import models
from uuid import uuid4
# Create your models here.
class Trip(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    current_location = models.CharField(max_length=255)
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    current_cycle_hours = models.IntegerField()
    total_distance_miles = models.FloatField()
    total_drive_hours = models.FloatField()
    estimated_days = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)




class Stop(models.Model):
    id = models.AutoField(primary_key=True)
    trip = models.ForeignKey(Trip, related_name="stops", on_delete=models.CASCADE)
    stop_type = models.CharField(max_length=50, choices=[
        ("pickup", "Pickup"),
        ("fuel", "Fuel"),
        ("rest", "Rest"),
        ("dropoff", "Dropoff"),
    ])
    location = models.CharField(max_length=255)
    mile_marker = models.FloatField(null=True, blank=True)
    duration_hours = models.FloatField()



class DailySchedule(models.Model):
    id = models.AutoField(primary_key=True)
    trip = models.ForeignKey(Trip, related_name="daily_schedules", on_delete=models.CASCADE)
    day_number = models.IntegerField()
    driving_hours = models.FloatField()
    on_duty_hours = models.FloatField()
    off_duty_hours = models.FloatField()
    notes = models.TextField(blank=True, null=True)



class LogEntry(models.Model):
    id = models.AutoField(primary_key=True)
    schedule = models.ForeignKey(DailySchedule, related_name="log_entries", on_delete=models.CASCADE)
    start_hour = models.FloatField()   # Example: 6.0 for 6:00 AM
    end_hour = models.FloatField()     # Example: 14.5 for 2:30 PM
    status = models.CharField(max_length=50, choices=[
        ("Off Duty", "Off Duty"),
        ("Sleeper", "Sleeper Berth"),
        ("Driving", "Driving"),
        ("On Duty", "On Duty (Not Driving)"),
        ("Break", "Break"),
    ])
