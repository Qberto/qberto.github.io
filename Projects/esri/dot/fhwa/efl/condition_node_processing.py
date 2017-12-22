# #############
"""
Tool Name:  Condition Event Node Post-Processing
Source Name: condition_node_processing.py
Version: ArcGIS 10.5
Author: ESRI

This tool identifies records from the Condition Event Collection Node feature classes, by LEC_NODE_TYPE attribute
and creates linear events along the closest matching routes from the ROUTES feature class. 

The intent of this tool is to provide capabilities for field collectors to record linear events that span a distance 
while still being able to collect other point events along the linear event. 
 
"""

### PSEUDOCODE ###

# GOAL: We need to have five condition feature class routes start with an event condition of excellent, then be altered
# based on points that designate the endpoints of condition changes.

# INGREDIENTS: We will have the following ingredients to cook with:
# 1. A feature class with our routes that will be the target output.
# 2. Five feature classes for each condition type. The feature classes will contain points corresponding

# Rough draft:
# We need a copy of the routes layer that will be split by points. The output from the split will be used to intersect
# with the original routes to create events. The tricky part is handling the original condition at default of excellent.


### PROCEDURE STEPS ###

# STEP 1: Create copy of our routes and condition points so we can operate on them for the splitting by point step.

# STEP 2: Perform Select-by-Location using the input points on the routes copy - the idea is to select only the lines that
# were evaluated. Export this selection to disk as "Evaluated_Routes".

# STEP 3: Use Split Line by Point to fracture the Routes into lines that are determined by the points entered. Make sure
# to enter a search area.

# STEP 4: Transfer the condition from the points to the line segments by using spatial join

# STEP 5: Correct for the first line segment by selecting it and changing the condition rating to "Excellent"


#TODO 01 - If line is digitized in the opposite direction, Step 5 would not be correct.

# Possible Solution:
# - Line to Points. What if we generate line segments from our point trail, and add a sequence attribute (i.e. Point 01, Point 02, etc.)
# - Option, convert point to polyline and get mid-point to transfer the attribute from the event to the route line.

# - Read from event editor tracking or object ID to find the start point for a specific route (to know which line segment is the first one).

# - Join route to event points to get route ID and then use Route ID as grouping mechanism for point to polyline.


#TODO 02 - Add artificial start and end points with excellent condition

#


### EXECUTION ###

# Import needed modules
import arcpy
import os
import datetime


