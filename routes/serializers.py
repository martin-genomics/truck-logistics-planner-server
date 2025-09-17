from rest_framework import serializers
from .models import Trip, Stop, DailySchedule, LogEntry

class StopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stop
        fields = ['id', 'stop_type', 'location', 'mile_marker', 'duration_hours']
        read_only_fields = ['id']

class LogEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LogEntry
        fields = ['id', 'start_hour', 'end_hour', 'status']
        read_only_fields = ['id']

class DailyScheduleSerializer(serializers.ModelSerializer):
    log_entries = LogEntrySerializer(many=True, read_only=True)
    
    class Meta:
        model = DailySchedule
        fields = ['id', 'day_number', 'driving_hours', 'on_duty_hours', 'off_duty_hours', 'notes', 'log_entries']
        read_only_fields = ['id']

class TripSerializer(serializers.ModelSerializer):
    stops = StopSerializer(many=True, read_only=True)
    daily_schedules = DailyScheduleSerializer(many=True, read_only=True)
    
    class Meta:
        model = Trip
        fields = [
            'id', 'current_location', 'pickup_location', 'dropoff_location',
            'current_cycle_hours', 'total_distance_miles', 'total_drive_hours',
            'estimated_days', 'created_at', 'stops', 'daily_schedules'
        ]
        read_only_fields = ['id', 'created_at', 'stops', 'daily_schedules']

class RouteRequestSerializer(serializers.Serializer):
    current_location = serializers.CharField(required=True, max_length=255, help_text="Current location of the driver/vehicle")
    pickup_location = serializers.CharField(required=True, max_length=255, help_text="Location where the pickup will happen")
    dropoff_location = serializers.CharField(required=True, max_length=255, help_text="Final destination where the delivery will be made")
    current_cycle_hours = serializers.FloatField(required=True, min_value=0, help_text="Current hours used in the current driving cycle")
    
    # For backward compatibility and routing
    @property
    def origin(self):
        return self.validated_data.get('current_location')
        
    @property
    def destination(self):
        return self.validated_data.get('dropoff_location')
