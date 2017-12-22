# #############
"""
Tool Name:  Linear Event Node Post-Processing
Source Name: lec_node_processing.py
Version: ArcGIS 10.5
Author: ESRI

This tool identifies records from the Linear Event Collection Node feature class, LEC, by LEC_NODE_TYPE attribute
and creates linear events along the closest matching routes from the ROUTES feature class. 

The intent of this tool is to provide capabilities for field collectors to record linear events that span a distance 
while still being able to collect other point events along the linear event. 
 
"""

### PSEUDOCODE ###

# GOAL: We need to read each record in the input 'LEC' feature class, determine pairs of records as designated
# by a start and end value in the NODE_TYPE attribute, and create a linear event that is attached to the nearest
# road feature.

# CONSIDERATIONS: We need to be careful with overlapping linear events. Either the user needs to designate an event ID
# or the tool needs to be smart enough to understand how to pair events based on collection logic.

# STEP 1: Confirm that the routes we are creating events for are Routes in a linear referencing system

# STEP 2: Iterate on all LEC_node records to do the following:

#   a. Identify start and end point connections by event ID

#   b. Convert each connection to a polyline

# STEP 3: Run "Locate Features Along Routes" GP tool to create events table

# STEP 4: Run "Make Route Event Layer" GP tool to create linear events layer

# STEP 5: Copy the temporary linear events layer to disk as a feature class


### EXECUTION ###

# Import needed modules
import arcpy
import os


def convert_routes_to_lr(routes_fc,
                         routes_id_field,
                         out_fc):
    arcpy.CreateRoutes_lr(in_line_features=routes_fc, route_id_field=routes_id_field,
                          out_feature_class=out_fc,
                          measure_source="LENGTH", from_measure_field="", to_measure_field="",
                          coordinate_priority="UPPER_LEFT", measure_factor="1", measure_offset="0",
                          ignore_gaps="IGNORE", build_index="INDEX")
    return out_fc


def convert_fs_to_fc(fs_url, out_fc):
    pass


def convert_lec_nodes_to_line_events(workspace_gdb,
                                     lec_nodes_fc,
                                     lec_fault_id_field,
                                     routes_fc,
                                     routes_id_field,
                                     snapping_tolerance_meters,
                                     clean_up_temp_files=False,
                                     ):

    # Naming file variables
    temp_lines_fc = os.path.join(workspace_gdb, "temp_ConvertedLines")
    temp_events_table = os.path.join(workspace_gdb, "temp_LocatedAlongRoute")
    temp_events_lyr_name = "LEC_events_lyr"
    output_fc = os.path.join(workspace_gdb, "LEC_LinearEvents")

    # Snapping tolerance variable since GP tool accepts string with distance format
    snapping_tolerance = "{0} Meters".format(str(snapping_tolerance_meters))

    # GP Tool: LEC points to line, using a fault ID field to allow multiple edits to be processed
    arcpy.PointsToLine_management(Input_Features=lec_nodes_fc,
                                  Output_Feature_Class=temp_lines_fc,
                                  Line_Field=lec_fault_id_field, Sort_Field="OBJECTID", Close_Line="NO_CLOSE")

    # GP Tool: Locate features along route using lines and routes and write to a table.
    arcpy.LocateFeaturesAlongRoutes_lr(in_features=temp_lines_fc,
                                       in_routes=routes_fc,
                                       route_id_field=routes_id_field,
                                       radius_or_tolerance=snapping_tolerance,
                                       out_table=temp_events_table,
                                       out_event_properties="RID LINE FMEAS TMEAS",
                                       route_locations="FIRST",
                                       distance_field="DISTANCE",
                                       zero_length_events="ZERO",
                                       in_fields="FIELDS", m_direction_offsetting="M_DIRECTON")

    # GP Tool: Table conversion of edited events to a feature layer.
    event_layer = arcpy.MakeRouteEventLayer_lr(in_routes=routes_fc,
                                               route_id_field=routes_id_field,
                                               in_table=temp_events_table,
                                               in_event_properties="rid LINE fmeas tmeas",
                                               out_layer=temp_events_lyr_name,
                                               offset_field="",
                                               add_error_field="NO_ERROR_FIELD",
                                               add_angle_field="NO_ANGLE_FIELD",
                                               angle_type="NORMAL",
                                               complement_angle="ANGLE",
                                               offset_direction="LEFT",
                                               point_event_type="POINT").getOutput(0)

    # GP Tool: Copy feature layer to disk as feature class.
    arcpy.CopyFeatures_management(in_features=event_layer,
                                  out_feature_class=output_fc)

    # Optional clean-up of temp data.
    if clean_up_temp_files:
        arcpy.AddMessage("Cleaning up temporary content...")
        # print("Cleaning up temporary content...")

        content_to_delete = [temp_lines_fc, temp_events_table]

        for item in content_to_delete:
            arcpy.Delete_management(item)

        arcpy.AddMessage("Temp files cleaned up.")
        # print("Temp files cleaned up.")


def main():

    # Prod GP Tool Vars
    workspace_gdb = arcpy.GetParameterAsText(0)
    lec_nodes_fc = arcpy.GetParameterAsText(1)
    lec_fault_id_field = arcpy.GetParameterAsText(2)
    routes_fc = arcpy.GetParameterAsText(3)
    routes_id_field = arcpy.GetParameterAsText(4)
    snapping_tolerance_meters = arcpy.GetParameterAsText(5)
    clean_up_temp_files = arcpy.GetParameter(6)

    arcpy.AddMessage("Starting LEC post-processing...")
    # print("Starting LEC post-processing...")

    convert_lec_nodes_to_line_events(workspace_gdb,
                                     lec_nodes_fc,
                                     lec_fault_id_field,
                                     routes_fc,
                                     routes_id_field,
                                     snapping_tolerance_meters,
                                     clean_up_temp_files)

    arcpy.AddMessage("LEC post-processing completed.")
    # print("LEC post-processing completed.")


if __name__ == "__main__":
    main()
