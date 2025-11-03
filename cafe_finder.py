import requests
import streamlit as st
from geopy.distance import geodesic
import geocoder
import time
import folium
from streamlit_folium import st_folium

# -----------------------------
# Page configuration
# -----------------------------
st.set_page_config(page_title="☕ Cafe Finder", layout="wide", page_icon="☕")
st.markdown("<h1 style='text-align:center; color:#FF6600;'>☕ Cafe Finder</h1>", unsafe_allow_html=True)
st.write("Find nearby cafes for free using OpenStreetMap — sorted by distance, with clickable directions!")

# -----------------------------
# Session state
# -----------------------------
if "cafes_fetched" not in st.session_state:
    st.session_state.cafes_fetched = False
    st.session_state.cafes_data = []
    st.session_state.lat = None
    st.session_state.lng = None
    st.session_state.radius = 1000

# -----------------------------
# Layout
# -----------------------------
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("🛠 Controls")
    use_auto = st.checkbox("Auto-detect my location", value=True)

    if use_auto:
        g = geocoder.ip('me')
        if g.ok:
            lat, lng = g.latlng
            st.success(f"Detected location: {lat:.5f}, {lng:.5f}")
        else:
            st.warning("Could not auto-detect. Enter manually below.")
            use_auto = False

    if not use_auto:
        location_input = st.text_input("Enter location (lat,lng)", "12.9716,77.5946")
        try:
            lat, lng = map(float, location_input.split(","))
        except:
            st.error("Invalid input. Use format: lat,lng")
            st.stop()

    st.session_state.lat = lat
    st.session_state.lng = lng
    st.session_state.radius = st.slider("Search radius (meters)", 500, 2000, st.session_state.radius)

    if st.button("🔍 Find Cafes"):
        st.session_state.cafes_fetched = True
        st.session_state.cafes_data = []

with col2:
    st.subheader("🗺️ Map / Results")

# -----------------------------
# Fetch function
# -----------------------------
def fetch_cafes(lat, lng, radius):
    servers = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter"
    ]
    query = f"""
    [out:json];
    node
      [amenity=cafe]
      (around:{radius},{lat},{lng});
    out;
    """
    for server in servers:
        try:
            r = requests.get(server, params={"data": query}, timeout=25)
            r.raise_for_status()
            data = r.json().get("elements", [])
            if data:
                return data
        except:
            time.sleep(1)
    return []

# -----------------------------
# Main logic
# -----------------------------
if st.session_state.cafes_fetched:
    if not st.session_state.cafes_data:
        st.info("Fetching nearby cafes...")
        cafes = fetch_cafes(st.session_state.lat, st.session_state.lng, st.session_state.radius)
        if not cafes:
            st.error("Could not fetch cafes. Try again later or reduce radius.")
            st.session_state.cafes_fetched = False
        else:
            user_loc = (st.session_state.lat, st.session_state.lng)
            for cafe in cafes:
                cafe_loc = (cafe["lat"], cafe["lon"])
                cafe["distance"] = geodesic(user_loc, cafe_loc).meters
            cafes.sort(key=lambda x: x["distance"])
            st.session_state.cafes_data = cafes

    # -----------------------------
    # Display cafes
    # -----------------------------
    cafes = st.session_state.cafes_data
    user_loc = (st.session_state.lat, st.session_state.lng)

    st.subheader(f"Top {min(len(cafes), 20)} cafes near you:")
    for cafe in cafes[:20]:
        name = cafe["tags"].get("name", "Unnamed Cafe")
        distance = int(cafe["distance"])
        lat_c, lng_c = cafe["lat"], cafe["lon"]
        osm_link = f"https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route={user_loc[0]},{user_loc[1]}%3B{lat_c},{lng_c}"
        with st.expander(f"☕ {name} — {distance} m away"):
            st.markdown(f"[Get Directions 🗺️]({osm_link})", unsafe_allow_html=True)

    # -----------------------------
    # Display map
    # -----------------------------
    cafe_map = folium.Map(location=user_loc, zoom_start=15)
    folium.Marker(user_loc, popup="📍 You are here", icon=folium.Icon(color="blue")).add_to(cafe_map)
    for cafe in cafes[:20]:
        name = cafe["tags"].get("name", "Unnamed Cafe")
        distance = int(cafe["distance"])
        folium.Marker(
            [cafe["lat"], cafe["lon"]],
            popup=f"☕ {name} ({distance} m)",
            icon=folium.Icon(color="red", icon="coffee", prefix="fa")
        ).add_to(cafe_map)

    st_data = st_folium(cafe_map, width=700, height=500)
