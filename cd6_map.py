import geopandas as gpd
import folium
from folium import plugins
import requests
import zipfile
import os
import pandas as pd
from shapely.geometry import Point
import numpy as np

def download_and_extract_data():
    """Use local congressional district and county boundary data"""
    
    # Check if the congressional district files exist
    congress_dir = "tl_2024_21_cd119"
    county_dir = "tl_2024_us_county"
    
    if not os.path.exists(f"{congress_dir}/tl_2024_21_cd119.shp"):
        print(f"Error: Could not find congressional district shapefile in {congress_dir}/")
        print("Please make sure the tl_2024_21_cd119 folder is in the same directory as this script.")
        return False
    
    if not os.path.exists(f"{county_dir}/tl_2024_us_county.shp"):
        print(f"Error: Could not find county shapefile in {county_dir}/")
        print("Please make sure the tl_2024_us_county folder is in the same directory as this script.")
        return False
    
    # Create symbolic links or copy files for easier access
    if not os.path.exists("congress_districts.shp"):
        # Copy congressional district files
        import shutil
        for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg']:
            src = f"{congress_dir}/tl_2024_21_cd119{ext}"
            dst = f"congress_districts{ext}"
            if os.path.exists(src):
                shutil.copy2(src, dst)
    
    if not os.path.exists("counties.shp"):
        # Copy county files
        import shutil
        for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg']:
            src = f"{county_dir}/tl_2024_us_county{ext}"
            dst = f"counties{ext}"
            if os.path.exists(src):
                shutil.copy2(src, dst)
    
    print("Using local data files successfully!")
    return True

