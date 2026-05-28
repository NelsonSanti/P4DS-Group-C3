import json
import pandas as pd
import geopandas as gpd
import numpy as np
import ipywidgets as widgets
import ipyleaflet
from ipyleaflet import Map, FullScreenControl, Marker, MarkerCluster, Popup, GeoData
from branca.colormap import linear
from IPython.display import display
from unidecode import unidecode

html_label = widgets.HTML(
    value='<div style="font-family: "Inter", sans-serif; font-size: 1.6rem; font-weight: 700; background: linear-gradient(45deg, #4f46e5, #06b6d4); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0; padding: 8px 0;">Hover on a location</div>',
)
html_control = ipyleaflet.WidgetControl(widget=html_label, position='topright')

def get_map(*, map_center=None, title="Portugal", basemap=ipyleaflet.basemaps.CartoDB.Positron) -> Map:
    # ipyleaflet.basemaps.OpenStreetMap.Mapnik
    # get a map locked to Portuguese boundary
    portugal_center = (39.3999, -8.2245)
    portugal_bounds = [(36.7, -9.7), (42.3, -6.1)]

    if map_center: # for markers, we want representative centers at each municipality/district.
        m = m = Map(
            center=map_center,
            zoom=8,
            min_zoom=6,
            max_zoom=12,
            max_bounds=portugal_bounds,
            scroll_wheel_zoom=True,
            basemap=basemap,
        )
    else:
        m = Map(
            center=portugal_center,
            zoom=8,
            min_zoom=6,
            max_zoom=12,
            max_bounds=portugal_bounds,
            scroll_wheel_zoom=True,
            basemap=basemap,
        )
    
    m.add(FullScreenControl())

    map_title = widgets.HTML(
        value=f'<div style="font-family: "Inter", sans-serif; font-size: 1.6rem; font-weight: 700; background: linear-gradient(45deg, #4f46e5, #06b6d4); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0; padding: 8px 0;">{title}</div>',
        layout=widgets.Layout(padding='0px 10px')
    )
    title_control = ipyleaflet.WidgetControl(widget=map_title, position='bottomleft')
    m.add_control(title_control)

    return m

def with_html_label(m:Map) -> Map:
    m.add_control(html_control)
    return m


geojson_url = r"C:\Users\Nelso\Documents\NOVA IMS\Programming for Data Science\Group Project\P4DS-Group-C3\startup-distribution-portugal\data\processed_data\portugal-municipalities.geojson"


#def get_geojson():
#    with open(geojson_url, 'r') as f:
#        geo_data = json.load(f)
#        # promote district and municipal for key mapping on choropleths and remove null districts
#        for i in range(len(geo_data["features"])-1, -1, -1): # there are other ways :)
#            feature = geo_data["features"][i]
#            if feature["properties"]["Concelho"] is None:
#                del geo_data["features"][i]
#            else:
#                geo_data["features"][i]["id"] = feature["properties"]["Concelho"]
        
#        return geo_data


def get_geojson():
    with open(geojson_url, 'r', encoding='utf-8') as f:
        geo_data = json.load(f)

        # promote district and municipal for key mapping on choropleths
        # and remove null districts
        for i in range(len(geo_data["features"]) - 1, -1, -1):

            feature = geo_data["features"][i]

            if feature["properties"]["Concelho"] is None:
                del geo_data["features"][i]

            else:
                # normalize municipality names
                municipality_name = (
                    unidecode(
                        feature["properties"]["Concelho"].upper()
                    )
                    .replace(" ", "-")
                )

                geo_data["features"][i]["id"] = municipality_name

        return geo_data


def get_gpd_dataframe():
    geojson_dict = get_geojson()
    gdf = gpd.GeoDataFrame.from_features(geojson_dict["features"])
    gdf = gdf.set_crs(epsg=4326)

    return gdf

def update_html(feature, **kwargs):
    name = feature['properties']['Concelho']
    html_label.value = f'<div style="font-family: "Inter", sans-serif; font-size: 1.6rem; font-weight: 700; background: linear-gradient(45deg, #4f46e5, #06b6d4); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0; padding: 8px 0;">{name}</div>'

def state_style_callback(feature):
    return {
        'fillColor': '#4a7c59',   # Elegant sage/slate green (neutral yet distinct)
        'color': '#ffffff',       # Crisp white border lines
        'weight': 1.2,            # Thin, sleek borders
        'opacity': 0.6,           # Full opacity for the white line border
        'fillOpacity': 0.35       # Low opacity lets basemap details peek through beautifully
    }

hover_style = {
    'fillColor': '#2b5037',       # Deepens the green shade on hover
    'color': '#ffffff',           # Keeps the crisp white boundary line
    'weight': 2.0,                # Marginally thickens border to emphasize selection
    'fillOpacity': 0.6           # Brightens up the fill significantly
}

style = {
    'fillColor': '#2b5c8f', # Sleek slate blue
    'fillOpacity': 0.3,     # Translucent fill
    'color': '#ffffff',     # Pure white crisp borders
    'weight': 1.5,          # Mid-thin borders
    'dashArray': '3, 3'     # Elegant dashed state borders
}

def overlay_pt_districts(m:Map):
    geojson_layer = ipyleaflet.GeoJSON(
        data=get_geojson(),
        style_callback=state_style_callback,
        style=style,
        hover_style=hover_style,
    )
    geojson_layer.on_hover(update_html)

    m.add_layer(geojson_layer)
    

