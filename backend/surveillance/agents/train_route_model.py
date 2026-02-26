import os
import shapefile
import joblib
from shapely.geometry import LineString, Polygon

# Safe corridors: motorways, trunks, primary roads
SAFE_TYPES = {'motorway', 'trunk', 'primary'}

# Risk zones: residential, living streets, pedestrian zones, unclassified roads
RISK_TYPES = {'residential', 'living_street', 'pedestrian', 'unclassified'}

# Bounding box for filtering (Longitude, Latitude) - Targeting Delhi region
# ~ 28.2 to 29.0 N, 76.8 to 77.5 E
MIN_LON, MAX_LON = 76.8, 77.5
MIN_LAT, MAX_LAT = 28.2, 29.0

# Buffer distance (~100 meters in degrees)
BUFFER_DIST = 0.001

def in_bbox(bbox):
    """Check if the shape's bbox intersects with our region of interest."""
    s_min_lon, s_min_lat, s_max_lon, s_max_lat = bbox
    # If the shape is completely outside our bbox, return False
    if s_max_lon < MIN_LON or s_min_lon > MAX_LON:
        return False
    if s_max_lat < MIN_LAT or s_min_lat > MAX_LAT:
        return False
    return True

def create_model():
    sf = shapefile.Reader('roads/roads.shp')
    
    safe_corridors = []
    risk_zones = []
    
    print("Parsing shapefile...")
    total_records = len(sf)
    
    for i, shape_record in enumerate(sf.iterShapeRecords()):
        if i % 50000 == 0:
            print(f"Processed {i}/{total_records} shapes")
            
        rec = shape_record.record.as_dict()
        road_type = rec.get('type')
        name = rec.get('name') or "Unnamed Road"
        
        # Only process if it's one of the types we care about
        is_safe = road_type in SAFE_TYPES
        is_risk = road_type in RISK_TYPES
        
        if not (is_safe or is_risk):
            continue
            
        shape = shape_record.shape
        
        # Fast bounding box check
        if not in_bbox(shape.bbox):
            continue
            
        # Extract coordinates and make a Shapely LineString
        points = shape.points
        if len(points) < 2:
            continue
            
        try:
            line = LineString(points)
            # Buffer the line to create a Polygon
            poly = line.buffer(BUFFER_DIST)
            
            # If the resulting geometry is essentially empty, skip it
            if poly.is_empty:
                continue
                
            # Handle MultiPolygons if necessary, but usually buffering a LineString yields a Polygon
            polygons = []
            if poly.geom_type == 'Polygon':
                polygons.append(poly)
            elif poly.geom_type == 'MultiPolygon':
                polygons.extend(list(poly.geoms))
            else:
                continue
                
            # Extract exterior coordinates
            for p in polygons:
                coords = list(p.exterior.coords)
                
                # Format: {"name": string, "coordinates": list of (lon, lat)}
                model_entry = {
                    "name": f"{name} ({road_type})",
                    "coordinates": coords
                }
                
                if is_safe:
                    safe_corridors.append(model_entry)
                elif is_risk:
                    risk_zones.append(model_entry)
                    
        except Exception as e:
            # Skip shapes that fail geometry construction
            continue

    print(f"\nExtracted {len(safe_corridors)} safe corridors.")
    print(f"Extracted {len(risk_zones)} risk zones.")
    
    # Save the model
    os.makedirs('AI-models', exist_ok=True)
    model_path = 'AI-models/route_model.pkl'
    
    model_data = {
        "safe_corridors": safe_corridors,
        "risk_zones": risk_zones
    }
    
    joblib.dump(model_data, model_path)
    print(f"Model saved to {model_path} ({os.path.getsize(model_path) // 1024} KB)")

if __name__ == '__main__':
    create_model()
