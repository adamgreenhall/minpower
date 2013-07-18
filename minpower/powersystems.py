"""
Defines models for power systems components, including
:class:`~powersystems.PowerSystem`, :class:`~powersystems.Bus`,
:class:`~powersystems.Load` and  :class:`~powersystems.Line`.
:class:`~powersystems.Generator` components can be found
in the :module:`~generators`. Each of these objects inherits an
optimization framework from :class:`~optimization.OptimizationObject`.
"""

import logging

from commonscripts import (update_attributes, getattrL, flatten, set_trace)
from config import user_config

from optimization import (value, OptimizationObject,
                          OptimizationProblem, OptimizationError)
import stochastic


from coopr import pyomo
import numpy as np
import pandas as pd

max_hydro_profits_form = False


class Load(OptimizationObject):
    """
    Describes a power system load (demand).
    Currently only real power is considered.
    For OPF problems, the name of the bus can.
    For UC problems, schedules (pandas.Series objects) are used.
    By setting `sheddingallowed`, the amount of power can become a variable,
        (bounded to be at most the scheduled amount).
    """
    def __init__(self,
                 name='', index=None, bus='system', schedule=None,
                 sheddingallowed=True,
                 cost_shedding=None,
                 ):
        update_attributes(self, locals())  # load in inputs
        if cost_shedding is None:
            self.cost_shedding = user_config.cost_load_shedding
        self.init_optimization()
        self.shedding_mode = False

    def power(self, time, scenario=None, evaluate=False):
        if self.shedding_mode:
            power = self.get_variable('power', time,
                scenario=scenario, indexed=True)
            if evaluate:
                power = value(power)
            return power
        else:
            return self.get_scheduled_output(time)

    def shed(self, time, scenario=None, evaluate=False):
        return self.get_scheduled_output(time) - self.power(time, scenario, evaluate)

    def cost(self, time, scenario=None):
#  Moved load shedding cost to penalty
#        return self.cost_shedding * self.shed(time, scenario)
        return 0

    def penalty(self, time, scenario=None):
        return self.cost_shedding * self.shed(time, scenario)

    def cost_first_stage(self, times):
        return 0

    def cost_second_stage(self, times):
        return sum(self.cost(time) for time in times)

#  Added penalties to influence solution
    def penalties(self, times):
        return sum(self.cost(time) for time in times)

    def create_variables(self, times):
        if self.shedding_mode:
            self.add_variable('power', index=times.set, low=0)

    def create_constraints(self, times):
        if self.shedding_mode:
            for time in times:
                self.add_constraint('max_load_power', time,
                                    self.power(time) <= self.get_scheduled_output(time))

    def create_objective(self, times):
#  Added Penality to influence solution
#        return sum([self.cost(time) for time in times])
        return sum([self.cost(time)+self.penalty(time) for time in times])

    def __str__(self):
        return 'd{ind}'.format(ind=self.index)


    def get_scheduled_output(self, time):
        return float(self.schedule.ix[time])


class Line(OptimizationObject):
    """
    A tranmission line. Currently the model
    only considers real power flow under normal conditions.
    """
    def __init__(self, name='', index=None, frombus=None, tobus=None,
                 reactance=0.05, pmin=None, pmax=9999, **kwargs):
        update_attributes(self, locals())  # load in inputs
        if self.pmin is None:
            self.pmin = -1 * self.pmax   # default is -1*pmax
        self.init_optimization()

    def power(self, time):
        return self.get_variable('power', time, indexed=True)

    def price(self, time):
        '''congestion price on line'''
        return self.get_dual('line flow', time)

    def create_variables(self, times):
        self.add_variable('power', index=times.set)

    def create_constraints(self, times, buses):
        '''create the constraints for a line over all times'''
        busNames = getattrL(buses, 'name')
        iFrom, iTo = busNames.index(self.frombus), busNames.index(self.tobus)
        for t in times:
            line_flow_ij = self.power(t) == \
                1 / self.reactance * (buses[iFrom].angle(t) -
                                      buses[iTo].angle(t))
            self.add_constraint('line flow', t, line_flow_ij)
            self.add_constraint(
                'line limit high', t, self.power(t) <= self.pmax)
            self.add_constraint(
                'line limit low', t, self.pmin <= self.power(t))
        return

    def __str__(self):
