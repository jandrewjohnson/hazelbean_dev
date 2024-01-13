# coding=UTF-8

from natcap.invest.ui import model, inputs
import natcap.invest.wave_energy.wave_energy


class WaveEnergy(model.InVESTModel):
    def __init__(self):
        model.InVESTModel.__init__(
            self,
            label='Wave Energy',
            target=natcap.invest.wave_energy.wave_energy.execute,
            validator=natcap.invest.wave_energy.wave_energy.validate,
            localdoc='../documentation/wave_energy.html')

        self.results_suffix = inputs.Text(
            args_key='suffix',
            helptext=(
                'A string that will be added to the end of the output file '
                'paths.'),
            label='Results Suffix (Optional)',
            validator=self.validator)
        self.add_input(self.results_suffix)
        self.wave_base_data = inputs.Folder(
            args_key='wave_base_data_uri',
            helptext=(
                'Select the folder that has the packaged Wave Energy '
                'Data.'),
            label='Wave Base Data Folder',
            validator=self.validator)
        self.add_input(self.wave_base_data)
        self.analysis_area = inputs.Dropdown(
            args_key='analysis_area_uri',
            helptext=(
                "A list of analysis areas for which the model can "
                "currently be run.  All the wave energy data needed "
                "for these areas are pre-packaged in the WaveData "
                "folder."),
            label='Analysis Area',
            options=(
                'West Coast of North America and Hawaii',
                'East Coast of North America and Puerto Rico',
                'North Sea 4 meter resolution',
                'North Sea 10 meter resolution',
                'Australia',
                'Global'))
        self.add_input(self.analysis_area)
        self.aoi = inputs.File(
            args_key='aoi_uri',
            helptext=(
                "An OGR-supported vector file containing a single "
                "polygon representing the area of interest.  This "
                "input is required for computing valuation and is "
                "recommended for biophysical runs as well.  The AOI "
                "should be projected in linear units of meters."),
            label='Area of Interest (Vector)',
            validator=self.validator)
        self.add_input(self.aoi)
        self.machine_perf_table = inputs.File(
            args_key='machine_perf_uri',
            helptext=(
                "A CSV Table that has the performance of a particular "
                "wave energy machine at certain sea state conditions."),
            label='Machine Performance Table (CSV)',
            validator=self.validator)
        self.add_input(self.machine_perf_table)
        self.machine_param_table = inputs.File(
            args_key='machine_param_uri',
            helptext=(
                "A CSV Table that has parameter values for a wave "
                "energy machine.  This includes information on the "
                "maximum capacity of the device and the upper limits "
                "for wave height and period."),
            label='Machine Parameter Table (CSV)',
            validator=self.validator)
        self.add_input(self.machine_param_table)
        self.dem = inputs.File(
            args_key='dem_uri',
            helptext=(
                "A GDAL-supported raster file containing a digital "
                "elevation model dataset that has elevation values in "
                "meters.  Used to get the cable distance for wave "
                "energy transmission."),
            label='Global Digital Elevation Model (Raster)',
            validator=self.validator)
        self.add_input(self.dem)
        self.valuation_container = inputs.Container(
            args_key='valuation_container',
            expandable=True,
            expanded=False,
            label='Valuation')
        self.add_input(self.valuation_container)
        self.land_grid_points = inputs.File(
            args_key='land_gridPts_uri',
            helptext=(
                "A CSV Table that has the landing points and grid "
                "points locations for computing cable distances."),
            label='Grid Connection Points File (CSV)',
            validator=self.validator)
        self.valuation_container.add_input(self.land_grid_points)
        self.machine_econ_table = inputs.File(
            args_key='machine_econ_uri',
            helptext=(
                "A CSV Table that has the economic parameters for the "
                "wave energy machine."),
            label='Machine Economic Table (CSV)',
            validator=self.validator)
        self.valuation_container.add_input(self.machine_econ_table)
        self.number_of_machines = inputs.Text(
            args_key='number_of_machines',
            helptext=(
                "An integer for how many wave energy machines will be "
                "in the wave farm."),
            label='Number of Machines',
            validator=self.validator)
        self.valuation_container.add_input(self.number_of_machines)

    def assemble_args(self):
        args = {
            self.workspace.args_key: self.workspace.value(),
            self.suffix.args_key: self.suffix.value(),
            self.wave_base_data.args_key: self.wave_base_data.value(),
            self.analysis_area.args_key: self.analysis_area.value(),
            self.machine_perf_table.args_key: self.machine_perf_table.value(),
            self.machine_param_table.args_key: self.machine_param_table.value(),
            self.dem.args_key: self.dem.value(),
            self.valuation_container.args_key: self.valuation_container.value(),
        }
        if self.results_suffix.value():
            args[self.results_suffix.args_key] = self.results_suffix.value()
        if self.aoi.value():
            args[self.aoi.args_key] = self.aoi.value()
        if self.valuation_container.value():
            args[self.land_grid_points.args_key] = self.land_grid_points.value()
            args[self.machine_econ_table.args_key] = (
                self.machine_econ_table.value())
            args[self.number_of_machines.args_key] = (
                self.number_of_machines.value())

        return args
