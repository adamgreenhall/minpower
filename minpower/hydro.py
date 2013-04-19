import pandas as pd
from config import user_config
from commonscripts import update_attributes, hours, set_trace
from generators import Generator
from schedule import is_init
import bidding


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
            elevation_initial=0, elevation_final=None,
            outflow_initial=0,
            power_initial=0,
            spill_initial=0,
            inflow_schedule=None,
            flow_to_forebay_elevation=None,
            flow_to_tailwater_elevation=None,
            head_to_production_coefficient=None
            ):
        update_attributes(self, locals())  # load in inputs

        self.upstream_reservoirs = []
        self.is_hydro = True
        self.is_controllable = True
        self.is_stochastic = False
        self.initial_status = True

        self.build_pw_models()
        if self.outflow_max is None:
            try:
                self.outflow_max = self.flow_to_tailwater_elevation.indvar.max()
            except AttributeError:
                self.outflow_max = 1e9
        self.init_optimization()
    def build_pw_models(self):
        '''
        take sets of PWL points and make models for the
        three different hydro PWL functions.
        '''
        def pw_or_poly(obj, input_variable, output_name='cost'):
            params = dict(
                input_variable=input_variable,
                output_name=output_name,
                )
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
            flow_to_forebay_elevation= pw_or_poly(
                self.flow_to_forebay_elevation,
                self.net_flow,
                output_name='el_fb'),
            flow_to_tailwater_elevation= pw_or_poly(
                self.flow_to_forebay_elevation,
                self.net_outflow,
                output_name= 'el_tw'),
            head_to_production_coefficient=pw_or_poly(
                self.head_to_production_coefficient,
                self.head,
                output_name= 'prod_coeff')
        )
        for k in self.PWparams.keys():
            self.PWparams[k].update(dict(
                owner= self,
                status_variable= self.status,
                ))
    def power(self, time=None, scenario=None):
        if time is not None and is_init(time):
            return self.initial_power
        return self.get_var('power', time, scenario)

    def outflow(self, time=None, scenario=None):
        if time is not None and is_init(time):
            return self.initial_outflow
        return self.get_var('outflow', time, scenario)

    def elevation(self, time=None, scenario=None):
        if time is not None and is_init(time):
            return self.initial_elevation
        return self.get_var('elevation', time, scenario)

    def spill(self, time=None, scenario=None):
        return self.get_var('spill', time, scenario)

    def head(self, time=None, scenario=None):
        return self.get_var('head', time, scenario)

    def net_outflow(self, time=None, scenario=None):
        return self.get_var('outflow', time, scenario)

    def elevation_tailwater(self, time=None, scenario=None):
        return self.PWmodels['flow_to_tailwater_elevation'].output(time)

    def net_flow(self, time=None, scenario=None):
        return self.get_var('net_flow', time, scenario)

    def net_inflow(self, t, times, other_hydro):
        return self.inflow_schedule[times[t]] + sum(
            self.upstream_unit_outflow(
                times, t, other_hydro[r]) for r in self.upstream_reservoirs)

    def modeled_net_flow(self, t, times, other_hydro):
        return self.net_inflow(t, times, other_hydro) - \
               self.net_outflow(times[t])

    def elevation_change(self, t, times):
        '''change in elevation between t and t-1'''
        prev = self.elevation(times[t - 1]) if t > 1 else self.elevation_initial
        return self.elevation(times[t]) - prev

    def upstream_unit_outflow(self, times, t, upstream_gen):
        outflow_time = times.times[t] - \
            hours(upstream_gen.delay_downstream)
        if times.is_hourly:
            # HACK: use hour start
            outflow_time = pd.Timestamp(outflow_time) + \
                pd.DateOffset(minute=0)

        if outflow_time < times.Start:
            out = upstream_gen.outflow_initial + upstream_gen.spill_initial
        else:
            tm_up = times[times.times.indexer_at_time(outflow_time)[0]]
            out = upstream_gen.net_outflow(tm_up)
        return out

    def modeled_outflow(self, time, scenario=None):
        '''
        flow output through turbine as modeled by the
        head dependent production equation
        '''
        return self.PWmodels['head_to_production_coefficient'].output(
            time, scenario) * self.power(time, scenario)

    def modeled_head(self, time=None, scenario=None):
        return self.elevation(time, scenario)\
            - self.elevation_tailwater(time, scenario)

    def modeled_net_outflow(self, time=None, scenario=None):
        return self.outflow(time, scenario)\
               + self.spill(time, scenario)



    def create_variables(self, times):
        self.add_variable('power', index=times.set,
            low=self.pmin, high=self.pmax)
        self.add_variable('elevation', index=times.set,
            low=self.elevation_min, high=self.elevation_max)
        self.add_variable('outflow', index=times.set,
            low=self.outflow_min, high=self.outflow_max)

        self.add_variable('net_outflow', index=times.set,
            low= self.outflow_min + self.spill_min,
            # high= self.outflow_max + self.spill_max)
            )
        self.add_variable('net_flow', index=times.set,
            low=-1e9, high=1e9)
        try:
            max_head = self.head_to_production_coefficient.indvar.max()
        except AttributeError:
            max_head = 1e5
        self.add_variable('head', index=times.set,
            low=0,
            high=max_head)
        self.add_variable('spill', index=times.set,
            low=self.spill_min, high=self.spill_max)
        self.PWmodels = {
            key: bidding.Bid(times=times, **self.PWparams[key])
            for key in self.PWparams.keys()}

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
            self.add_constraint('water balance', time,
                self.elevation_change(t, times) == \
                    self.net_inflow(t, times, hydro_gens) - \
                    self.net_outflow(time))
            self.add_constraint('modeled net flow', time,
                self.net_flow(times[t]) == \
                self.modeled_net_flow(t, times, hydro_gens))

        self.add_constraint_set('modeled outflow', times.set, lambda model, t:
            self.outflow(t) == self.modeled_outflow(t))

        self.add_constraint_set('modeled head', times.set, lambda model, t:
            self.head(t) == self.modeled_head(t))

        self.add_constraint_set('modeled net outflow', times.set, lambda model, t:
            self.net_outflow(t) == self.modeled_net_outflow(t))


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
