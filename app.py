import streamlit as st
import ee
import json
from PIL import Image
from io import BytesIO
import datetime
import concurrent.futures

@st.cache_resource()
def initialize_ee():
    json_data = st.secrets["service_key"]
    service_account = st.secrets["service_email"]
    # Initialize the Earth Engine module.
    credentials = ee.ServiceAccountCredentials(service_account, key_data=json_data)
    ee.Initialize(credentials)
    return ee



ee = initialize_ee()

def calculate_ndvi(image):
    return image.normalizedDifference(['B5', 'B4'])

def get_satellite_image(geometry, year):
    # Convert Python date to Unix time

    date_start = f"{year}-01-01"
    date_end = f"{year}-12-31"
    date_start_unix = int(datetime.datetime.strptime(date_start, "%Y-%m-%d").timestamp() * 1000)
    date_end_unix = int(datetime.datetime.strptime(date_end, "%Y-%m-%d").timestamp() * 1000)
    # Convert GeoJSON geometry to Earth Engine object
    region = ee.Geometry(geometry)

    # Get the satellite image
    image = ee.ImageCollection('LANDSAT/LC08/C01/T1_TOA') \
            .filterBounds(region) \
            .filterDate(ee.Date(date_start_unix), ee.Date(date_end_unix)) \
            .median()  # Taking median composite for cloud removal
    print("passes here")
    # Select the Red and Near-Infrared bands
    red = image.select('B4')
    nir = image.select('B5')

    # Calculate NDVI
    ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
    mean_ndvi_value = ndvi.reduceRegion(reducer=ee.Reducer.mean(), geometry=region, scale=30).getInfo()['NDVI']
    
    # Define visualization parameters for NDVI
    vis_params = {
        'region': region.getInfo(),
        'palette': ['red', 'green','blue'],
        'dimensions': '1024x768'
    }
    
    # Convert to URL for visualization
    url =ndvi.getThumbURL(vis_params)
    print(url)
    # response = requests.get(url)
    # ndvi_image = Image.open(BytesIO(response.content))

    return year, url, mean_ndvi_value

st.title("ARDHI-ai NDVI Calculator ")

# Upload GeoJSON file
uploaded_file = st.file_uploader("Upload a GeoJSON file, you can create one at: [geojson.io](https://geojson.io/)", type=["geojson", "json"])

# Or select from sample data
sample_data = st.selectbox("Or select from sample data", ["", "Penhalonga", "Ngundu", "Gokwe", "Hwange"], index=0)
if sample_data:
    uploaded_file = open(f"samples/{sample_data.lower()}.geojson", "r")

columns = st.columns(2)
with columns[0]:
    start_year= st.slider("Start Year", 2013, 2021, 2013)
with columns[1]:
    end_year = st.slider("End Year", 2013, 2021, 2021)

if start_year > end_year:
    st.error("End year should be after start year.")
    st.stop()

st.write("Upload a GeoJSON and enter the date range to calculate the NDVI.")

if st.button("Calculate NDVI"):
    if uploaded_file:
        geojson = json.load(uploaded_file)
        geometry = geojson['features'][0]['geometry']

        columns = st.columns(3)
        ndvi_scores = {}

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(get_satellite_image,geometry, year): year for year in range(start_year, end_year + 1)}
            ndvi_scores = {}
            with st.spinner('Calculating NDVI...'):
                for future in concurrent.futures.as_completed(futures):
                    year, ndvi_image, avg_ndvi = future.result()
                    ndvi_scores[year] = {'image': ndvi_image, 'avg_ndvi': avg_ndvi}  # Store the NDVI score for the year

                # After the loop finishes
        first_year_ndvi = ndvi_scores[start_year]['avg_ndvi']
        last_year_ndvi = ndvi_scores[end_year]['avg_ndvi']
        difference = last_year_ndvi - first_year_ndvi
        sign = "+" if difference > 0 else "-"

        st.write(f"NDVI in {start_year}: **{first_year_ndvi:.4f}**")
        st.write(f"NDVI in {end_year}: **{last_year_ndvi:.4f}**")
        st.write(f"Difference between {start_year} and {end_year}: **{sign}{abs(difference):.4f}**")
        
        for idx, (year, data) in enumerate(sorted(ndvi_scores.items())):
            with columns[idx % 3]:  # Select the column based on the index
                st.image(data['image'], caption=f"NDVI {year}: {data['avg_ndvi']:.4f}", use_column_width=True)

    else:
        st.error("Please upload a GeoJSON file.")
