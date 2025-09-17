import json
import requests
import uuid
from datetime import datetime, timedelta
from django.conf import settings
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
import os
import mapbox
from geopy.distance import geodesic

from .models import Trip, Stop, DailySchedule, LogEntry
from .serializers import TripSerializer, RouteRequestSerializer
import os
from dotenv import load_dotenv

from .services.local_geocoding import MapboxDirectionsService

# Load environment variables
load_dotenv()

class TripAPIView(generics.ListCreateAPIView):
    """
    API endpoint to create and list trips with their stops and schedules.
    """
    def get(self, request, *args, **kwargs):
        try:
            # Get all trips ordered by creation date (newest first)
            trips = Trip.objects.all().order_by('-created_at')
            
            # Prefetch related data to optimize database queries
            trips = trips.prefetch_related(
                'stops',
                'daily_schedules__log_entries'
            )
            
            # Serialize the trips with all related data
            trip_serializer = TripSerializer(trips, many=True, context={'request': request})
            
            # Format the response with additional metadata
            response_data = {
                "status": status.HTTP_200_OK,
                "count": len(trip_serializer.data),
                "data": trip_serializer.data
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "error": "Failed to fetch trips",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def create(self, request, *args, **kwargs):
        serializer = RouteRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Initialize Mapbox Directions Service
            access_token = os.getenv('MAPBOX_ACCESS_TOKEN')
            if not access_token:
                return Response(
                    {'error': 'Mapbox access token not configured'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            directions_service = MapboxDirectionsService(access_token)
            
            # Process the directions request
            result = directions_service.process_directions_request(serializer.validated_data)
            if not result['success']:
                return Response(
                    {'error': result.get('error', 'Failed to process directions')},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            route_data = result['data']
            distance_meters = route_data['distance']
            distance_miles = distance_meters * 0.000621371  # Convert to miles
            duration_seconds = route_data['duration']
            driving_hours = duration_seconds / 3600  # Convert to hours
            
            # Extract locations and cycle hours from the request
            current_location = serializer.validated_data['current_location']
            pickup_location = serializer.validated_data['pickup_location']
            dropoff_location = serializer.validated_data['dropoff_location']
            current_cycle_hours = serializer.validated_data['current_cycle_hours']
            
            # Calculate stops based on rules
            driving_hours_limit = int(os.getenv('DRIVING_HOURS_LIMIT', 11))
            off_duty_hours = int(os.getenv('OFF_DUTY_HOURS', 10))
            fuel_stop_miles = int(os.getenv('FUEL_STOP_MILES', 1000))
            
            # Create trip with the provided current_cycle_hours
            trip = Trip.objects.create(
                current_location=current_location,
                pickup_location=pickup_location,
                dropoff_location=dropoff_location,
                current_cycle_hours=current_cycle_hours,
                total_distance_miles=round(distance_miles, 2),
                total_drive_hours=round(driving_hours, 2),
                estimated_days=max(1, int(driving_hours / 11))  # At least 1 day
            )
            
            # Add stops (pickup, fuel, rest, dropoff)
            stops = [
                Stop(
                    trip=trip,
                    stop_type='pickup',
                    location=pickup_location,
                    mile_marker=0,
                    duration_hours=0
                )
            ]
            
            # Add fuel stops
            fuel_stop_count = int(distance_miles // fuel_stop_miles)
            for i in range(1, fuel_stop_count + 1):
                mile_marker = min(i * fuel_stop_miles, distance_miles)
                stops.append(Stop(
                    trip=trip,
                    stop_type='fuel',
                    location=f'Fuel Stop {i}',
                    mile_marker=round(mile_marker, 2),
                    duration_hours=0.5  # 30 minutes for fuel stop
                ))
            
            # Add rest stops
            rest_stop_count = int(driving_hours // driving_hours_limit)
            for i in range(1, rest_stop_count + 1):
                mile_marker = min((i * driving_hours_limit * 50), distance_miles)  # Assuming 50 mph average
                stops.append(Stop(
                    trip=trip,
                    stop_type='rest',
                    location=f'Rest Stop {i}',
                    mile_marker=round(mile_marker, 2),
                    duration_hours=off_duty_hours
                ))
            
            # Add dropoff
            stops.append(Stop(
                trip=trip,
                stop_type='dropoff',
                location=dropoff_location,
                mile_marker=round(distance_miles, 2),
                duration_hours=0
            ))
            
            # Save all stops
            Stop.objects.bulk_create(stops)
            
            # Generate daily schedules
            daily_schedules = []
            current_day = 1
            remaining_hours = driving_hours
            
            while remaining_hours > 0 and current_day < 30:  # Prevent infinite loop
                day_hours = min(11, remaining_hours)  # Max 11 hours driving per day
                
                schedule = DailySchedule(
                    trip=trip,
                    day_number=current_day,
                    driving_hours=round(day_hours, 2),
                    on_duty_hours=round(day_hours + 1, 2),  # Driving + breaks
                    off_duty_hours=13,  # 11 hours driving + 1 hour break = 12 hours on duty, 12 off
                    notes=f'Day {current_day} schedule'
                )
                daily_schedules.append(schedule)
                
                remaining_hours -= day_hours
                current_day += 1
            
            # Save all daily schedules
            DailySchedule.objects.bulk_create(daily_schedules)
            
            # Serialize and return the trip with all related data
            trip_serializer = TripSerializer(trip)
            return Response({"status": status.HTTP_201_CREATED, "data": trip_serializer.data}, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'status': status.HTTP_500_INTERNAL_SERVER_ERROR, 'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TripDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint to retrieve, update or delete a trip.
    """
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    lookup_field = 'id'

    def get(self, request, id):
        try:
            trip = Trip.objects.get(id=id)
            trip_serializer = TripSerializer(trip)
            return Response({"status": status.HTTP_200_OK, "data": trip_serializer.data}, status=status.HTTP_200_OK)
        except Trip.DoesNotExist:
            return Response({"status": status.HTTP_404_NOT_FOUND, "error": "Trip not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"status": status.HTTP_500_INTERNAL_SERVER_ERROR, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DailyLogsAPIView(APIView):
    """
    API endpoint to get logs for a specific trip day.
    """
    def get(self, request, trip_id, day_number):
        try:
            schedule = DailySchedule.objects.get(
                trip_id=trip_id,
                day_number=day_number
            )
            
            # Generate log entries for the day
            log_entries = []
            current_hour = 8.0  # Start at 8 AM
            
            # Add driving log entry
            if schedule.driving_hours > 0:
                log_entries.append({
                    'start_hour': current_hour,
                    'end_hour': current_hour + schedule.driving_hours,
                    'status': 'Driving'
                })
                current_hour += schedule.driving_hours
            
            # Add break if needed
            if schedule.on_duty_hours - schedule.driving_hours > 0:
                log_entries.append({
                    'start_hour': current_hour,
                    'end_hour': current_hour + 0.5,  # 30 min break
                    'status': 'Break'
                })
                current_hour += 0.5
            
            # Add off-duty time to complete the day
            if current_hour < 24:  # Only if there's time left in the day
                log_entries.append({
                    'start_hour': current_hour,
                    'end_hour': 24.0,
                    'status': 'Off Duty'
                })
            
            return Response({"data":{
                'trip_id': str(trip_id),
                'day_number': day_number,
                'log_entries': log_entries,
                'total_driving_hours': schedule.driving_hours,
                'total_on_duty_hours': schedule.on_duty_hours,
                'total_off_duty_hours': schedule.off_duty_hours,
                'notes': schedule.notes
            }, "status": status.HTTP_200_OK}, status=status.HTTP_200_OK)
            
        except DailySchedule.DoesNotExist:
            return Response(
                {'error': 'Schedule not found for the specified trip and day'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Legacy views for backward compatibility
class LegacyRouteAPIView(APIView):
    """
    Legacy endpoint for route calculation (kept for backward compatibility).
    """
    def post(self, request):
        return Response(
            {'error': 'This endpoint is deprecated. Please use /api/trips/'},
            status=status.HTTP_410_GONE
        )


class LegacyLogsAPIView(APIView):
    """
    Legacy endpoint for logs (kept for backward compatibility).
    """
    def post(self, request):
        return Response(
            {'error': 'This endpoint is deprecated. Please use /api/trips/<id>/days/<day>/logs/'},
            status=status.HTTP_410_GONE
        )
