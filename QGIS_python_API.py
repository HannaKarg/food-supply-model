import os
import pandas as pd
import geopandas
from sqlalchemy import create_engine 
import processing
import requests
from os.path import exists
from qgis.core import *
from qgis.PyQt.QtCore import QVariant

## Data directory

myDirInput="/my_InputDirectory/"
myDirOutput="/my_OutputDirectory/"

food_flow_commodity_df=pd.read_csv(myDirInput+"food_flow_commodity_list.csv", delimiter=";")
city_list=["Tamale", "Bamako", "Ouagadougou", "Bamenda"]

# database connection

db_connection_url = "postgresql://postgres:postgres@localhost:5432/postgres"
con = create_engine(db_connection_url)

## Join spatial characteristics to location data

# point sources of food flows as a subset of location data (here accessed in PostgreSQL; available as .csv files in InputData/LocationData)

for city in city_list:
    if city=='Tamale':
        city_abbr='tle'
        city_locations='spatial'
    elif city=='Bamako':
        city_abbr='bko'
        city_locations='bamako'
    elif city=='Ouagadougou':
        city_abbr='ouaga'
        city_locations='ouaga'
    elif city=='Bamenda':
        city_abbr='bda'
        city_locations='bamenda'

    sql = "SELECT id, geom from food_flow_locations_"+city_locations
    df = geopandas.read_postgis(sql, con)
    layer = QgsVectorLayer(df.to_json(),f"food_flow_locations_{city_locations}","ogr")
    #QgsProject.instance().addMapLayer(layer)
    
    layer_reproject=processing.run("native:reprojectlayer", {
    'INPUT': layer,
    'OPERATION': '+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad +step +proj=sinu +lon_0=15 +x_0=0 +y_0=0 +ellps=WGS84',
    'TARGET_CRS': QgsCoordinateReferenceSystem('ESRI:102011'),
    'OUTPUT': myDirOutput+f'Locations/food_flow_locations_city}'
    })['OUTPUT']
    #QgsProject.instance().addMapLayer(layer_reproject)
    
# compute 50 km buffer around locations

    layer_buffer50km_wo_area=processing.run("native:buffer", {
    'DISSOLVE' : False, 
    'DISTANCE' : 50000, 
    'END_CAP_STYLE' : 0, 
    'INPUT' : layer_reproject,
    'JOIN_STYLE' : 0, 
    'MITER_LIMIT' : 2, 
    'OUTPUT' : 'TEMPORARY_OUTPUT', 
    'SEGMENTS' : 5 
    })['OUTPUT']
    
    processing.run("native:savefeatures", { 
    'DATASOURCE_OPTIONS' : '', 
    'INPUT' : layer_buffer50km_wo_area, 
    'LAYER_NAME' : f'food_flow_locations_buffer_{city}', 
    'LAYER_OPTIONS' : '', 
    'OUTPUT' : myDirOutput+f'Locations/food_flow_locations_buffer_{city}'
    })['OUTPUT']


# access GAEZ4 suitability data for selected commodities (siLa: low input, rainfed (all phases))

