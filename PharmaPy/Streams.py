# -*- coding: utf-8 -*-
"""
Created on Wed May 27 10:12:13 2020

@author: dcasasor
"""

from PharmaPy.Phases import LiquidPhase, SolidPhase, VaporPhase
from PharmaPy.Interpolation import NewtonInterpolation
from scipy.interpolate import CubicSpline
import numpy as np


def Interpolation(t_data, y_data, time, newton=True, num_points=3):
    idx_time = np.argmin(abs(time - t_data))

    idx_lower = max(0, idx_time - 1)
    idx_upper = min(len(t_data) - 1, idx_lower + num_points)

    t_interp = t_data[idx_lower:idx_upper]
    y_interp = y_data[idx_lower:idx_upper]

    # Newton interpolation (quadratic, three points)
    interp = NewtonInterpolation(t_interp, y_interp)
    y_target = interp.evalPolynomial(time)

    return y_target


class LiquidStream(LiquidPhase):
    def __init__(self, path_thermo=None, temp=298.15, pres=101325,
                 mass_flow=0, vol_flow=0, mole_flow=0,
                 controls=None, args_control=None,
                 mass_frac=None, mole_frac=None, mass_conc=None, mole_conc=None,
                 ind_solv=None, num_interpolation_points=3):

        super().__init__(path_thermo, temp, pres,
                         mass=mass_flow, vol=vol_flow, moles=mole_flow,
                         mass_frac=mass_frac, mole_frac=mole_frac,
                         mass_conc=mass_conc, mole_conc=mole_conc,
                         ind_solv=ind_solv)

        self.mass_flow = self.mass
        self.vol_flow = self.vol
        self.mole_flow = self.moles

        self._DynamicInlet = None
        self.controllable = ('mass_flow', 'mole_flow', 'vol_flow', 'temp')

        # del self.mass
        # del self.vol
        # del self.moles

        # Outputs from upstream UO
        self.y_upstream = None
        self.time_upstream = None

        # Controls
        if controls is None:
            controls = {}
        else:
            if args_control is None:
                args_control = {key: () for key in controls.keys()}

            update_dict = {}
            for key, fun in controls.items():
                update_dict[key] = fun(0, *args_control[key])

            self.updatePhase(**update_dict)

        self.controls = controls
        self.args_control = args_control

        self.num_interpolation_points = num_interpolation_points

    @property
    def DynamicInlet(self):
        return self._DynamicInlet

    @DynamicInlet.setter
    def DynamicInlet(self, dynamic_object):
        dynamic_object.controllable = self.controllable
        dynamic_object.parent_instance = self

        self._DynamicInlet = dynamic_object

    def InterpolateInputs(self, time):
        if isinstance(time, (float, int)):
            # Assume steady state for extrapolation
            time = min(time, self.time_upstream[-1])

            y_interpol = Interpolation(self.time_upstream, self.y_inlet,
                                       time,
                                       num_points=self.num_interpolation_points)
        else:
            interpol = CubicSpline(self.time_upstream, self.y_inlet)
            flags_interpol = time > self.time_upstream[-1]

            if any(flags_interpol):
                time_interpol = time[~flags_interpol]
                y_interp = interpol(time_interpol)

                y_extrapol = np.tile(y_interp[-1],
                                     (sum(flags_interpol), 1))
                y_interpol = np.vstack((y_interp, y_extrapol))
            else:
                y_interpol = interpol(time)

        return y_interpol

    def updatePhase(self, concentr=None, mass_conc=None,
                    mass_frac=None, mole_frac=None,
                    vol_flow=None, mass_flow=None, mole_flow=None):

        if vol_flow is None:
            vol_flow = self.vol_flow

        if mass_flow is None:
            mass_flow = self.mass_flow

        if mole_flow is None:
            mole_flow = self.mole_flow

        super().updatePhase(concentr, mass_conc, mass_frac, mole_frac,
                            vol_flow, mass_flow, mole_flow)

        self.mass_flow = self.mass
        self.vol_flow = self.vol
        self.mole_flow = self.moles

        del self.mass
        del self.vol
        del self.moles

    def evaluate_inputs(self, time):
        if self.DynamicInlet is None:
            inputs = {}
            for attr in self.controllable:
                inputs[attr] = getattr(self, attr)

        else:
            inputs = self.DynamicInlet.evaluate_inputs(time)

        return inputs


class SolidStream(SolidPhase):
    def __init__(self, path_thermo=None, temp=298.15, pres=101325,
                 mass_flow=0, mass_frac=None,
                 distrib=None, x_distrib=None, kv=1):

        super().__init__(path_thermo, temp, pres=pres,
                         mass=mass_flow, mass_frac=mass_frac,
                         # moments=moments,
                         distrib=distrib, x_distrib=x_distrib, kv=kv)

        self.mass_flow = self.mass
        # self.vol_flow = self.vol
        self.mole_flow = self.moles

        # del self.mass
        # # del self.vol
        # del self.moles


class VaporStream(VaporPhase):
    def __init__(self, path_thermo=None, temp=298.15, pres=101325,
                 mass_flow=0, vol_flow=0, mole_flow=0,
                 mass_frac=None, mole_frac=None, mole_conc=None):

        super().__init__(path_thermo, temp, pres,
                         mass=mass_flow, vol=vol_flow, moles=mole_flow,
                         mass_frac=mass_frac, mole_frac=mole_frac,
                         mole_conc=mole_conc)

        self.mass_flow = self.mass
        self.vol_flow = self.vol
        self.mole_flow = self.moles

        self.controllable = ('mass_flow', 'mole_flow', 'vol_flow', 'temp')

        # del self.mass
        # del self.vol
        # del self.moles

    @property
    def DynamicInlet(self):
        return self._DynamicInlet

    @DynamicInlet.setter
    def DynamicInlet(self, dynamic_object):
        dynamic_object.controllable = self.controllable
        dynamic_object.parent_instance = self

        self._DynamicInlet = dynamic_object

    def evaluate_inputs(self, time):
        if self.DynamicInlet is None:
            inputs = {}
            for attr in self.controllable:
                inputs[attr] = getattr(self, attr)

        else:
            inputs = self.DynamicInlet.evaluate_inputs(time)

        return inputs


if __name__ == '__main__':
    path = '../../data/evaporator/compounds_evap.json'
    stream_liq = LiquidStream(path)