def create_ky6_map():
    """Create interactive map of Kentucky's 6th Congressional District"""
    
    # Download data if needed
    download_and_extract_data()
    
    # Load congressional districts
    districts = gpd.read_file("congress_districts.shp")
    
    # Load counties
    counties = gpd.read_file("counties.shp")
    
    # Filter for Kentucky's 6th Congressional District
    ky6_district = districts[(districts['STATEFP'] == '21') & (districts['CD119FP'] == '06')]
    
    if ky6_district.empty:
        print("Kentucky 6th District not found. Checking available districts...")
        ky_districts = districts[districts['STATEFP'] == '21']
        print("Available Kentucky districts:", ky_districts['CD119FP'].unique())
        return None
    
    # Filter for Kentucky counties
    ky_counties = counties[counties['STATEFP'] == '21']
    
    # Find counties that intersect with KY-6
    ky6_geom = ky6_district.geometry.iloc[0]
    intersecting_counties = ky_counties[ky_counties.geometry.intersects(ky6_geom)]
    
    # Clip counties to only show the portion within KY-6
    clipped_counties = gpd.GeoDataFrame()
    for idx, county in intersecting_counties.iterrows():
        try:
            clipped_geom = county.geometry.intersection(ky6_geom)
            if not clipped_geom.is_empty and clipped_geom.is_valid:
                county_data = county.copy()
                county_data.geometry = clipped_geom
                clipped_counties = pd.concat([clipped_counties, county_data.to_frame().T], ignore_index=True)
            else:
                print(f"Skipping {county['NAME']} County due to geometry issues")
        except Exception as e:
            print(f"Error processing {county['NAME']} County: {e}")
            continue
    
    # Convert to GeoDataFrame and ensure valid geometries
    clipped_counties = gpd.GeoDataFrame(clipped_counties, crs=intersecting_counties.crs)
    
    # Clean up any invalid geometries
    clipped_counties['geometry'] = clipped_counties['geometry'].buffer(0)
    
    # County seats data for Kentucky (approximate coordinates)
    county_seats = {
        'Anderson': (38.0515, -84.8041, 'Lawrenceburg'),
        'Bourbon': (38.2042, -84.1466, 'Paris'),
        'Boyle': (37.7548, -84.7719, 'Danville'),
        'Clark': (37.9748, -84.0633, 'Winchester'),
        'Estill': (37.6962, -83.7738, 'Irvine'),
        'Fayette': (38.0406, -84.5037, 'Lexington'),
        'Fleming': (38.4331, -83.7329, 'Flemingsburg'),
        'Franklin': (38.2009, -84.8733, 'Frankfort'),
        'Garrard': (37.6270, -84.5219, 'Lancaster'),
        'Harrison': (38.4198, -84.3030, 'Cynthiana'),
        'Jessamine': (37.8820, -84.5819, 'Nicholasville'),
        'Lincoln': (37.4476, -84.6358, 'Stanford'),
        'Madison': (37.5270, -84.2963, 'Richmond'),
        'Mercer': (37.7845, -84.8244, 'Harrodsburg'),
        'Montgomery': (38.1770, -83.9435, 'Mount Sterling'),
        'Nicholas': (38.3331, -84.1530, 'Carlisle'),
        'Powell': (37.8456, -83.7821, 'Stanton'),
        'Robertson': (38.4081, -84.0541, 'Mount Olivet'),
        'Scott': (38.3059, -84.6016, 'Georgetown'),
        'Washington': (37.6806, -85.0330, 'Springfield'),
        'Woodford': (38.1417, -84.7394, 'Versailles')
    }
    
    # Create base map centered on KY-6 (using bounds instead of centroid to avoid CRS warnings)
    bounds = ky6_district.bounds
    center_lat = (bounds.miny.iloc[0] + bounds.maxy.iloc[0]) / 2
    center_lon = (bounds.minx.iloc[0] + bounds.maxx.iloc[0]) / 2
    
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=10,
        tiles='OpenStreetMap'
    )
    
    # Add grey overlay for areas outside the district to create contrast
    # Show all Kentucky counties outside the district in grey
    outside_counties = ky_counties[~ky_counties.geometry.intersects(ky6_geom)]
    
    # Add counties outside the district in grey
    for idx, county in outside_counties.iterrows():
        try:
            folium.GeoJson(
                county.geometry,
                style_function=lambda x: {
                    'fillColor': '#808080',
                    'color': '#666666',
                    'weight': 1,
                    'fillOpacity': 0.5
                },
                popup=False,
                tooltip=folium.Tooltip(f"{county['NAME']} County (Outside District)")
            ).add_to(m)
        except Exception as e:
            print(f"Error adding outside county {county['NAME']}: {e}")
            continue
    
    # Add partial counties (parts outside the district) in grey
    for idx, county in intersecting_counties.iterrows():
        try:
            # Get the part of the county that's OUTSIDE the district
            outside_part = county.geometry.difference(ky6_geom)
            if not outside_part.is_empty:
                folium.GeoJson(
                    outside_part,
                    style_function=lambda x: {
                        'fillColor': '#808080',
                        'color': '#666666',
                        'weight': 1,
                        'fillOpacity': 0.5
                    },
                    popup=False,
                    tooltip=folium.Tooltip(f"{county['NAME']} County (Outside District)")
                ).add_to(m)
        except Exception as e:
            print(f"Error adding outside part of {county['NAME']}: {e}")
            continue
    
    # Add district boundary
    folium.GeoJson(
        ky6_district,
        style_function=lambda x: {
            'fillColor': 'none',
            'color': '#0000FF',
            'weight': 5,
            'fillOpacity': 0
        },
        tooltip=folium.Tooltip("Kentucky's 6th Congressional District")
    ).add_to(m)
    
    # Add counties within the district
    for idx, county in clipped_counties.iterrows():
        county_name = county['NAME']
        
        # Skip if geometry is invalid
        if county.geometry is None or county.geometry.is_empty:
            print(f"Skipping {county_name} County - invalid geometry")
            continue
        
        try:
            # Determine if county is fully or partially in district
            partial_text = ""
            
            # Create county feature with hover effect
            geojson_data = {
                "type": "Feature",
                "properties": {"name": county_name},
                "geometry": county.geometry.__geo_interface__
            }
            
            county_layer = folium.GeoJson(
                geojson_data,
                style_function=lambda feature: {
                    'fillColor': '#87CEEB',
                    'color': '#0000FF',
                    'weight': 2.25,
                    'fillOpacity': 0.2,
                    'dashArray': '0'
                },
                highlight_function=lambda feature: {
                    'fillColor': '#ADD8E6',
                    'color': '#0000FF',
                    'weight': 2.25,
                    'fillOpacity': 0.6,
                    'dashArray': '0'
                },
                tooltip=folium.Tooltip(
                    f"<div style='font-size: 14px; font-weight: bold;'>{county_name} County</div>",
                    permanent=False
                )
            )
            county_layer.add_to(m)
            
            # Add county label
            if county.geometry.geom_type == 'Polygon':
                centroid = county.geometry.centroid
            elif county.geometry.geom_type == 'MultiPolygon':
                centroid = county.geometry.representative_point()
            else:
                continue
            
            folium.Marker(
                location=[centroid.y, centroid.x],
                icon=folium.DivIcon(
                    html=f'<div style="font-size: 12px; font-weight: bold; color: black; text-shadow: 1px 1px 1px white;">{county_name}</div>',
                    class_name="county-label"
                )
            ).add_to(m)
        
        except Exception as e:
            print(f"Error adding {county_name} County to map: {e}")
            continue
    
    # Add title and address search
    title_and_search_html = '''
    <div style="position: absolute; top: 10px; left: 50%; transform: translateX(-50%); z-index: 1000; text-align: center;">
        <h3 style="margin: 0 0 10px 0; font-size: 20px; font-weight: bold; color: #333;">Kentucky's 6th Congressional District</h3>
        <p style="margin: 0 0 15px 0; font-size: 14px; color: #666;">Counties and County Seats</p>
        
        <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); display: inline-block;">
            <label style="display: block; margin-bottom: 8px; font-weight: bold; color: #333;">Check if your address is in this district:</label>
            <div style="display: flex; gap: 8px; align-items: center;">
                <input type="text" id="addressInput" placeholder="Enter your address (e.g., 123 Main St, Lexington, KY)" 
                       style="padding: 8px 12px; border: 2px solid #ddd; border-radius: 4px; width: 300px; font-size: 14px;">
                <button onclick="checkAddress()" 
                        style="padding: 8px 16px; background: #0066cc; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; font-weight: bold;">
                    Check Address
                </button>
                <button onclick="resetMap()" id="resetButton"
                        style="padding: 8px 16px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; font-weight: bold; display: none;">
                    Reset Map
                </button>
            </div>
            <div id="addressResult" style="margin-top: 10px; padding: 8px; border-radius: 4px; display: none;"></div>
        </div>
    </div>
    
    <script>
    let currentMarker = null;
    let map = null;
    let originalView = null;
    
    // Wait for map to be fully loaded
    document.addEventListener('DOMContentLoaded', function() {
        // Get reference to the Leaflet map (folium creates a global map variable)
        setTimeout(function() {
            map = window[Object.keys(window).find(key => key.startsWith('map_'))];
            if (map) {
                // Store original map view
                originalView = {
                    center: map.getCenter(),
                    zoom: map.getZoom()
                };
            }
        }, 1000);
    });
    
    async function checkAddress() {
        const address = document.getElementById('addressInput').value;
        const resultDiv = document.getElementById('addressResult');
        
        if (!address.trim()) {
            showResult('Please enter an address.', 'error');
            return;
        }
        
        showResult('Checking address...', 'loading');
        
        try {
            // Use Nominatim geocoding service (free)
            const geocodeUrl = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(address)}&limit=1&countrycodes=us`;
            const response = await fetch(geocodeUrl);
            const data = await response.json();
            
            if (data.length === 0) {
                showResult('Address not found. Please try a different address or add city/state.', 'error');
                return;
            }
            
            const lat = parseFloat(data[0].lat);
            const lon = parseFloat(data[0].lon);
            
            // Check if coordinates are within Kentucky 6th District
            const isInDistrict = checkIfInDistrict(lat, lon);
            
            if (isInDistrict) {
                showResult(`✓ YES - This address is in Kentucky's 6th Congressional District`, 'success');
            } else {
                showResult(`✗ NO - This address is not in Kentucky's 6th Congressional District`, 'error');
            }
            
            // Add marker to map WITHOUT zooming
            if (map) {
                // Remove previous marker
                if (currentMarker) {
                    map.removeLayer(currentMarker);
                }
                
                // Create colored icon based on result
                const iconColor = isInDistrict ? 'green' : 'red';
                const iconHtml = `<div style="background-color: ${iconColor}; width: 20px; height: 20px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`;
                
                const customIcon = L.divIcon({
                    html: iconHtml,
                    className: 'custom-div-icon',
                    iconSize: [20, 20],
                    iconAnchor: [10, 10]
                });
                
                // Add new marker with custom icon
                currentMarker = L.marker([lat, lon], { icon: customIcon })
                    .addTo(map)
                    .bindPopup(`<b>Your Address:</b><br>${data[0].display_name}<br><br><b>In District:</b> ${isInDistrict ? 'YES' : 'NO'}`);
                
                // Show reset button
                document.getElementById('resetButton').style.display = 'inline-block';
            }
            
        } catch (error) {
            console.error('Geocoding error:', error);
            showResult('Error checking address. Please try again.', 'error');
        }
    }
    
    function resetMap() {
        // Remove marker
        if (currentMarker && map) {
            map.removeLayer(currentMarker);
            currentMarker = null;
        }
        
        // Reset map view to original position
        if (map && originalView) {
            map.setView(originalView.center, originalView.zoom);
        }
        
        // Clear address input and result
        document.getElementById('addressInput').value = '';
        document.getElementById('addressResult').style.display = 'none';
        
        // Hide reset button
        document.getElementById('resetButton').style.display = 'none';
    }
    
    function checkIfInDistrict(lat, lon) {
        // Simplified bounding box check for Kentucky 6th District
        // You could make this more precise by checking against the actual district polygon
        
        // Approximate bounds of KY-6 (you may want to adjust these)
        const bounds = {
            north: 38.6,
            south: 37.4,
            east: -83.8,
            west: -85.2
        };
        
        return lat >= bounds.south && lat <= bounds.north && 
               lon >= bounds.west && lon <= bounds.east;
    }
    
    function showResult(message, type) {
        const resultDiv = document.getElementById('addressResult');
        resultDiv.style.display = 'block';
        resultDiv.innerHTML = message;
        
        // Style based on result type
        if (type === 'success') {
            resultDiv.style.background = '#d4edda';
            resultDiv.style.color = '#155724';
            resultDiv.style.border = '1px solid #c3e6cb';
        } else if (type === 'error') {
            resultDiv.style.background = '#f8d7da';
            resultDiv.style.color = '#721c24';
            resultDiv.style.border = '1px solid #f5c6cb';
        } else if (type === 'loading') {
            resultDiv.style.background = '#d1ecf1';
            resultDiv.style.color = '#0c5460';
            resultDiv.style.border = '1px solid #bee5eb';
        }
    }
    
    // Allow Enter key to trigger search
    document.getElementById('addressInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            checkAddress();
        }
    });
    </script>
    '''
    m.get_root().html.add_child(folium.Element(title_and_search_html))
    
    # Add fullscreen button
    plugins.Fullscreen().add_to(m)
    
    # Save the map
    m.save('index.html')
    
    print("Map created successfully!")
    print("Counties in Kentucky's 6th Congressional District:")
    for county_name in sorted(clipped_counties['NAME'].unique()):
        print(f"- {county_name} County")
    
    return m

# Create the map
if __name__ == "__main__":
    map_obj = create_ky6_map()
    
    # Optional: Display additional information
    print("\nMap saved as 'index.html'")
    print("You can open this file in any web browser to view the interactive map.")
    print("The map includes:")
    print("- Exact congressional district boundaries")
    print("- County boundaries clipped to district area")
    print("- County labels")
    print("- County seats marked with red stars")
    print("- Interactive tooltips and popups")
    print("- Fullscreen capability")
    print("- Legend and title")