def plot_point_map(df: pd.DataFrame, *, label:str='municipality', metric:str='metric', title="Portugal", html_popup_template:str=None):
    """
        Plot a Point Map on a Portugal Municipality layout.

        Note: The label (municipality) is mapped directly to Portugal's `Concelho`
    """
    df = df.copy() # defensive copy
    df[label] = df[label].str.upper()
    gdf = get_gpd_dataframe()

    # centroids = gdf.geometry.centroid
    # map_center = [gdf.unary_union.centroid.y, gdf.unary_union.centroid.x]
    centroid = gdf.union_all().representative_point()
    map_center = [centroid.y, centroid.x]
    m = get_map(map_center=map_center, title=title)
    m = with_html_label(m)
    overlay_pt_districts(m)

    merged_gdf = gdf.merge(df, left_on='Concelho',right_on=label)
    
    # iterate over DataFrame and register interactive markers
    cluster_markers = [] # we're using cluster markers for efficient rendering.
    for index, row in merged_gdf.iterrows():
        # construct distinct marker and make sure they fall inside the right polygons
        rep_point = row.geometry.representative_point()
        lat, lon = rep_point.y, rep_point.x

        marker = Marker(location=(lat,lon), draggable=False, opacity=0.7)
        
        # render customized HTML layout popup attached to each landmark coordinate
        message = widgets.HTML(value=f"""
            <div style="font-family: Arial, sans-serif; padding: 5px;">
                <b style="color: #2C3E50; font-size: 14px;">{row[label]}</b><br>
                <span style="color: #7F8C8D;">Performance {metric}:</span> 
                <strong style="color: #27AE60;">{row[metric]}</strong>
            </div>
        """)
        
        marker.popup = message
        cluster_markers.append(marker)
    
    marker_cluster = MarkerCluster(markers=cluster_markers)
    m.add_layer(marker_cluster)
    
    return m # returns m, can be saved, displayed etc.

def plot_point_map_with_coods(df: pd.DataFrame, *, label:str='municipality', metric:str='metric', title="Portugal", html_popup_template:str=None):
    """
        Plot a Point Map on a Portugal Municipality layout.

        Note: The longitude and latitude columns are required in the dataframe.
    """
    m = get_map(title=title)
    m = with_html_label(m)
    overlay_pt_districts(m)

    df = df.copy() # defensive copy
    
    # 4. Iterate over DataFrame to systematically register interactive markers
    for index, row in df.iterrows():
        # construct distinct marker
        marker = Marker(location=(row['latitude'], row['longitude']), draggable=False, opacity=0.6)
        
        # render customized HTML layout popup attached to each landmark coordinate
        message = widgets.HTML(value=f"""
            <div style="font-family: Arial, sans-serif; padding: 5px;">
                <b style="color: #2C3E50; font-size: 14px;">{row[label]}</b><br>
                <span style="color: #7F8C8D;">Performance {metric}:</span> 
                <strong style="color: #27AE60;">{row[metric]}</strong>
            </div>
        """)
        
        marker.popup = message
        m.add(marker)
    
    return m

def plot_choropleth(df: pd.DataFrame, *, label:str="municipality", metric:str="metric", op:str="sum", title="Portugal", html_popup_template:str=None):
    """
        Plot a Choropleth Map on a Portugal Municipality layout.

        Note: The `municipality` column is required in the dataframe.
    """

    m = get_map(title=title)
    m = with_html_label(m)

    df = df.copy()  # defensive copy
    
    df[metric] = pd.to_numeric(df[metric], errors="coerce").fillna(0)

    agg_df = (
        df.groupby(label).agg(value=(metric, op)).reset_index()
    )

    # generate lookup dictionary
    value_dict = pd.Series(
        agg_df.value.values,
        index=agg_df[label]
    ).to_dict()

    geo_data = get_geojson()

    # fill missing municipalities with 0
    for feature in geo_data["features"]:
        municipality_id = feature["id"]

        if municipality_id not in value_dict:
            value_dict[municipality_id] = 0

    # dynamic color scale
    colormap = linear.magma.scale(
        min(value_dict.values()),
        max(value_dict.values())
    )

    layer = ipyleaflet.Choropleth(
        geo_data=geo_data,
        choro_data=value_dict,
        key_on="id",
        colormap=colormap,
        border_color='black',
        style={
            "fillOpacity": 0.6,
            "dashArray": "5, 5",
            "weight": 1,
            "color": "gray"
        },
        hover_style={
            "fillOpacity": 0.9,
            "color": "#2c3e50",
            "weight": 2,
        },
    )

    def update_hover_label(**kwargs):

        feature = kwargs.get('feature', {})
        properties = feature.get('properties', {})

        if properties:

            name = properties.get('Concelho', 'Unknown')

            normalized_name = (
                unidecode(name.upper())
                .replace(" ", "-")
            )

            value = value_dict.get(normalized_name, 0)

            html_label.value = f'''
            <div style="
                font-family: Inter, sans-serif;
                font-size: 1.1rem;
                font-weight: 700;
                background: white;
                padding: 10px;
                border-radius: 8px;
            ">
                <b>{name}</b><br>
                Value: {value}
            </div>
            '''

    layer.on_hover(update_hover_label)

    m.add(layer)
    
    metric_labels = {
    "startup_count": "Startup Count",
    "funding": "Funding (Million EUR)"
    }

    legend = ipyleaflet.ColormapControl(
        colormap=colormap,
        position="bottomright",
        caption=metric_labels.get(metric, metric),
    )

    m.add(legend)

    return m
