# coding=UTF-8

from natcap.invest.ui import model, inputs
from natcap.invest.routing import delineateit, routedem


class Delineateit(model.InVESTModel):
    def __init__(self):
        model.InVESTModel.__init__(
            self,
            label='DelineateIT: Watershed Delineation',
            target=delineateit.execute,
            validator=delineateit.validate,
            localdoc='../documentation/delineateit.html')

        self.dem_uri = inputs.File(
            args_key='dem_uri',
            helptext=(
                "A GDAL-supported raster file with an elevation value "
                "for each cell.  Make sure the DEM is corrected by "
                "filling in sinks, and if necessary burning "
                "hydrographic features into the elevation model "
                "(recommended when unusual streams are observed.) See "
                "the 'Working with the DEM' section of the InVEST "
                "User's Guide for more information."),
            label='Digital Elevation Model (Raster)',
            validator=self.validator)
        self.add_input(self.dem_uri)
        self.outlet_shapefile_uri = inputs.File(
            args_key='outlet_shapefile_uri',
            helptext=(
                "This is a layer of points representing outlet points "
                "that the watersheds should be built around."),
            label='Outlet Points (Vector)',
            validator=self.validator)
        self.add_input(self.outlet_shapefile_uri)
        self.flow_threshold = inputs.Text(
            args_key='flow_threshold',
            helptext=(
                "The number of upstream cells that must flow into a "
                "cell before it's considered part of a stream such "
                "that retention stops and the remaining export is "
                "exported to the stream.  Used to define streams from "
                "the DEM."),
            label='Threshold Flow Accumulation',
            validator=self.validator)
        self.add_input(self.flow_threshold)
        self.snap_distance = inputs.Text(
            args_key='snap_distance',
            label='Pixel Distance to Snap Outlet Points',
            validator=self.validator)
        self.add_input(self.snap_distance)

        # Set interactivity, requirement as input sufficiency changes

    def assemble_args(self):
        args = {
            self.workspace.args_key: self.workspace.value(),
            self.suffix.args_key: self.suffix.value(),
            self.dem_uri.args_key: self.dem_uri.value(),
            self.outlet_shapefile_uri.args_key: (
                self.outlet_shapefile_uri.value()),
            self.flow_threshold.args_key: self.flow_threshold.value(),
            self.snap_distance.args_key: self.snap_distance.value(),
        }

        return args


class RouteDEM(model.InVESTModel):
    def __init__(self):
        model.InVESTModel.__init__(
            self,
            label='RouteDEM',
            target=routedem.execute,
            validator=routedem.validate,
            localdoc='../documentation/routedem.html')

        self.dem_path = inputs.File(
            args_key='dem_path',
            helptext=(
                "A GDAL-supported raster file containing a base "
                "Digital Elevation Model to execute the routing "
                "functionality across."),
            label='Digital Elevation Model (Raster)',
            validator=self.validator)
        self.add_input(self.dem_path)
        self.calculate_slope = inputs.Checkbox(
            args_key='calculate_slope',
            helptext='If selected, calculates slope raster.',
            label='Calculate Slope')
        self.add_input(self.calculate_slope)
        self.calculate_flow_accumulation = inputs.Checkbox(
            args_key='calculate_flow_accumulation',
            helptext='Select to calculate flow accumulation.',
            label='Calculate Flow Accumulation')
        self.add_input(self.calculate_flow_accumulation)
        self.calculate_stream_threshold = inputs.Checkbox(
            args_key='calculate_stream_threshold',
            helptext='Select to calculate a stream threshold to flow accumulation.',
            interactive=False,
            label='Calculate Stream Thresholds')
        self.add_input(self.calculate_stream_threshold)
        self.threshold_flow_accumulation = inputs.Text(
            args_key='threshold_flow_accumulation',
            helptext=(
                "The number of upstream cells that must flow into a "
                "cell before it's classified as a stream."),
            interactive=False,
            label='Threshold Flow Accumulation Limit',
            validator=self.validator)
        self.add_input(self.threshold_flow_accumulation)
        self.calculate_downstream_distance = inputs.Checkbox(
            args_key='calculate_downstream_distance',
            helptext=(
                "If selected, creates a downstream distance raster "
                "based on the thresholded flow accumulation stream "
                "classification."),
            interactive=False,
            label='Calculate Distance to stream')
        self.add_input(self.calculate_downstream_distance)

        # Set interactivity, requirement as input sufficiency changes
        self.calculate_flow_accumulation.sufficiency_changed.connect(
            self.calculate_stream_threshold.set_interactive)
        self.calculate_stream_threshold.sufficiency_changed.connect(
            self.threshold_flow_accumulation.set_interactive)
        self.calculate_stream_threshold.sufficiency_changed.connect(
            self.calculate_downstream_distance.set_interactive)

    def assemble_args(self):
        args = {
            self.workspace.args_key: self.workspace.value(),
            self.suffix.args_key: self.suffix.value(),
            self.dem_path.args_key: self.dem_path.value(),
            self.calculate_slope.args_key: self.calculate_slope.value(),
            self.calculate_flow_accumulation.args_key:
                self.calculate_flow_accumulation.value(),
            self.calculate_stream_threshold.args_key:
                self.calculate_stream_threshold.value(),
            self.threshold_flow_accumulation.args_key:
                self.threshold_flow_accumulation.value(),
            self.calculate_downstream_distance.args_key:
                self.calculate_downstream_distance.value(),
        }
        return args