def create_cond_events(workspace,
                       condition,
                       condlec_nodes_fc,
                       condition_field,
                       routes_fc,
                       routes_id_field,
                       point_search_meters,
                       clean_up_temp_files):

    """
    
    :param workspace: 
    :param condition: 
    :param condlec_nodes_fc: 
    :param condition_field: 
    :param routes_fc: 
    :param routes_id_field: 
    :param point_search_meters: 
    :param clean_up_temp_files: 
    :return: 
    """

    # STEP 0: Set-up

    # Take the user parameter for search radius and append linear unit measurement for string
    search_distance = "{0} Meters".format(str(point_search_meters))

    # Create workspace file geodatabase
    timestamp = '{:%Y%m%d_%H%M}'.format(datetime.datetime.now())
    workspace_gdb_name = "ConditionPostProcessing_{0}".format(timestamp)

    arcpy.AddMessage("Creating workspace file geodatabase '{0}'...".format(workspace_gdb_name))
    workspace_gdb = arcpy.CreateFileGDB_management(workspace, workspace_gdb_name).getOutput(0)

    os.chdir(workspace)
    if os.path.isfile(os.path.join(workspace, "work_routes_lyr")):
        arcpy.AddMessage("Removing previously-existing layers...")
        os.remove(os.path.join(workspace, "work_routes_lyr"))

    work_event_table = os.path.join(workspace_gdb, "work_cond_events_table")

    out_condition_event_fc = os.path.join(workspace_gdb, "out_{0}_events".format(condition))

    # STEP 1: Create copy of our routes and condition points so we can operate on them for the splitting by point step.
    arcpy.AddMessage("Copying data to workspace...")
    work_nodes_fc = arcpy.FeatureClassToFeatureClass_conversion(condlec_nodes_fc, workspace_gdb,
                                                                "work_condition_nodes").getOutput(0)

    work_routes_fc = arcpy.FeatureClassToFeatureClass_conversion(routes_fc, workspace_gdb,
                                                                "work_routes").getOutput(0)

    work_routes_lyr = arcpy.MakeFeatureLayer_management(routes_fc, "work_routes_lyr").getOutput(0)

    # STEP 2: Perform Select-by-Location using the input points on the routes copy - the idea is to select only the
    # lines that were evaluated. Export this selection to disk as "Evaluated_Routes".
    arcpy.AddMessage("Finding evaluated roads...")
    arcpy.SelectLayerByLocation_management(work_routes_lyr, "INTERSECT", work_nodes_fc, search_distance)
    work_routes_evaluated = arcpy.CopyFeatures_management(work_routes_lyr,
                                                          os.path.join(workspace_gdb,
                                                                       "work_evaluated_routes")).getOutput(0)

    # STEP 3: Use Split Line by Point to fracture the Routes into lines that are determined by the points entered.
    # Make sure to enter a search area.
    arcpy.AddMessage("Creating condition segments...")
    #TODO - Use the near tool to find the nearest point on the line instead of a search radius for "SplitLineAtPoint"
    work_route_evaluated_segments = arcpy.SplitLineAtPoint_management(in_features=work_routes_evaluated,
                                                                      point_features=work_nodes_fc,
                                                                      out_feature_class=os.path.join(workspace_gdb,
                                                                                                     "work_evaluated_route_segments"),
                                                                      search_radius=search_distance).getOutput(0)

    # STEP 4: Transfer the condition from the points to the line segments by using spatial join
    arcpy.AddMessage("Transferring condition attributes to condition route segments...")
    arcpy.SpatialJoin_analysis(
        target_features=work_route_evaluated_segments,
        join_features=work_nodes_fc,
        out_feature_class=os.path.join(workspace_gdb, "work_evaluated_route_segment_conditions"),
        join_operation="JOIN_ONE_TO_ONE", join_type="KEEP_ALL",
        match_option="INTERSECT", search_radius=search_distance, distance_field_name="closest_node_distance")

    work_evaluated_route_segment_conditions = os.path.join(workspace_gdb, "work_evaluated_route_segment_conditions")

    # STEP 5: Correct for the first line segment by selecting it and changing the condition rating to "Excellent"
    arcpy.AddMessage("Adding default start segment condition...")
    with arcpy.da.UpdateCursor(work_evaluated_route_segment_conditions, condition_field) as cursor:
        for row in cursor:
            row[0] = "Excellent"
            cursor.updateRow(row)
            break

    # STEP 6: Create event table using condition segments
    arcpy.LocateFeaturesAlongRoutes_lr(in_features=work_evaluated_route_segment_conditions,
                                       in_routes=work_routes_evaluated,
                                       route_id_field=routes_id_field,
                                       out_table=work_event_table, radius_or_tolerance=search_distance,
                                       out_event_properties="RID LINE FMEAS TMEAS",
                                       route_locations="FIRST",
                                       distance_field="DISTANCE",
                                       zero_length_events="ZERO",
                                       in_fields="FIELDS", m_direction_offsetting="M_DIRECTON")

    # GP Tool: Table conversion of edited events to a feature layer.
    work_condition_events_lyr = arcpy.MakeRouteEventLayer_lr(in_routes=routes_fc,
                                                             route_id_field=routes_id_field,
                                                             in_table=work_event_table,
                                                             in_event_properties="rid LINE fmeas tmeas",
                                                             out_layer="work_condition_events_lyr").getOutput(0)

    # GP Tool: Copy feature layer to disk as feature class.
    arcpy.CopyFeatures_management(in_features=work_condition_events_lyr,
                                  out_feature_class=out_condition_event_fc)

    # Optional clean-up of temp data.
    if clean_up_temp_files:
        arcpy.AddMessage("Cleaning up temporary content...")
        # print("Cleaning up temporary content...")

        content_to_delete = [work_evaluated_route_segment_conditions,
                             work_nodes_fc,
                             work_routes_lyr,
                             work_condition_events_lyr,
                             work_event_table,
                             work_route_evaluated_segments,
                             work_routes_evaluated,
                             work_routes_fc]

        for item in content_to_delete:
            arcpy.Delete_management(item)

        arcpy.AddMessage("Temp files cleaned up.")
        # print("Temp files cleaned up.")


def main():

    # Prod GP Tool Vars
    workspace = arcpy.GetParameterAsText(0)
    condlec_nodes_fc = arcpy.GetParameterAsText(1)
    condition_field = arcpy.GetParameterAsText(2)
    routes_fc = arcpy.GetParameterAsText(3)
    routes_id_field = arcpy.GetParameterAsText(4)
    point_search_meters = arcpy.GetParameterAsText(5)
    clean_up_temp_files = arcpy.GetParameter(6)

    arcpy.AddMessage("Starting Condition Event post-processing...")
    # print("Starting LEC post-processing...")

    condition = "longcracking"

    create_cond_events(workspace,
                       condition,
                       condlec_nodes_fc,
                       condition_field,
                       routes_fc,
                       routes_id_field,
                       point_search_meters,
                       clean_up_temp_files)

    arcpy.AddMessage("Condition Event post-processing completed.")
    # print("LEC post-processing completed.")


if __name__ == "__main__":
    main()
