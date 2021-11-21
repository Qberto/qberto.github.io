import arcpy
import saspy
from saspy import autocfg
import time

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [SASCorr]


class SASCorr(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Spearman Rank-Order Correlation"
        self.description = "Compute the non-parametric Spearman rank-order measues of association."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        
        param0 = arcpy.Parameter(displayName="Input Features",
                                 name="in_features",
                                 datatype="GPFeatureLayer",
                                 parameterType="Required",
                                 direction="Input")

        param1 = arcpy.Parameter(displayName="Input Fields",
                            name = "Input_Field",
                            datatype = "Field",
                            parameterType = "Required",
                            multiValue = True,
                            direction = "Input")

        param1.filter.list = ['Short','Long','Float','Double']
        param1.parameterDependencies = ["in_features"]
        
        param2 = arcpy.Parameter(displayName="Output Table",
                            name = "Output_Table",
                            datatype = "DETable",
                            parameterType = "Required",
                            direction = "Output")
        
        params = [param0, param1, param2]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        inputFC = parameters[0].valueAsText
        varNames = parameters[1].valueAsText.upper()
        varNames = varNames.replace(';', ' ')
        outputTable = parameters[2].valueAsText
        
        ##### Create a unique SAS file name #####
        uniqueFilename = 'temp_' + time.strftime("%Y%m%d_%H%M%S")
        sasFileName = 'sasuser.' + uniqueFilename
        sasOutFileName = 'sasuser.' + 'out_' + uniqueFilename

        ##### Convert input feature layer to SAS table ####                
        arcpy.conversion.TableToSAS(inputFC, 
                                    sasFileName, 
                                    replace_sas_dataset="OVERWRITE", 
                                    use_domain_and_subtype_description="USE_DOMAIN")       

        ##### Create the SAS CORR procedure #####
        sasSyntax = f"""options linesize=80; 
                        proc corr data={sasFileName} OUTS={sasOutFileName} pearson spearman kendall hoeffding; 
                        var {varNames}; 
                        run;"""     

        ##### Create automatic SAS config file #####
        scratchCFG = f"{arcpy.CreateUniqueName('sasConfig', arcpy.env.scratchFolder)}.txt"
        autocfg.main(cfgfile = scratchCFG)

        ##### Create a SAS session and submit the SAS CORR procedure #####
        sas = saspy.SASsession(results='TEXT', cfgfile = scratchCFG)
        sas_result = sas.submit(sasSyntax) 
        sas.endsas()

        ##### Convert output SAS CORR table to output table ####  
        arcpy.conversion.SASToTable(sasOutFileName, outputTable)
        
        ##### Retrieve the SAS log files to add as geoprocessing messages ####  
        log_lines = sas_result.get('LOG').split('\n')
        for line in log_lines:
            arcpy.AddMessage(line)
            
        lst_lines = sas_result.get('LST').split('\n')
        for line in lst_lines:
            arcpy.AddMessage(line)
        
        return