#  Prefer descriptive names
#        return 'k{ind}'.format(ind=self.index)
#        return 'k{ind}-{name}'.format(name=self.name,ind=self.index)
        return 'Line_' + self.name

    def __int__(self):
        return self.index


class Bus(OptimizationObject):
    """
    A transmission bus bus (usually a substation where one or more
    tranmission lines start/end).

    :param isSwing: flag if the bus is the swing bus
      (sets the reference angle for the system)
    """
    def __init__(self, name=None, index=None, isSwing=False, exports=None):
        update_attributes(self, locals())  # load in inputs
        self.generators, self.loads = [], []
        self.init_optimization()

    def angle(self, time):
        return self.get_variable('angle', time, indexed=True)

    def price(self, time):
        return self.get_dual('power balance', time)

    def Pgen(self, t, evaluate=False):
        if evaluate:
            return sum(value(gen.power(t)) for gen in self.generators)
        else:
            return sum(gen.power(t) for gen in self.generators)

    def Pload(self, t, evaluate=False):
        if evaluate:
            return sum(value(ld.power(t)) for ld in self.loads)
        else:
            return sum(ld.power(t) for ld in self.loads)

    def Pexport(self, t, evaluate=False):
        if not self.has_exports: return 0
        P = self.get_variable('power_export', t, indexed=True)
        return value(P) if evaluate else P

    def Pimport(self, t, evaluate=False):
        if not self.has_imports: return 0
        P = self.get_variable('power_import', t, indexed=True)
        return value(P) if evaluate else P

    def power_balance(self, t, Bmatrix, allBuses):
        if len(allBuses) == 1:
            lineFlowsFromBus = 0
        else:
            lineFlowsFromBus = sum([
                Bmatrix[self.index][otherBus.index] * otherBus.angle(t)
                for otherBus in allBuses])  # P_{ij}=sum_{i} B_{ij}*theta_j ???
        lineFlowsFromBus += self.Pexport(t) - self.Pimport(t)

        return self.Pgen(t) - self.Pload(t) - lineFlowsFromBus

    def create_variables(self, times):
        self.add_children(self.generators, 'generators')
        self.add_children(self.loads, 'loads')
        logging.debug('added bus {} components - generators and loads'.format(
            self.name))
        for gen in self.generators:
            gen.create_variables(times)

        logging.debug('created generator variables')
        for load in self.loads:
            load.create_variables(times)
        logging.debug('created load variables')
        self.add_variable('angle', index=times.set)
        
        self.has_imports = False
        self.has_exports = False
        if self.exports is not None:
            self.add_variable('power_export', index=times.set,
                low=self.exports['exportmin'],
                high=self.exports['exportmax'])
            self.has_exports = True
            if 'priceimport' in self.exports.columns:
                self.add_variable('power_import', index=times.set,
                    low=self.exports['importmin'],
                    high=self.exports['importmax'])
                self.has_imports = True
        logging.debug('created bus variables ... returning')
        return

    def create_objective(self, times):
        return self.cost_first_stage(times) + self.cost_second_stage(times) + self.penalty(time)

    def cost_first_stage(self, times):
        cost = sum(gen.cost_first_stage(times) for gen in self.generators) + \
            sum(load.cost_first_stage(times) for load in self.loads)
        if max_hydro_profits_form:
            cost *= -1
            # assuming hydro generators have no 1st stage income
        return cost

    def cost_second_stage(self, times):
        cost = sum(gen.cost_second_stage(times) for gen in self.generators) + \
            sum(load.cost_second_stage(times) for load in self.loads)
        if self.has_imports:
            cost += sum(self.Pimport(t) * self.exports.priceimport[t] for t in times)
        if self.has_exports:
            cost -= sum(self.Pexport(t) * self.exports.priceexport[t] for t in times)
        if max_hydro_profits_form:
            # assuming hydro generators have no costs
            cost *= -1
        return cost

