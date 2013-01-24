import pandas as pd
import logging
from config import user_config
from commonscripts import update_attributes, bool_to_int, set_trace
from generators import Generator
from optimization import value
from schedule import is_init
import bidding


class HydroGenerator(Generator):
    """
    A hydro plant model, including the upstream reservoir.
    Has constraints and variables which are significantly different from conventional generators.
    """
    def __init__(self,
                 name, bus=None, index=None,
                 downstream_reservoir=None,
                 delay_downstream=0,
                 volume_min=0, volume_max=None,
                 volume_initial=0,
                 volume_final=None,
                 outflow_min=0, outflow_max=None,
                 outflow_initial=None,
                 power_min=0, power_max=None,
                 power_initial=0,
                 spill_min=0, spill_max=None,
                 spill_initial=0,
                 production_curve_string='10Q',
                 production_curve_correction_string='0',
                 head_correction_string='0',
                 inflow_schedule=None
                 ):
        update_attributes(self, locals())  # load in inputs
        self.init_optimization()
        self.upstream_reservoirs = []
        self.is_hydro = True
        self.is_controllable = True
        self.production_curve_model = bidding.makeModel(production_curve_string, min_input=self.outflow_min, max_input=self.outflow_max)
        self.production_correction_model = bidding.makeModel(
            production_curve_correction_string)
        self.head_correction_constant = get_leading_number(
            head_correction_string)
        if self.outflow_initial is None:
            self.outflow_initial = (self.outflow_max - self.outflow_min) / 2.0

    def outflow(self, time=None, scenario=None):
        return self.get_variable('outflow', time=str(time), indexed=True, scenario=scenario)

    def spill(self, time=None, scenario=None):
        return self.get_variable('spill', time=str(time), indexed=True, scenario=scenario)

    def volume(self, time=None, scenario=None):
        return self.get_variable('volume', time=str(time), indexed=True, scenario=scenario)

    def outflow_total(self, time=None, scenario=None):
        return self.outflow(time, scenario) + self.spill(time, scenario)

    def volume_change(self, t, times):
        '''change in volume between t and t-1'''
        if t > 0:
            previous_vol = self.volume(times[t - 1])
        else:
            previous_vol = self.volume_initial
        return self.volume(times[t]) - previous_vol

    def production(self, time):
        '''
        total power production is the sum of:
        the production curve (based on outflow),
        the volume correction (based on volume),
        and the head correction (based on outflow and volume)
        '''
        return self.production_curve(time).output() + self.production_correction(time).output() + self.head_correction(time)

    def production_curve(self, time):
        return self.get_child('production_curves', time)

    def production_correction(self, time):
        return self.get_child('production_corrections', time)

    def head_correction(self, time):
        return self.head_correction_constant * self.outflow(time) * self.volume(time)

    def cost(self, *a, **k):
        return 0

    def operatingcost(self, *a, **k):
        return 0

    def incrementalcost(self, *a, **k):
        return 0

    def truecost(self, *a, **k):
        return 0

    def cost_first_stage(self, *a, **k):
        return 0

    def cost_second_stage(self, *a, **k):
        return 0

    def status(self, *a, **k):
        return True

    def cost_startup(self, *a, **k):
        return 0

    def cost_shutdown(self, *a, **k):
        return 0

    def getstatus(self, *a, **k):
        return {}

    def create_variables(self, times):
        self.add_variable('power', index=times.set,
                          low=self.power_min, high=self.power_max)
        self.add_variable('outflow', index=times.set,
                          low=self.outflow_min, high=self.outflow_max)
        self.add_variable('spill', index=times.set,
                          low=self.spill_min, high=self.spill_max)
        self.add_variable('volume', index=times.set,
                          low=self.volume_min, high=self.volume_max)

        # production curve
        production_curves = dict(zip(times, [bidding.Bid(
            model=self.production_curve_model,
            time=time,
            input_var=self.outflow(time),
            owner_iden=str(self),
            time_iden=str(time)) for time in times]))
        production_corrections = dict(zip(times, [bidding.Bid(
            model=self.production_correction_model,
            time=time,
            input_var=self.volume(time),
            owner_iden=str(self),
            time_iden=str(time)) for time in times]))
        self.add_children(production_curves, 'production_curves')
        self.add_children(production_corrections, 'production_corrections')
        for time in times:
            self.production_curve(time).create_variables()
            self.production_correction(time).create_variables()

    def create_constraints(self, times, generators):
        # initial and final volumes
        self.add_constraint('volume final', times[-1], self.volume(
            times[-1]) >= self.volume_final)

        other_hydro_generators = filter(lambda gen: gen.is_hydro, generators)

        def upstream_unit_outflow(h, t):
            upstream_gen = getclass_inlist(other_hydro_generators, h, 'index')
            outflow_time = times[t].Start - hours(
                upstream_gen.delay_downstream)
            if outflow_time < times.Start:
                return upstream_gen.outflow_initial + upstream_gen.spill_initial
            else:
                outflow_time = times.get_time_by_start(outflow_time)
                return upstream_gen.outflow_total(outflow_time)
        for t, time in enumerate(times):
            # network balance
            upstream_inflow = sum(
                upstream_unit_outflow(r, t) for r in self.upstream_reservoirs)
            natural_inflow = self.inflow_schedule.get_amount(time)
            self.add_constraint('water balance', time, self.volume_change(t, times) == upstream_inflow + natural_inflow - self.outflow_total(time))

            # production
            self.add_constraint(
                'production', time, self.power(time) == self.production(time))
            self.production_curve(time).create_constraints()
            self.production_correction(time).create_constraints()

    def __str__(self):
        return 'h{ind}'.format(ind=self.index)
