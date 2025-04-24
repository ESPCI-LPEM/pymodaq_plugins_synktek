from typing import NamedTuple

import numpy as np

from qtpy import QtWidgets
from pyqtgraph.parametertree.parameterTypes.basetypes import GroupParameter
from pyqtgraph.parametertree.parameterTypes import registerParameterType

from pymodaq_utils.utils import ThreadCommand
from pymodaq_data.data import DataToExport
from pymodaq_gui.parameter import Parameter

from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.data import DataFromPlugins

from MCL import MCL

LOCKIN_CHANNELS = ['L1', 'L2']
OUTPUT_CHANNELS = ["x", "y", "r", "thetadeg"]

class MCL_LIData_generalreadings(NamedTuple):
    dt_s: float
    cyclespersample: float
    syncindex: float
    time_s=float
    lockinf_hz: float
    pll1_hz: float
    pll2_hz: float
    composite1_hz: float


class MCL_LIData_moduledata(NamedTuple):
    digitalInf_hz: float
    digitaloutf_hz: float
    amplitude_vrms: float
    output_offset_v: float


class MCL_LIData_datareadings(NamedTuple):
    generalreadings: MCL_LIData_generalreadings
    moduledata: list[MCL_LIData_moduledata]
    dc: list[float]
    x: list[float]
    y: list[float]
    r: list[float]
    thetadeg: list[float]


class ChannelGroup(GroupParameter):
    """Group Parameter listing the different lockins of the MCL1540
    """

    def __init__(self, **opts) -> None:
        opts['type'] = 'outputchannel'
        opts['addText'] = 'Add lockin'
        super().__init__(**opts)

    def addNew(self) -> None:
        """Add new channel to viewer
        """
        name_prefix = "channel"
        
        child_indexes = [int(par.name()[len(name_prefix) + 1:])
                         for par in self.children()]
        
        if child_indexes == []:
            newindex = 0
        else:
            newindex = max(child_indexes) + 1

        child = {
            'title': f'Measure {newindex:02.0f}',
            'name': f'{name_prefix}{newindex:02.0f}',
            'type': 'itemselect',
            'removable': True,
            'value': dict(all_items=OUTPUT_CHANNELS, selected=[OUTPUT_CHANNELS[0]])
        }

        self.addChild(child)

registerParameterType('outputchannel', ChannelGroup, override=True)

class DAQ_0DViewer_MCL1540_Lockin(DAQ_Viewer_base):
    """ Instrument plugin class for a OD viewer.
    
    This object inherits all functionalities to communicate with PyMoDAQ’s DAQ_Viewer module through inheritance via
    DAQ_Viewer_base. It makes a bridge between the DAQ_Viewer module and the Python wrapper of a particular instrument.

    TODO Complete the docstring of your plugin with:
        * The set of instruments that should be compatible with this instrument plugin.
        * With which instrument it has actually been tested.
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
    params = comon_parameters+[
            {'title': 'Ip address', 'name': 'ip', 'type': 'str'},
            {'title': 'Lockin channel', 'name': 'lockinchannel', 'type': 'list', 'limits': LOCKIN_CHANNELS},
            {'title': 'Output channel', 'name': 'outputchannel', 'type': 'outputchannel'}
        ]
    live_mode_available = True

    def ini_attributes(self):
        self.controller: MCL = None

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """
        pass

    def ini_detector(self, controller=None):
        """Detector communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one actuator/detector by controller
            (Master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """

        self.ini_detector_init(slave_controller=controller)

        if self.is_master:
            self.controller = MCL()
            self.controller.connect(self.settings['ip'])

        self.dte_signal_temp.emit(
            DataToExport(
                name='lockin',
                data=[DataFromPlugins(
                    name='Mock1',
                    data=[np.array([0]), np.array([0])],
                    dim='Data0D',
                    labels=['x', 'y']
                )]
            )
        )

        # Library quit on failure and does not send signal. May be improved.
        info = "MCL1-540 initialized"
        initialized = True
        return info, initialized

    def close(self):
        """Terminate the communication protocol"""
        self.controller.disconnect()

    def grab_data(self, Naverage=1, **kwargs):
        """Start a grab from the detector

        Parameters
        ----------
        Naverage: int
            Number of hardware averaging (if hardware averaging is possible, self.hardware_averaging should be set to
            True in class preamble and you should code this implementation)
        kwargs: dict
            others optionals arguments
        """
        self.controller.data.L1.register_callback(self.callback, self.controller)
        self.live = True


    def callback(self, lockin_channel: int, data: MCL_LIData_generalreadings, mcl: MCL):
        """optional asynchrone method called when the detector has finished its acquisition of data"""

        if f"L{lockin_channel + 1}" == self.settings['lockinchannel']:
            data_te = []
            for child in self.settings.child('outputchannel').children():
                labels = child.value()['selected'][:]
                subdata = [np.array([getattr(data, label)[0]])
                        for label in labels]
                data_te.append(DataFromPlugins(
                        name=child.name(),
                        data=subdata,
                        dim='Data0D',
                        labels=labels
                ))
            self.dte_signal.emit(
                DataToExport(
                    name='mcl1540',
                    data=data_te
                )
            )

    def stop(self):
        """Stop the current grab hardware wise if necessary"""
        self.controller.data.L1.unregister_callback(self.callback)
        self.live = False
        self.emit_status(ThreadCommand('Update_Status', ['Stopped lockin acquistion.']))
        return ''


if __name__ == '__main__':
    main(__file__)