#  Added Penalties to influence solution
    def penalties(self, times):
        cost = sum(gen.penalties(times) for gen in self.generators) + \
            sum(load.penalties(times) for load in self.loads)
        return cost

    def create_constraints(self, times, Bmatrix, buses, include_children=True):
        if include_children:
            for gen in self.generators:
                gen.create_constraints(times)
            for load in self.loads:
                load.create_constraints(times)
        nBus = len(buses)
        for time in times:
            self.add_constraint('power balance', time, self.power_balance(
                time, Bmatrix, buses) == 0)  # power balance must be zero
            if nBus > 1 and self.isSwing:
                self.add_constraint('swing bus', time, self.angle(
                    time) == 0)  # swing bus has angle=0
        return
    # def clear_constraints(self):
    #     self.constraints={}
    #     for gen in self.generators: gen.clear_constraints()
    #     for load in self.loads: load.clear_constraints()

    def __str__(self):
#  Prefer descriptive names
#        return 'i{ind}'.format(ind=self.index)
#        return 'i{ind}-{name}'.format(name=self.name,ind=self.index)
        return 'Bus_' + self.name


class PowerSystem(OptimizationProblem):
    '''
    Power systems object which is the container for all other components.

    :param generators: list of :class:`~powersystem.Generator` objects
    :param loads: list of :class:`~powersystem.Load` objects
    :param lines: list of :class:`~powersystem.Line` objects

    Other settings are inherited from `user_config`.
    '''
    def __init__(self, generators, loads, lines=None, exports=None):
        # load in inputs
        update_attributes(self, locals(),
                          exclude=['generators', 'loads', 'lines'])
        self.reserve_fixed = user_config.reserve_fixed
        self.reserve_load_fraction = user_config.reserve_load_fraction
        self.reserve_required = (self.reserve_fixed > 0) or \
            (self.reserve_load_fraction > 0.0)
        
        self.has_exports = exports is not None and len(exports) > 0
        self.has_imports = self.has_exports and 'priceimports' in exports.columns

        if lines is None:  # pragma: no cover
            lines = []

        buses = self.make_buses_list(loads, generators, exports)

        self.create_admittance_matrix(buses, lines)
        self.init_optimization()

        self.add_children(buses, 'buses')
        self.add_children(lines, 'lines')

        self.is_stochastic = \
            any(map(lambda gen: gen.is_stochastic, generators))
        self.has_hydro = \
            any(map(lambda gen:
                getattr(gen, 'is_hydro', False), generators))
        self.shedding_mode = False



    def make_buses_list(self, loads, generators, exports=None):
        """
        Create list of :class:`powersystems.Bus` objects
        from the load and generator bus names. Otherwise
        (as in ED,UC) create just one (system)
        :class:`powersystems.Bus` instance.

        :param loads: a list of :class:`powersystems.Load` objects
        :param generators: a list of :class:`powersystems.Generator` objects
        :returns: a list of :class:`powersystems.Bus` objects
        """
        busNameL = []
        busNameL.extend(getattrL(generators, 'bus'))
        busNameL.extend(getattrL(loads, 'bus'))
        busNameL = pd.Series(pd.unique(busNameL)).dropna().tolist()

        if len(busNameL) == 0:
            busNameL = ['system']

        buses = []
        swingHasBeenSet = False

        for b, busNm in enumerate(busNameL):
            newBus = Bus(name=busNm, index=b)
            for gen in generators:
                if gen.bus == newBus.name:
                    newBus.generators.append(gen)
                if not swingHasBeenSet:
                    newBus.isSwing = swingHasBeenSet = True
            for ld in loads:
                if ld.bus == newBus.name:
                    newBus.loads.append(ld)
            if self.has_exports and busNm in exports.index.levels[0]:
                newBus.exports = exports.ix[busNm]
            buses.append(newBus)
        return buses

    def create_admittance_matrix(self, buses, lines):
        """
        Creates the admittance matrix (B),
        with elements = total admittance of line from bus i to j.
        Used in calculating the power balance for OPF problems.

        :param buses: list of :class:`~powersystems.Line` objects
        :param lines: list of :class:`~powersystems.Bus` objects
        """
        nB = len(buses)
        self.Bmatrix = np.zeros((nB, nB))
        namesL = [bus.name for bus in buses]
        for line in lines:
            busFrom = buses[namesL.index(line.frombus)]
            busTo = buses[namesL.index(line.tobus)]
            self.Bmatrix[busFrom.index, busTo.index] += -1 / line.reactance
            self.Bmatrix[busTo.index, busFrom.index] += -1 / line.reactance
        for i in range(0, nB):
            self.Bmatrix[i, i] = -1 * sum(self.Bmatrix[i, :])

    def loads(self):
        return flatten(bus.loads for bus in self.buses)

    def generators(self):
        return flatten(bus.generators for bus in self.buses)

    def create_variables(self, times):
        self.add_variable('cost_first_stage')
        self.add_variable('cost_second_stage')
        self.add_variable('penalties')
        self.add_set('times', times._set, ordered=True)
        times.set = self._model.times
        for bus in self.buses:
            bus.create_variables(times)
        for line in self.lines:
            line.create_variables(times)
        logging.debug('... created power system vars... returning')

    def cost_first_stage(self, scenario=None):
        return self.get_component('cost_first_stage', scenario=scenario)

    def cost_second_stage(self, scenario=None):
        return self.get_component('cost_second_stage', scenario=scenario)

