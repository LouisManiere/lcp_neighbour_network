# Author : Louis Manière HiSoMA CNRS UM 5189
# creation date : 09/02/2021
# PyQGIS 3.14
# processing GRASS and plugins ETL_LOAD

# create neighbour network from an initial network.
# neighbour are define by distance threshold on the network and not by buffer

# libraries
from PyQt5.QtCore import QVariant
import os
from qgis.core import *
import processing

###
# distance threshold variable (in meters)
distance_threshold = 40000
###

# input output variables
# working folder
wd_path = r"C:\Users\l.maniere\Documents\SIG\Reseaux\20210318_medieval_network"

# site layer
path_sites = wd_path+r"\input\sites\20210325_network_sites.shp"

# network layer
path_network = wd_path+r"\postprocess_medieval_network.shp"

# intermediate data
# network
path_output_network = wd_path+r"\neighbours_networks\intermediate_data\postprocess_medieval_network_neighbour_raw_2.shp"

# network clean
path_output_network_null = wd_path+r"\neighbours_networks\intermediate_data\postprocess_medieval_network_neighbour_null_2.shp"

# network break intersection
path_output_network_break = wd_path+r"\neighbours_networks\intermediate_data\postprocess_medieval_network_neighbour_null_break_2.shp"

# output
# output network break intersection clean
path_output_network_clean = wd_path+r"\neighbours_networks\output\postprocess_medieval_network_neighbour_2.shp"

# import files
sites=iface.addVectorLayer(path_sites,"","ogr")
network = iface.addVectorLayer(path_network,"","ogr")

# extract max id value
idx = sites.fields().indexFromName('id')
max_id = sites.maximumValue(idx)

# select by ID iteration
for i in range(0, max_id):
    i=i+1
#    sites.removeSelection()
    point_select = processing.run("qgis:extractbyattribute", 
        {'INPUT':sites,
        'FIELD': 'id',
        'OPERATOR': 0,
        'VALUE': i,
        'OUTPUT': 'memory:'})

    # extract x an y coordinate
    for f in point_select['OUTPUT'].getFeatures():
      geom = f.geometry()
      x_coord = geom.asPoint().x()
      y_coord = geom.asPoint().y()

    # compute LCP service area with threshold distance
    service = processing.run("qgis:serviceareafrompoint",{
        'DEFAULT_DIRECTION' : 2,
        'DEFAULT_SPEED' : 3.9,
        'DIRECTION_FIELD' : None,
        'INCLUDE_BOUNDS' : False,
        'INPUT' : network, 
        'OUTPUT_LINES' : 'memory:', 
        'SPEED_FIELD' : None, 
        'START_POINT' : str(x_coord)+','+str(y_coord)+' [EPSG:32636]', 
        'STRATEGY' : 0, 
        'TOLERANCE' : 0, 
        'TRAVEL_COST' : distance_threshold, 
        'VALUE_BACKWARD' : '', 
        'VALUE_BOTH' : '', 
        'VALUE_FORWARD' : '' })

    split = processing.run("qgis:splitwithlines",{
    'INPUT' : service['OUTPUT_LINES'], 
    'LINES' : service['OUTPUT_LINES'], 
    'OUTPUT' : 'memory:' })

    # buffer along line service area cleaned
    buffer = processing.run("qgis:buffer",{
        'INPUT': split['OUTPUT'],
        'DISSOLVE' : False,
        'DISTANCE' : 10,
        'END_CAP_STYLE' : 0, 
        'JOIN_STYLE' : 0, 
        'MITER_LIMIT' : 2, 
        'OUTPUT' : 'memory:', 
        'SEGMENTS' : 5 })

    extract_sites = processing.run('qgis:extractbylocation',{
    'INPUT' : sites, 
    'INTERSECT' : buffer['OUTPUT'], 
    'OUTPUT' : 'memory:', 
    'PREDICATE' : [0] })

    # shortest paths
    lcp = processing.run('qgis:shortestpathpointtolayer', {
        'DEFAULT_DIRECTION' : 2, 
        'DEFAULT_SPEED' : 3.9, 
        'DIRECTION_FIELD' : None, 
        'END_POINTS' : extract_sites['OUTPUT'], 
        'INPUT' : network, 
        'OUTPUT' : 'memory:', 
        'SPEED_FIELD' : None, 
        'START_POINT' : str(x_coord)+','+str(y_coord)+' [EPSG:32636]', 
        'STRATEGY' : 0, 
        'TOLERANCE' : 0, 
        'VALUE_BACKWARD' : '', 
        'VALUE_BOTH' : '', 
        'VALUE_FORWARD' : '' })

    # output
    # write first iteration
    if i==1:
        QgsVectorFileWriter.writeAsVectorFormat(
            lcp['OUTPUT'],
            path_output_network,"utf-8",
            lcp['OUTPUT'].crs(),
            "ESRI Shapefile")
    else:
        processing.run("etl_load:appendfeaturestolayer", {
        'ACTION_ON_DUPLICATE' : 0, 
        'SOURCE_FIELD' : None, 
        'SOURCE_LAYER' : lcp['OUTPUT'], 
        'TARGET_FIELD' : None,
        'TARGET_LAYER' : path_output_network})
    

# delete feature with null geometry
output_network_null = processing.run("qgis:removenullgeometries", { 
    'INPUT' : path_output_network, 
    'OUTPUT' : path_output_network_null})
output_network_null = QgsVectorLayer(output_network_null['OUTPUT'], "output_network_null", "ogr")

# delete index field
field_index_to_delete = []
# Fieldnames to delete list ['column1','column2']
fieldnames = set(['index'])
# iterate through fields to get their idex if their are in Fieldnames to delete
for field in output_network_null.fields():
    if field.name() in fieldnames:
      field_index_to_delete.append(output_network_null.fields().indexFromName(field.name()))

# Delete the fields in the attribute table through their corresponding index in the list.
output_network_null.dataProvider().deleteAttributes(field_index_to_delete)
output_network_null.updateFields()

# break line to intersections
service_clean = processing.run("grass7:v.clean",{
    '-b' : False, 
    '-c' : False, 
    'GRASS_MIN_AREA_PARAMETER' : 0.0001, 
    'GRASS_OUTPUT_TYPE_PARAMETER' : 0, 
    'GRASS_REGION_PARAMETER' : None, 
    'GRASS_SNAP_TOLERANCE_PARAMETER' : -1, 
    'GRASS_VECTOR_DSCO' : '', 
    'GRASS_VECTOR_EXPORT_NOCAT' : False, 
    'GRASS_VECTOR_LCO' : '', 
    'error' : 'memory:', 
    'input' : path_output_network_null, 
    'output' : path_output_network_break, 
    'threshold' : '', 
    'tool' : [0], 
    'type' : [0,1,2,3,4,5,6] })

# remove duplicate geometry
processing.run("qgis:deleteduplicategeometries",{
    'INPUT' : path_output_network_break, 
    'OUTPUT' : path_output_network_clean })