for item in food_flow_commodity_df.GAEZ4_acronym:
    path = "https://s3.eu-west-1.amazonaws.com/data.gaezdev.aws.fao.org/res05/CRUTS32/Hist/8110L/siLa_"+item+".tif"
    response = requests.get(path)
    if response.status_code == 200:
        print('Web site exists')

        suitability_raster=QgsRasterLayer(path, f"suitability_{item}")
        
        #reproject raster layer 
        
        suitability_reproject=processing.run("gdal:warpreproject", {
        'DATA_TYPE' : 0, 
        'EXTRA' : '',
        'INPUT': suitability_raster,
        'MULTITHREADING' : False, 
        'NODATA' : None, 
        'OPTIONS' : '', 
        'OUTPUT' : 'TEMPORARY_OUTPUT', 
        'RESAMPLING' : 0, 
        'SOURCE_CRS' : QgsCoordinateReferenceSystem('EPSG:4326'), 
        'TARGET_CRS' : QgsCoordinateReferenceSystem('ESRI:102011'), 
        'TARGET_EXTENT' : '-3825828.976600000,378916.779800000,-244678.581200000,4130201.396400000 [ESRI:102011]', 
        'TARGET_EXTENT_CRS' : QgsCoordinateReferenceSystem('ESRI:102011'), 
        'TARGET_RESOLUTION' : None,
        'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        })['OUTPUT']
    
        # vectorize
    
        suitability_vector=processing.run("gdal:polygonize",{ 
        'BAND' : 1, 
        'EIGHT_CONNECTEDNESS' : False, 
        'EXTRA' : '', 
        'FIELD' : 'Class', 
        'INPUT' : suitability_reproject, 
        'OUTPUT' : 'TEMPORARY_OUTPUT'
        })['OUTPUT']
        
        # Extract by attribute 
    
        suitability_only=processing.run("qgis:extractbyattribute", {
        'FIELD' : 'Class', 
        'INPUT' : suitability_vector,
        'OPERATOR' : 1, 
        'OUTPUT' : 'TEMPORARY_OUTPUT', 
        'VALUE' : '0'
        })['OUTPUT']
    
        # fix geometries
    
        suitability_fix=processing.run("native:fixgeometries", {
        'INPUT' : suitability_only,
        'OUTPUT' : 'TEMPORARY_OUTPUT'
        })['OUTPUT']
    
    
        # dissolve
    
        suitability_dissolved=processing.run("qgis:dissolve", {
        'FIELD' : ['Class'], 
        'INPUT' : suitability_fix,
        'OUTPUT' : myDirOutput+f'GAEZ4_suitability/agric_suitability_{item}.gpkg'
        })['OUTPUT']
    else:
        continue


# compute suitability per buffer

suitability_directory=os.listdir(myDirOutput+'GAEZ4_suitability')

for city in city_list:
    if city=='Tamale':
        city_abbr='tle'
        city_locations='spatial'
    elif city=='Bamako':
        city_abbr='bko'
        city_locations='bamako'
    elif city=='Ouagadougou':
        city_abbr='ouaga'
        city_locations='ouaga'
    elif city=='Bamenda':
        city_abbr='bda'
        city_locations='bamenda'
    
    # recalculate buffer_area_m
    
    buffer_new_area=processing.run("qgis:advancedpythonfieldcalculator", {
    'FIELD_LENGTH' : 8, 
    'FIELD_NAME' : 'buffer_area_m_clip', 
    'FIELD_PRECISION' : 4, 
    'FIELD_TYPE' : 1, 
    'FORMULA' : 'value = $geom.area()',
    'GLOBAL' : '', 
    'INPUT' : myDirOutput+f'Locations/food_flow_locations_buffer_{city}.gpkg',
    'OUTPUT' : myDirOutput+f'Locations/food_flow_locations_buffer_{city}_area.gpkg'
    })['OUTPUT']
    
    # creating files without suitability for crops for which suitability data are unavailable (e.g. some vegetables)
    
    layers_wo_suitability=processing.run("native:addfieldtoattributestable", {
    'FIELD_LENGTH' : 10, 
    'FIELD_NAME' : 'avg_suitability', 
    'FIELD_PRECISION' : 0, 
    'FIELD_TYPE' : 1, 
    'INPUT' : myDirOutput+f'Locations/food_flow_locations_buffer_{city}_area.gpkg',
    'OUTPUT' : myDirOutput+f'Locations/buffer_{city}_agric_suitability_wo_gaez.gpkg'
    })['OUTPUT']
    
    path_buffer=myDirOutput+f'Locations/food_flow_locations_buffer_{city}_area.gpkg'

    for item in suitability_directory:
        print(item)
        filename = os.fsdecode(item)
        if filename.endswith(".gpkg"):
            suitability_buffer_intersect=processing.run("qgis:intersection", {
            'INPUT' : path_buffer,
            'INPUT_FIELDS' : '', 
            'OUTPUT' : 'TEMPORARY_OUTPUT', 
            'OVERLAY' : myDirOutput+f'GAEZ4_suitability/{item}',
            'OVERLAY_FIELDS' : ['Class'], 
            'OVERLAY_FIELDS_PREFIX' : '' 
            })['OUTPUT']

            # add field and compute class in percent
            
            suitability_percent=processing.run("qgis:advancedpythonfieldcalculator", {
            'FIELD_LENGTH' : 8, 
            'FIELD_NAME' : 'area_percent_times_classvalue', 
            'FIELD_PRECISION' : 4, 
            'FIELD_TYPE' : 1, 
            'FORMULA' : 'value = <Class>*$geom.area()/<buffer_area_m_clip>',
            'GLOBAL' : '', 
            'INPUT' : suitability_buffer_intersect,
            'OUTPUT' : 'TEMPORARY_OUTPUT'
            })['OUTPUT']
            #QgsProject.instance().addMapLayer(maize_suitability_percent)

            # summarise

            suitability_summary=processing.run("qgis:statisticsbycategories", {
            'CATEGORIES_FIELD_NAME' : ['id'], 
            'INPUT' : suitability_percent,
            'OUTPUT' : 'TEMPORARY_OUTPUT', 
            'VALUES_FIELD_NAME' : 'area_percent_times_classvalue' 
            })['OUTPUT']

            #QgsProject.instance().addMapLayer(suitability_summary)

            # add field for renaming 'sum'
            suitability_summary_field=processing.run("qgis:advancedpythonfieldcalculator", {
            'FIELD_LENGTH' : 8, 
            'FIELD_NAME' : 'avg_suitability', 
            'FIELD_PRECISION' : 4, 
            'FIELD_TYPE' : 1, 
            'FORMULA' : 'value = <sum>',
            'GLOBAL' : '', 
            'INPUT' : suitability_summary,
            'OUTPUT' : 'TEMPORARY_OUTPUT'
            })['OUTPUT']

            buffer_join_agric_suitability=processing.run("native:joinattributestable",{
            'DISCARD_NONMATCHING' : False, 
            'FIELD' : 'id', 
            'FIELDS_TO_COPY' : ['avg_suitability'], 
            'FIELD_2' : 'id', 
            'INPUT' : path_buffer,
            'INPUT_2' : suitability_summary_field,
            'METHOD' : 0, 
            'OUTPUT' : myDirOutput+f'GAEZ4_suitability/Buffer/buffer_{city}_{item}.gpkg',
            'PREFIX' : '' 
            })['OUTPUT']
        else:
            continue



# spatial units

for city in city_list:
    if city=='Tamale':
        country='Ghana'
        country_OSM='ghana'
        city_locations='spatial'
    elif city=='Bamako':
        country='Mali'
        country_OSM='mali'
        city_locations='bamako'
    elif city=='Ouagadougou':
        country='Burkina Faso'
        country_OSM='bf'
        city_locations='ouaga'
    elif city=='Bamenda':
        country='Cameroon'
        country_OSM='cameroon'
        city_locations='bamenda'
    
    for commodity_name_gen, GAEZ4_acronym in zip(food_flow_commodity_df.commodity_name_gen, food_flow_commodity_df.GAEZ4_acronym):
        if exists(myDirOutput+f'GAEZ4_suitability/Buffer/buffer_{city}_agric_suitability_{GAEZ4_acronym}.gpkg'):

            join_gaez_to_point_locations=processing.run("native:joinattributestable",{
            'DISCARD_NONMATCHING' : False, 
            'FIELD' : 'id', 
            'FIELDS_TO_COPY' : ['avg_suitability', 'spam_production_sum'], 
            'FIELD_2' : 'id', 
            'INPUT' : myDirOutput+f'Locations/food_flow_locations_{city}.gpkg',
            'INPUT_2' : myDirOutput+f'GAEZ4_suitability/Buffer/buffer_{city}_agric_suitability_{GAEZ4_acronym}.gpkg',
            'METHOD' : 0, 
            'OUTPUT' : myDirOutput+f'GAEZ4_suitability/Point/point_{city}_{commodity_name_gen}.gpkg',
            'PREFIX' : '' 
            })['OUTPUT']
            
            # national, intra-regional, border
            # the Africa national borders were extracted from a dataset containing level 0 world administrative boundaries (source: https://public.opendatasoft.com/explore/dataset/world-administrative-boundaries/information/)
            
            data_layer=myDirOutput+f'GAEZ4_suitability/Point/point_{city}_{commodity_name_gen}.gpkg'
            
            spatial_join_data_boundaries=processing.run("native:joinattributesbylocation", {
                'DISCARD_NONMATCHING' : False, 
                'INPUT' : data_layer, 
                'JOIN' : myDirInput+'Secondary_data/national_borders/Africa_Boundaries_reprojected_fix.geojson',
                'JOIN_FIELDS' : ['NAME_0'], 
                'METHOD' : 0, 
                'OUTPUT' : 'TEMPORARY_OUTPUT', 
                'PREDICATE' : [0], 
                'PREFIX' : '' 
                })['OUTPUT']
            
            data_layer_added_field=processing.run("native:addfieldtoattributestable", {
                'FIELD_LENGTH' : 20, 
                'FIELD_NAME' : 'national_origin', 
                'FIELD_PRECISION' : 0, 
                'FIELD_TYPE' : 2, 
                'INPUT' : spatial_join_data_boundaries, 
                'OUTPUT' : 'TEMPORARY_OUTPUT' 
                })['OUTPUT']
            
            # set country of origin based on overlaying country polygon
            
            select_national_sources=processing.run("qgis:selectbyattribute", {
                'FIELD' : 'NAME_0', 
                'INPUT' : data_layer_added_field, 
                'METHOD' : 0, 
                'OPERATOR' : 0, 
                'VALUE' : country
                })['OUTPUT']
            QgsProject.instance().addMapLayer(data_layer_added_field, False)
           
            features = data_layer_added_field.selectedFeatures()
            data_layer_added_field.startEditing()
            for f in features:
                f['national_origin'] = 'national'
                data_layer_added_field.updateFeature(f)
            data_layer_added_field.commitChanges()
            iface.vectorLayerTools().stopEditing(data_layer_added_field) 
            
            data_layer_added_field.removeSelection()
          
                
            select_intraregional_sources=processing.run("qgis:selectbyattribute", {
                'FIELD' : 'NAME_0', 
                'INPUT' : data_layer_added_field, 
                'METHOD' : 0, 
                'OPERATOR' : 1, 
                'VALUE' : country 
                })['OUTPUT']
            QgsProject.instance().addMapLayer(data_layer_added_field, False)
            
            
            features = data_layer_added_field.selectedFeatures()
            data_layer_added_field.startEditing()
            for f in features:
                f['national_origin'] = 'intraregional'
                data_layer_added_field.updateFeature(f)
            data_layer_added_field.commitChanges()
            iface.vectorLayerTools().stopEditing(data_layer_added_field) 
            
            data_layer_added_field.removeSelection()
        
            
            QgsProject.instance().addMapLayer(data_layer_added_field, False)
            
                        
            select_within_border_buffer=processing.run("native:selectbylocation", {            
                'INPUT' : data_layer_added_field, 
                'INTERSECT' : myDir+'/Secondary_data/national_borders/20km_buffers.gpkg', 
                'METHOD' : 0, 
                'PREDICATE' : [0] 
                })['OUTPUT']   
                
            QgsProject.instance().addMapLayer(data_layer_added_field, False)
        
            selected_features = data_layer_added_field.selectedFeatures()
            data_layer_added_field.startEditing()
            for f in selected_features:
                f['national_origin'] = 'borderline'
                data_layer_added_field.updateFeature(f)
            data_layer_added_field.commitChanges()
            iface.vectorLayerTools().stopEditing(data_layer_added_field) 
            
            data_layer_added_field.removeSelection()


            #road distance
            
            fill_field=processing.run("qgis:advancedpythonfieldcalculator", {
                'FIELD_LENGTH' : 10, 
                'FIELD_NAME' : 'prox_to_road', 
                'FIELD_PRECISION' : 3, 
                'FIELD_TYPE' : 2, 
                'FORMULA' : "value = 'none'",
                'GLOBAL' : '', 
                'INPUT' : data_layer_added_field,
                'OUTPUT' : 'TEMPORARY_OUTPUT' 
                })['OUTPUT']
            #QgsProject.instance().addMapLayer(fill_field)
            
            # primary and secondary road network were extracted from OSM datasets (source: https://download.geofabrik.de/)

            buffer_primary_roads=processing.run("native:buffer",{
                'DISSOLVE' : True, 
                'DISTANCE' : 5000, 
                'END_CAP_STYLE' : 0, 
                'INPUT' : myDir+f'/Secondary_data/road_network/primary_road_{country_OSM}.gpkg', 
                'JOIN_STYLE' : 0, 
                'MITER_LIMIT' : 2, 
                'OUTPUT' : 'TEMPORARY_OUTPUT', 
                'SEGMENTS' : 5 
                })['OUTPUT']

            buffer_secondary_roads=processing.run("native:buffer",{
                'DISSOLVE' : True, 
                'DISTANCE' : 5000, 
                'END_CAP_STYLE' : 0, 
                'INPUT' : myDir+f'/Secondary_data/road_network/secondary_road_{country_OSM}.gpkg', 
                'JOIN_STYLE' : 0, 
                'MITER_LIMIT' : 2, 
                'OUTPUT' : 'TEMPORARY_OUTPUT', 
                'SEGMENTS' : 5 
                })['OUTPUT']
                
            
            select_within_secondary=processing.run("native:selectbylocation", {            
                'INPUT' : fill_field, 
                'INTERSECT' : buffer_secondary_roads, 
                'METHOD' : 0, 
                'PREDICATE' : [0] 
                })['OUTPUT'] 
            
            QgsProject.instance().addMapLayer(fill_field, False)
            
            features = fill_field.selectedFeatures()
            fill_field.startEditing()
            for f in features:
                f['prox_to_road'] = 'secondary'
                fill_field.updateFeature(f)
            fill_field.commitChanges()
            iface.vectorLayerTools().stopEditing(fill_field) 
            
            fill_field.removeSelection()
        
            select_within_primary=processing.run("native:selectbylocation", {
                'INPUT' : fill_field, 
                'INTERSECT' : buffer_primary_roads, 
                'METHOD' : 0, 
                'PREDICATE' : [0] 
                })['OUTPUT']
        
            QgsProject.instance().addMapLayer(fill_field, False)
            
            features = fill_field.selectedFeatures()
            fill_field.startEditing()
            for f in features:
                f['prox_to_road'] = 'primary'
                fill_field.updateFeature(f)
            fill_field.commitChanges()
            iface.vectorLayerTools().stopEditing(fill_field) 
            
            fill_field.removeSelection()
            
            
            processing.run("native:savefeatures", { 
            'DATASOURCE_OPTIONS' : '', 
            'INPUT' : fill_field, 
            'LAYER_NAME' : NULL, 
            'LAYER_OPTIONS' : '', 
            'OUTPUT' : myDirOutput+f'Locations/Joins/joins_{city}_{commodity_name_gen}.gpkg'
            })['OUTPUT']
            
            processing.run("native:savefeatures", { 
            'DATASOURCE_OPTIONS' : '', 
            'INPUT' : fill_field, 
            'LAYER_NAME' : NULL, 
            'LAYER_OPTIONS' : '', 
            'OUTPUT' : myDirOutput+f'Locations/Joins/joins_{city}_{commodity_name_gen}.csv'
            })['OUTPUT']

        else:
            continue


## Connect with actual food flow data

for city in city_list:
    for commodity_name_gen, GAEZ4_acronym in zip(food_flow_commodity_df.commodity_name_gen, food_flow_commodity_df.GAEZ4_acronym):
        sql = f"SELECT source_name, source, geom, mean_unit_quantity, daily_quantity, total_quantity, percent_of_total_quantity, no_connections, total_number_connections, percent_of_total_connections, node_size, distance_to_source_km, commodity_name_gen, commodity_category, season, year, population, city from dataset_nodelevel_incoming WHERE commodity_name_gen='{commodity_name_gen}' AND city='{city}'"
        df = geopandas.read_postgis(sql, con)
        if df.empty:
            print(f"{commodity_name_gen}_{city}"+"empty")
            continue
        else:
            layer = QgsVectorLayer(df.to_json(),f"{commodity_name_gen}_{city}","ogr")

            layer_reproject=processing.run("native:reprojectlayer", {
                'INPUT': layer,
                'OPERATION': '+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad +step +proj=sinu +lon_0=15 +x_0=0 +y_0=0 +ellps=WGS84',
                'TARGET_CRS': QgsCoordinateReferenceSystem('ESRI:102011'),
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                })['OUTPUT']
                    
                
            print(f"{commodity_name_gen}{city}")
            
            join_location_charact_to_data=processing.run("native:joinattributestable",{
            'DISCARD_NONMATCHING' : False, 
            'FIELD' : 'source', 
            'FIELDS_TO_COPY' : ['avg_suitability', 'spam_production_sum', 'NAME_0', 'national_origin', 'prox_to_road'], 
            'FIELD_2' : 'id', 
            'INPUT' : layer_reproject,
            'INPUT_2' : f'C:/Users/hanna/Documents/papers/UBC/Inputs/model/Data_updated/intermediary_data/gaez_spam_rd_orig/buffer_g_s_rd_orig_{city}_{GAEZ4_acronym}.gpkg',
            'METHOD' : 0, 
            'OUTPUT' : myDirOutput+f'Flow_data/{city}_{commodity_name_gen}.gpkg',
            'PREFIX' : ''
            })['OUTPUT']
            
            processing.run("native:savefeatures", { 
            'DATASOURCE_OPTIONS' : '', 
            'INPUT' : join_location_charact_to_data, 
            'LAYER_NAME' : f'{commodity_name_gen}_{city}', 
            'LAYER_OPTIONS' : '', 
            'OUTPUT' : myDirOutput+f'Flow_data/{city}_{commodity_name_gen}.csv'
            })['OUTPUT']

