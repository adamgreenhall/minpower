import pandas as pd
import numpy as np
from config import user_config
from commonscripts import update_attributes, hours, set_trace
from optimization import value
from generators import Generator
from schedule import is_init, get_tPrev
import bidding

default_max=dict(
    flow= 1e9,
    elevation= 1e6,
    volume= 1e9)

class HydroGenerator(Generator):
    """
    A hydro plant model, including the upstream reservoir.
    Has constraints and variables which are significantly
    different from conventional generators.
    """
    def __init__(self,
            name, bus='system', index=None,
            downstream_reservoir=None,
            delay_downstream=0,
            elevation_min=0, elevation_max=None,
            outflow_min=0, outflow_max=None,
            spill_min=0, spill_max=None,
            pmin=0, pmax=None,
            rampratemin=None, rampratemax=None,
            elevation_ramp_min=None, elevation_ramp_max=None,
            outflow_ramp_min=None, outflow_ramp_max=None,
            elevation_final=None,
            inflow_schedule=None,
            volume_to_forebay_elevation=None,
            flow_to_tailwater_elevation=None,
            head_to_production_coefficient=None
            ):
        update_attributes(self, locals())  # load in inputs

        self.upstream_reservoirs = []
        self.is_hydro = True
        self.is_controllable = True
        self.is_stochastic = False

        self.build_pw_models()
        if self.outflow_max is None:
            try:
                self.outflow_max = self.flow_to_tailwater_elevation.indvar.max()
            except AttributeError:
                self.outflow_max = default_max['flow']
        self.init_optimization()

    def set_initial_condition(self,
        power=0, elevation=0, outflow=0, spill=0):
        self.initial = dict(
            power=power,
            elevation=elevation,
            outflow=outflow,
            spill=spill)
        self.initial_status = True

    def getstatus(self, tend, *a, **kw):
        return dict(
            status=self.status(tend),
            power= value(self.power(tend)),
            elevation= value(self.elevation(tend)),
            outflow= value(self.outflow(tend)),
            spill= value(self.spill(tend)),
            )

    def _set_derived_init(self):
        '''after models have been built, set derived initial vars'''
        self.initial['head'] = \
            self.initial['elevation'] - \
            self.PWmodels['flow_to_tailwater_elevation'].output_true(
                self.initial['outflow'] + \
                self.initial['spill']
                )
        #self.power_production_coef = self.PWmodels[
        #    'head_to_production_coefficient'].output_true(
        #    self.initial['head'])

    def build_pw_models(self):
        '''
        take sets of PWL points and make models for the
        three different hydro PWL functions.
        '''
        def pw_or_poly(obj, input_variable, output_name='cost', **kwds):
            params = dict(
                input_variable=input_variable,
                output_name=output_name,
                )
            params.update(kwds)
            if type(obj) == pd.DataFrame:
                # PWL model
                params.update(dict(
                    bid_points= obj,
                    polynomial= None))
            else:
                cost_coeffs = bidding.parse_polynomial(obj)
                params.update(dict(
                    polynomial= cost_coeffs,
                    constant_term= cost_coeffs[0],
                    num_breakpoints= user_config.breakpoints))
            return params


        self.PWparams = dict(
            volume_to_forebay_elevation= pw_or_poly(
                self.volume_to_forebay_elevation,
                self.volume,
                output_name='el_fb'),
            flow_to_tailwater_elevation= pw_or_poly(
                self.flow_to_tailwater_elevation,
                self.net_outflow,
                output_name= 'el_tw'),
            #head_to_production_coefficient=pw_or_poly(
            #    self.head_to_production_coefficient,
            #    self.head,
            #    output_name= 'prod_coeff',
            #    pw_repn='SOS2',
            #    pw_constr_type='UB'
            #    ),
        )
        
        prod = dict(
                inputA=self.head,
                inputB=self.outflow,
                pointsA=self.head_to_production_coefficient.indvar.values,
                pointsB=np.linspace(
                    self.flow_to_tailwater_elevation.indvar.min(),
                    self.flow_to_tailwater_elevation.indvar.max(),
                    user_config.breakpoints),
                output_name='power_production',
                output_var=self.power,
                )        
        index = pd.MultiIndex.from_arrays([
            np.repeat(prod['pointsA'], len(prod['pointsB'])),
            np.tile(prod['pointsB'], len(prod['pointsA']))],
            names=['pointsA', 'pointsB'])            
        prod['pointsOut'] = pd.Series([
            outflow * self.head_to_production_coefficient.set_index('indvar').ix[head, 'depvar']
            for head, outflow in index], index=index, name='output')
        self.PWparams['head_outflow_to_production'] = prod
        
        for k in self.PWparams.keys():
            self.PWparams[k].update(dict(
                owner= self,
                status_variable= self.status,
                ))
        
    def power(self, time=None, scenario=None):
        if time is not None and is_init(time):
            return self.initial['power']
        return self.get_var('power', time, scenario)

    def outflow(self, time=None, scenario=None):
        if time is not None and is_init(time):
            return self.initial['outflow']
        return self.get_var('outflow', time, scenario)

    def elevation(self, time=None, scenario=None):
        if time is not None and is_init(time):
            return self.initial['elevation']
        return self.get_var('elevation', time, scenario)

    def volume(self, time=None, scenario=None):
        return self.get_var('volume', time, scenario)

    def spill(self, time=None, scenario=None):
        return self.get_var('spill', time, scenario)

    def head(self, time=None, scenario=None):
        return self.get_var('head', time, scenario)

    def net_outflow(self, time=None, scenario=None):
        return self.get_var('net_outflow', time, scenario)

    def net_flow(self, time=None, scenario=None):
        return self.get_var('net_flow', time, scenario)

    def net_inflow(self, t, times, other_hydro):
        return self.inflow_schedule[times[t]] + sum(
            self.upstream_unit_outflow(
                times, t, other_hydro[r]) for r in self.upstream_reservoirs)

    def upstream_unit_outflow(self, times, t, upstream_gen):
        outflow_time = times.times[t] - \
            hours(upstream_gen.delay_downstream)
        if times.is_hourly:
            # HACK: use hour start
            outflow_time = pd.Timestamp(outflow_time) + \
                pd.DateOffset(minute=0)

        if outflow_time < times.Start:
            out = upstream_gen.initial['outflow'] + \
                  upstream_gen.initial['spill']
        else:
            tm_up = times[times.times.indexer_at_time(outflow_time)[0]]
            out = upstream_gen.net_outflow(tm_up)
        return out

    def create_variables(self, times):
        self.add_variable('power', index=times.set,
            low=self.pmin, high=self.pmax)
        self.add_variable('elevation', index=times.set,
            low=self.elevation_min, high=self.elevation_max)
        self.add_variable('volume', index=times.set,
            low=0, high=default_max['volume'])
        self.add_variable('outflow', index=times.set,
            low=self.outflow_min, high=self.outflow_max)

        self.add_variable('net_outflow', index=times.set, low= 0, high= default_max['flow'])
        self.add_variable('net_flow', index=times.set,
            low= -1*default_max['flow'],
            high= default_max['flow'])
        try:
            max_head = self.head_to_production_coefficient.indvar.max()
        except AttributeError:
            max_head = default_max['elevation']
        self.add_variable('head', index=times.set,
            low=0,
            high=max_head)
        self.add_variable('spill', index=times.set,
            low=self.spill_min, high=self.spill_max)
        def bid_maker(key): 
            return bidding.TwoVarPW if \
                key == 'head_outflow_to_production' else bidding.Bid
        self.PWmodels = {
            key: bid_maker(key)(times=times, **self.PWparams[key])
            for key in self.PWparams.keys()}
        self._set_derived_init()

    def create_constraints(self, times):
        hydro_gens = filter(
            lambda gen: getattr(gen,'is_hydro', False),
            self._parent_problem().generators())

        # initial and final elevations
        if self.elevation_final is not None:
            self.add_constraint('elevation final', times.last(),
                self.elevation(times.last()) >= self.elevation_final)

        for t, time in enumerate(times):
            # network balance
            if t < len(times) - 1:
                self.add_constraint('water balance', time,
                    self.volume(times[t+1]) - self.volume(time) == \
                    self.net_flow(time))

            self.add_constraint('modeled net flow', time,
                self.net_flow(times[t]) == \
                self.net_inflow(t, times, hydro_gens) - \
                self.net_outflow(time))


        self.add_constraint_set('modeled elevation', times.set, lambda model, t:
            self.elevation(t) == self.PWmodels['volume_to_forebay_elevation'].output(t))
        self.add_constraint_set('power production', times.set, lambda model, t:
            self.power(t) <= \
            # self.power_production_coef * self.outflow(t) # based on initial head
            #self.PWmodels['head_to_production_coefficient'].output(t) * self.outflow(t)
            self.PWmodels['head_outflow_to_production'].output(t)
            )

        self.add_constraint_set('modeled head', times.set, lambda model, t:
            self.head(t) == self.elevation(t) - \
            self.PWmodels['flow_to_tailwater_elevation'].output(t))

        self.add_constraint_set('modeled net outflow', times.set,
            lambda model, t:
            self.net_outflow(t) == self.outflow(t) + self.spill(t))

        # ramping constraints
        self.add_ramp_constraints(self.power,
            self.rampratemin, self.rampratemax, times)
        self.add_ramp_constraints(self.elevation, 
            self.elevation_ramp_min, self.elevation_ramp_max, times)
        self.add_ramp_constraints(self.outflow, 
            self.outflow_ramp_min, self.outflow_ramp_max, times)

    def add_ramp_constraints(self, var, minlim, maxlim, times):
        name = var(None).name
        if minlim is not None:
            self.add_constraint_set('{} ramp limit low'.format(name), times.set,
            lambda model, t:
            var(t) - var(get_tPrev(t, model, times)) >= float(minlim[t]))
        #def max_lim_setter(model, t): 
        #    return var(t) - var(get_tPrev(t, model, times)) <= float(maxlim[t])
        if maxlim is not None:
            self.add_constraint_set('{} ramp limit high'.format(name), times.set,
            lambda model, t:
            var(t) - var(get_tPrev(t, model, times)) <= float(maxlim[t]))
        return
        
    def __str__(self):
        return 'h{ind}'.format(ind=self.index)

    def cost(self, *a, **k): return 0
    def operatingcost(self, *a, **k): return 0
    def incrementalcost(self, *a, **k): return 0
    def truecost(self, *a, **k): return 0
    def cost_first_stage(self, *a, **k): return 0
    def cost_second_stage(self, *a, **k): return 0
    def status(self, *a, **k): return True
    def cost_startup(self, *a, **k): return 0
    def cost_shutdown(self, *a, **k): return 0
    def getstatus(self, *a, **k): return {}
    

