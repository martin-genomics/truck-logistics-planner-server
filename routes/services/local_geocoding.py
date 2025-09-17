import mapbox
from mapbox import Directions, Geocoder
from typing import Dict, List, Optional, Tuple
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MapboxDirectionsService:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.directions_service = Directions(access_token=access_token)
        self.geocoder = Geocoder(access_token=access_token)
    
    def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Convert address string to coordinates (longitude, latitude)
        """
        try:
            response = self.geocoder.forward(address)
            
            if response.status_code == 200:
                data = response.json()
                if data['features']:
                    # Get the first result's coordinates
                    coordinates = data['features'][0]['geometry']['coordinates']
                    return tuple(coordinates)  # (longitude, latitude)
                else:
                    logger.warning(f"No results found for address: {address}")
                    return None
            else:
                logger.error(f"Geocoding failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error in geocoding: {e}")
            return None
    
    def get_coordinates_from_request(self, request_data: Dict) -> Dict:
        """
        Extract and geocode all addresses from the request data
        """
        coordinates = {}
        
        # Geocode origin
        if 'origin' in request_data:
            origin_coords = self.geocode_address(request_data['origin'])
            if origin_coords:
                coordinates['origin'] = origin_coords
            else:
                raise ValueError(f"Could not geocode origin: {request_data['origin']}")
        
        # Geocode destination
        if 'destination' in request_data:
            dest_coords = self.geocode_address(request_data['destination'])
            if dest_coords:
                coordinates['destination'] = dest_coords
            else:
                raise ValueError(f"Could not geocode destination: {request_data['destination']}")
        
        # Geocode pickup location (if provided)
        if 'pickup_location' in request_data and request_data['pickup_location']:
            pickup_coords = self.geocode_address(request_data['pickup_location'])
            if pickup_coords:
                coordinates['pickup_location'] = pickup_coords
            else:
                logger.warning(f"Could not geocode pickup location: {request_data['pickup_location']}")
        
        # Geocode dropoff location (if provided)
        if 'dropoff_location' in request_data and request_data['dropoff_location']:
            dropoff_coords = self.geocode_address(request_data['dropoff_location'])
            if dropoff_coords:
                coordinates['dropoff_location'] = dropoff_coords
            else:
                logger.warning(f"Could not geocode dropoff location: {request_data['dropoff_location']}")
        
        return coordinates
    
    def get_directions_with_waypoints(self, coordinates: Dict, profile: str = 'mapbox/driving') -> Optional[Dict]:
        """
        Get directions with optional pickup and dropoff waypoints
        """
        try:
            # Build waypoints list in correct order
            waypoints = []
            
            # Start with origin
            if 'origin' in coordinates:
                waypoints.append(coordinates['origin'])
            
            # Add pickup location if provided (after origin)
            if 'pickup_location' in coordinates:
                waypoints.append(coordinates['pickup_location'])
            
            # Add dropoff location if provided (before destination)
            if 'dropoff_location' in coordinates:
                waypoints.append(coordinates['dropoff_location'])
            
            # End with destination
            if 'destination' in coordinates:
                waypoints.append(coordinates['destination'])
            
            # Ensure we have at least 2 waypoints
            if len(waypoints) < 2:
                raise ValueError("Need at least origin and destination coordinates")
            
            # Get directions
            response = self.directions_service.directions(
                waypoints,
                profile=profile,
                geometries='geojson',
                steps=True,
                overview='full'
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Directions API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting directions: {e}")
            return None
    
    def parse_directions_response(self, directions_data: Dict) -> Dict:
        """
        Parse and format the directions response
        """
        if not directions_data or 'routes' not in directions_data:
            return {}
        
        route = directions_data['routes'][0]
        leg = route['legs'][0]
        
        result = {
            'distance': route['distance'],  # meters
            'duration': route['duration'],  # seconds
            'geometry': route['geometry'],
            'waypoints': directions_data['waypoints'],
            'steps': []
        }
        
        # Extract step-by-step instructions
        for step in leg['steps']:
            result['steps'].append({
                'instruction': step['maneuver']['instruction'],
                'distance': step['distance'],
                'duration': step['duration'],
                'maneuver_type': step['maneuver']['type'],
                'waypoints': step['geometry']['coordinates']
            })
        
        return result
    
    def process_directions_request(self, request_data: Dict) -> Dict:
        """
        Complete processing of directions request
        """
        try:
            # Step 1: Geocode all addresses to coordinates
            logger.info("Geocoding addresses...")
            coordinates = self.get_coordinates_from_request(request_data)
            
            # Step 2: Get directions with waypoints
            logger.info("Getting directions...")
            directions_data = self.get_directions_with_waypoints(
                coordinates, 
                profile=request_data.get('profile', 'mapbox/driving')
            )
            
            if not directions_data:
                return {'error': 'Failed to get directions'}
            
            # Step 3: Parse the response
            logger.info("Parsing directions...")
            parsed_data = self.parse_directions_response(directions_data)
            
            # Add original coordinates to response
            parsed_data['coordinates'] = coordinates
            
            return {
                'success': True,
                'data': parsed_data,
                'metadata': {
                    'origin': request_data.get('origin'),
                    'destination': request_data.get('destination'),
                    'pickup_location': request_data.get('pickup_location'),
                    'dropoff_location': request_data.get('dropoff_location')
                }
            }
            
        except ValueError as e:
            logger.error(f"Validation error: {e}")
            return {'error': str(e), 'success': False}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {'error': 'Internal server error', 'success': False}