#  Added Penalties to influence solution
    def penalties(self, scenario=None):
        return self.get_component('penalties', scenario=scenario)

    def create_objective(self, times):
        sense = pyomo.maximize if max_hydro_profits_form else pyomo.minimize
        self.add_objective(self.cost_first_stage() + self.cost_second_stage() + self.penalties(),
            sense=sense)

    def create_constraints(self, times, include_children=True):
        if include_children:
            if user_config.duals:
                self.add_suffix('dual')
            for bus in self.buses:
                bus.create_constraints(times, self.Bmatrix, self.buses)
            for line in self.lines:
                line.create_constraints(times, self.buses)

        # system reserve constraint
        self._has_reserve = not self.shedding_mode and \
            (self.reserve_fixed > 0 or self.reserve_load_fraction > 0)
        if self._has_reserve:
            for time in times:
                required_generation_availability = self.reserve_fixed + (1.0 + self.reserve_load_fraction) * sum(load.power(time) for load in self.loads())
                generation_availability = sum(
                    gen.power_available(time) for gen in self.generators())
                self.add_constraint('reserve', generation_availability >= required_generation_availability, time=time)

        self.add_constraint('system_cost_first_stage',
            self.cost_first_stage() == \
            sum(bus.cost_first_stage(times) for bus in self.buses))
        self.add_constraint('system_cost_second_stage',
            self.cost_second_stage() == \
            sum(bus.cost_second_stage(times) for bus in self.buses))
        self.add_constraint('system_penalties',
            self.penalties() == \
            sum(bus.penalties(times) for bus in self.buses))

    def iden(self, time=None):
        name = 'system'
        if time is not None:
            name += '_' + str(time)
        return name

    def total_scheduled_load(self):
        return sum([load.schedule for load in self.loads()])

    def total_scheduled_generation(self):
        return sum(gen.schedule for gen in self.generators() if not gen.is_controllable)

    def get_generators_controllable(self):
        return filter(lambda gen: gen.is_controllable, self.generators())

    def get_generators_noncontrollable(self):
        return filter(lambda gen: not gen.is_controllable, self.generators())

    def get_generators_hydro(self):
        return filter(lambda gen: getattr(gen, 'is_hydro', False), self.generators())

    def get_generators_without_scenarios(self):
        return filter(lambda gen: getattr(gen, 'is_stochastic', False) == False, self.generators())

    def get_generator_with_scenarios(self):
        gens = filter(lambda gen: getattr(gen, 'is_stochastic',
                      False), self.generators())
        if len(gens) > 1:  # pragma: no cover
            raise NotImplementedError(
                'Dont handle the case of multiple stochastic generators')
        elif len(gens) == 0:  # pragma: no cover
            return []
        else:
            return gens[0]

    def get_generator_with_observed(self):
        return filter(lambda gen: getattr(gen, 'observed_values', None) is not None, self.generators())[0]

    def set_initial_conditions(self):
        if getattr(self, 'final_condition', None) is not None:
            for gen in self.generators():
                gen.set_initial_condition(
                    **self.final_condition.ix[str(gen)].dropna().to_dict())

    def get_final_conditions(self, sln):
        times = sln.times
        final_condition = {}
        for gen in self.generators():
            final_condition[str(gen)] = \
                gen.get_final_condition(times.non_overlap())
        self.final_condition = pd.DataFrame(final_condition).T.astype(float)
        return


    def solve_problem(self, times):
        try:
            instance = self.solve()

        except OptimizationError:
            # re-do stage, with load shedding allowed
            logging.critical('stage infeasible, re-run with shedding.')
            self.allow_shedding(times)
            try:
                instance = self.solve()
            except OptimizationError:
                scheduled, committed = self.debug_infeasible(times)
                raise OptimizationError('failed to solve with shedding.')
        return instance

    def resolve_stochastic_with_observed(self, instance, sln):
        s = sln.scenarios[0]
        self._model = instance.active_components(pyomo.Block)[s]
        self.is_stochastic = False
        self.stochastic_formulation = False

        self._resolve_problem(sln)

        # re-store the generator outputs and costs
        sln._resolved = True
        sln._get_outputs(resolve=True)
        sln._get_costs(resolve=True)

        self.is_stochastic = True
        self.disallow_shedding()
        return

    def resolve_determinisitc_with_observed(self, sln):
        # store the useful expected value solution information
        sln.expected_status = sln.generators_status.copy()
        sln.expected_power = sln.generators_power.copy()
        sln.expected_fuelcost = sln.fuelcost.copy()
        sln.expected_totalcost = sln.totalcost_generation.copy()
        sln.expected_load_shed = float(sln.load_shed)
        if self.has_hydro:
            sln.expected_hydro_vars = sln.hydro_vars.copy()
        
        # resolve the problem
        self._resolve_problem(sln)

        # re-calc the generator outputs and costs
        sln._resolved = True
        sln._get_outputs()
        sln._get_costs()


        sln.observed_fuelcost = sln.fuelcost
        sln.observed_totalcost = sln.totalcost_generation
        self.disallow_shedding()
        return

    def _set_load_shedding(self, to_mode):
        '''set system mode for load shedding'''
        for load in filter(lambda ld:
                           ld.sheddingallowed, self.loads()):
            load.shedding_mode = to_mode

    def _set_gen_shedding(self, to_mode):
        for gen in filter(lambda g:
            not g.is_controllable and g.sheddingallowed, self.generators()):
            gen.shedding_mode = to_mode

    def allow_shedding(self, times, resolve=False):
        self.shedding_mode = True
        self._set_load_shedding(True)

        if not user_config.economic_wind_shed:
            logging.debug('allowing non-controllable generation shedding')
            self._set_gen_shedding(True)

        const_times = times.non_overlap() if resolve else times

        # make load power into a variable instead of a param
        for load in self.loads():
            try:
                load.create_variables(times)  # need all for the .set attrib
                load.create_constraints(const_times)
            except RuntimeError:
                # load already has a power variable and shedding constraint
                pass

        if not user_config.economic_wind_shed:
            for gen in filter(lambda gen: gen.shedding_mode,
                self.get_generators_noncontrollable()):
                # create only the power_used var, don't reset the power param
                gen.create_variables_shedding(times)
                gen.create_constraints(const_times)

        # recalc the power balance constraint
        for bus in self.buses:
            for time in const_times:
                bus._remove_component('power balance', time)
            bus.create_constraints(const_times,
                self.Bmatrix, self.buses, include_children=False)

        # reset objective
        self.reset_objective()
        self.create_objective(const_times)
        # re-create system cost constraints
        self._remove_component('system_cost_first_stage')
        self._remove_component('system_cost_second_stage')
        self._remove_component('system_penalties')
        if self._has_reserve:
            self._remove_component('reserve')
        self.create_constraints(const_times, include_children=False)

        # recreating all constraints would be simpler
        # but would take a bit longer
        # self.create_constraints(const_times, include_children=True)
        if self.is_stochastic:
            # need to recreate the scenario tree variable links
            stochastic.define_stage_variables(self, times)
            # and the stochastic instance
            stochastic.create_problem_with_scenarios(self, times)


    def disallow_shedding(self):
        # change shedding allowed flags for the next stage
        self.shedding_mode = False
        self._set_load_shedding(False)
        if user_config.economic_wind_shed is False:
            self._set_gen_shedding(False)

    def _resolve_problem(self, sln):
        times = sln.times_non_overlap
        self._remove_component('times')
        self.add_set('times', times._set, ordered=True)
        times.set = self._model.times

        # reset the constraints
        self._remove_all_constraints()
        # dont create reserve constraints
        self.reserve_fixed = 0
        self.reserve_load_fraction = 0

        # set wind to observed power
        gen = self.get_generator_with_observed()
        gen.set_power_to_observed(times)

        # reset objective to only the non-overlap times
        self.reset_objective()
        self.create_objective(times)

        # recreate constraints only for the non-overlap times
        self.create_constraints(times)

        # fix statuses for all units
        self.fix_binary_variables(name_filter='status')

        # if this is a hydro problem - fix the net outflow
        if self.has_hydro:
        
            fixed_hydro_vars = []
            for nm in ['net_outflow', 'volume', 'head', 'elevation']:
                fixed_hydro_vars.extend([
                    getattr(hy, nm)().name \
                    for hy in self.get_generators_hydro()])
            self._fix_variables(fixed_hydro_vars)
            
            # HACK - feasification
            for gen in self.get_generators_hydro():
                for nm in ['volume_to_forebay_elevation', 'flow_to_tailwater_elevation']:
                    if gen.PWmodels[nm].bid_points is not None:
                        gen.PWmodels[nm]._pw_block().deactivate()
                
                #try: el_modeled = gen.get_var('el_fb_curve_el_fb')
                #except AttributeError: el_modeled = {}
                #for tm, val in el_modeled.iteritems(): 
                #    val.value = max(min(val.value, val.ub), val.lb)

        # store original problem solve time
        self.full_sln_time = self.solution_time
        full_mipgap = self.mipgap

        logging.info('resolving with observed values')
        try:
            self.solve() #get_duals=True
        except OptimizationError:
            faststarts = map(lambda gen: str(gen), filter(lambda gen: gen.faststart, self.generators()))
            # at least one faststarting unit must be available (off)
            if user_config.faststart_resolve and \
                (sln.expected_status[faststarts] == 0).any().any():
                self._resolve_with_faststarts(sln)
            else:
                # just shed the un-meetable load and calculate cost later
                self.allow_shedding(sln.times, resolve=True)
                try:
                    self.solve() #get_duals=True
                except OptimizationError:
                    scheduled, committed = self.debug_infeasible(
                        sln.times, resolve_sln=sln)
                    raise

        self.resolve_solution_time = float(self.solution_time)
        self.solution_time = float(self.full_sln_time)

        if self.mipgap:
            self.mipgap_resolve = float(self.mipgap)
        if full_mipgap:
            self.mipgap = float(full_mipgap)

        logging.info('resolved instance with observed values (in {}s)'.format(
            self.resolve_solution_time))

    def _resolve_with_faststarts(self, sln):
        '''allow faststart units to be started up to meet the load'''
        self._unfix_variables()
        self._fix_non_faststarts(sln.times)
        logging.warning('allowing fast-starting units')

        try:
            self.solve()
        except OptimizationError:
            self._unfix_variables()
            self._fix_non_faststarts(sln.times, fix_power=False)
            logging.warning(
                'allowing non fast-starters to change power output')
            try:
                self.solve()
            except OptimizationError:
                logging.warning('allowing load shedding')
                self.allow_shedding(sln.times, resolve=True)
                try:
                    self.solve()
                except OptimizationError:
                    scheduled, committed = self.debug_infeasible(
                        sln.times, resolve_sln=sln)
                    raise

    def _fix_non_faststarts(self, times, fix_power=True):
        '''
        fix non-faststart units - both power and status
        (unless this is infeasible, then only fix status)
        the idea is that fast-starts should be contributing power
        only for system security, not economics
        '''
        names = []
        for gen in filter(lambda gen:
                         (not gen.faststart) and gen.is_controllable, self.generators()):
            names.append(gen.status().name)
            if fix_power:
                names.append(gen.power().name)
        self._fix_variables(names)

    def debug_infeasible(self, times, resolve_sln=None):  # pragma: no cover
        generators = self.generators()
        if resolve_sln:
            windgen = self.get_generator_with_observed()

            scheduled = pd.DataFrame({
                'expected_power': resolve_sln.generators_power.sum(axis=1).values,
                'expected_wind': windgen.schedule.ix[times.non_overlap()],
                'observed_wind': windgen.observed_values.ix[times.non_overlap()],
            })
            scheduled['net_required'] = \
                scheduled.expected_wind - scheduled.observed_wind
        else:
            scheduled = pd.DataFrame({
                'load': self.total_scheduled_load().ix[times.strings.values]})

            if self.is_stochastic:
                gen = self.get_generator_with_scenarios()
                scenarios = gen.scenario_values[times.Start.date()].drop('probability', axis=1).T
                scenarios.index = scheduled.index

                scheduled['net_load'] = scheduled['load'] - sum(
                    map(lambda gen: gen.schedule,
                        filter(lambda gen: not gen.is_stochastic,
                            self.get_generators_noncontrollable())))

                gen_required = (-1 * scenarios).add(scheduled.net_load, axis=0)

                print('generation required')
                print(gen_required)
                print(gen_required.describe())

            else:
                if any([hasattr(gen, 'schedule') for gen in self.generators()]):
                    scheduled['generation'] = self.total_scheduled_generation().ix[times.strings.values]
                else:
                    scheduled['generation'] = 0

                scheduled['net_required'] = scheduled['load'] - \
                    scheduled.generation

        print 'total scheduled\n', scheduled

        if resolve_sln:
            committed = pd.DataFrame(dict(
                Pmin=[gen.pmin for gen in generators],
                Pmax=[gen.pmax for gen in generators],
                rampratemin=[getattr(gen, 'rampratemin',
                                     None) for gen in generators],
                rampratemax=[getattr(gen, 'rampratemax',
                                     None) for gen in generators],
            )).T
            print 'generator limits\n', committed
        else:
            gens = filter(lambda gen:
                          gen.is_controllable and gen.initial_status == 1,
                          self.generators())
            committed = pd.Series(dict(
                Pmin=sum(gen.pmin for gen in gens),
                Pmax=sum(gen.pmax for gen in gens),
                rampratemin=pd.Series(gen.rampratemin for gen in gens).sum(),
                rampratemax=pd.Series(gen.rampratemax for gen in gens).sum(),
            ))
            print 'total committed\n', committed

        if resolve_sln:
            print 'expected status'
            if len(resolve_sln.generators_status.columns) < 5:
                print(resolve_sln.generators_status)
            else:
                print(resolve_sln.generators_status.sum(axis=1))
            ep = resolve_sln.generators_power
            ep['net_required'] = scheduled.net_required.values
            print('expected power')
            if len(ep.columns) < 5:
                print(ep)
            else:
                print(ep.sum(axis=1))
        else:
            print 'initial_status\n'
            print pd.Series([gen.initial_status for gen in self.generators()])

        return scheduled, committed
