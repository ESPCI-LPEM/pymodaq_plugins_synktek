from typing import Union, List, Dict
from pymodaq.control_modules.move_utility_classes import (DAQ_Move_base, comon_parameters_fun,
                                                          main, DataActuatorType, DataActuator)

from pymodaq_utils.utils import ThreadCommand
from pymodaq_gui.parameter import Parameter

from MCL import MCL
LOCKIN_CHANNELS = ['L1', 'L2']


class DAQ_Move_MCL1540_Lockin(DAQ_Move_base):
    """ Instrument plugin class for an actuator.

    This object inherits all functionalities to communicate with PyMoDAQ’s DAQ_Move module through inheritance via
    DAQ_Move_base. It makes a bridge between the DAQ_Move module and the Python wrapper of a particular instrument.

    TODO Complete the docstring of your plugin with:
        * The set of controllers and actuators that should be compatible with this instrument plugin.
        * With which instrument and controller it has been tested.
        * The version of PyMoDAQ during the test.
        * The version of the operating system.
        * Installation instructions: what manufacturer’s drivers should be installed to make it run?

    Attributes:
    -----------
    controller: object
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library.

    # TODO add your particular attributes here if any

    """
    is_multiaxes = False  # TODO for your plugin set to True if this plugin is controlled for a multiaxis controller
    _axis_names: Union[List[str], Dict[str, int]] = [
        'Axis1', 'Axis2']  # TODO for your plugin: complete the list
    # TODO for your plugin: put the correct unit here, it could be
    _controller_units: Union[str, List[str]] = 'Hz'
    # TODO  a single str (the same one is applied to all axes) or a list of str (as much as the number of axes)
    # TODO replace this by a value that is correct depending on your controller
    _epsilon: Union[float, List[float]] = 0.1
    # TODO it could be a single float of a list of float (as much as the number of axes)
    # wether you use the new data style for actuator otherwise set this
    data_actuator_type = DataActuatorType.DataActuator
    # as  DataActuatorType.float  (or entirely remove the line)
    def __init__(self, parent=None, params_state=None):
            super().__init__(parent, params_state)
            self._enabled = False

    params = [{'title': 'Ip address', 'name': 'ip', 'type': 'str', 'value': '172.22.11.2'},


              {'title': 'Full-scale sensitivity', 'name': 'sensitivity',
               'type': 'list', 'limits': [10, 1, 0.1]},

              {'title': 'Voltage (V)', 'name': 'voltage', 'type': 'float',
               'limits': [0, 5], 'value': 1e-6},

              {'title': 'Frequency (Hz)', 'name': 'frequency', 'type': 'float',
               'limits': [0, 30], 'value': 13},

              {'title': 'Output enabled:', 'name': 'enabled',
                  'type': 'led_push', 'value': False}

              ] + comon_parameters_fun(is_multiaxes, axis_names=_axis_names, epsilon=_epsilon)
    # _epsilon is the initial default value for the epsilon parameter allowing pymodaq to know if the controller reached
    # the target value. It is the developer responsibility to put here a meaningful value

    def ini_attributes(self):
        self.controller: MCL = None
        pass

    def get_actuator_value(self):
        """Get the current value from the hardware with scaling conversion.

        Returns
        -------
        float: The position obtained after scaling conversion.
        """
        freq = DataActuator(data=self.controller.config.frequency_1.frequency)
        freq = self.get_position_with_scaling(freq)
        return freq
    

    def enabled(self):
        return self._enabled

    def enable_source(self, enable=True):
        self._enabled = enable
        if enable:
            self.controller.config.output_B.outputenabled = True
        else:
            self.controller.config.output_B.outputenabled = False

        self.settings.child('enabled').setValue(enable)

    def close(self):
        """Terminate the communication protocol"""
        self.controller.disconnect()

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """

        if param.name() == 'voltage':
            self.controller.config.amplitude_1.amplitude = param.value()
            print('voltage equal to', self.controller.config.amplitude_1.amplitude)


        elif param.name() == 'enabled':
            self.enable_source(param.value())
            
        elif param.name() == 'frequency':
            self.controller.config.frequency_1.frequency = param.value()

        else:
            pass

    def ini_stage(self, controller=None):
        """Actuator communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one actuator by controller (Master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """

        self.ini_stage_init(slave_controller=controller)

        if self.is_master:  # is needed when controller is master
            try:
                self.controller = MCL()
                self.controller.connect(mcl_ip=self.settings['ip'])
                info = "Connected to Lockin"
                initialized = True

            except:
                initialized = False
                info = "connection failed"

        return info, initialized

    def move_abs(self, value: DataActuator):
        """ Move the actuator to the absolute target defined by value

        Parameters
        ----------
        value: (float) value of the absolute target positioning
        """

        # if user checked bounds, the defined bounds are applied here
        value = self.check_bound(value)
        self.target_value = value
        # apply scaling if the user specified one
        value = self.set_position_with_scaling(value)

        # when writing your own plugin replace this line
        self.controller.config.frequency_1.frequency = value.value()

        self.emit_status(ThreadCommand(
            'Update_Status', ['changed frequency of the Lockin !']))

    def move_rel(self, value: DataActuator):
        """ Move the actuator to the relative target actuator value defined by value

        Parameters
        ----------
        value: (float) value of the relative target positioning
        """
        value = self.check_bound(
            self.current_position + value) - self.current_position

        self.target_value = value + self.current_position
        value = self.set_position_relative_with_scaling(value)

        # when writing your own plugin replace this line
        self.controller.config.frequency_1.frequency = self.target_value
        self.emit_status(ThreadCommand(
            'Update_Status', ['relative frequency updated !']))

    def move_home(self):
        """Call the reference method of the controller"""

        "set the Lockin to 16.7 Hz"
        self.controller.config.frequency_1.frequency = 16.7
        self.emit_status(ThreadCommand(
            'Update_Status', ['Went back to reference frequency']))

    def stop_motion(self):
        """Stop the actuator and emits move_done signal"""
        pass


if __name__ == '__main__':
    main(__file__)
