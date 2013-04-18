from commonscripts import update_attributes, hours, set_trace
from generators import Generator
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
            outflow_initial=None,
            power_initial=0,
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
        if self.outflow_initial is None:
            self.outflow_initial = \
                (self.outflow_max - self.outflow_min) / 2.0

        self.build_pw_models()
        self.init_optimization()
    def build_pw_models(self):
        '''
        take sets of PWL points and make models for the 
        three different hydro PWL functions.
        '''
        self.PWparams = dict(
            flow_to_forebay_elevation= {
                'bid_points': self.flow_to_forebay_elevation,
                'input_variable': self.net_flow,
            },
            flow_to_tailwater_elevation={
                'bid_points': self.flow_to_forebay_elevation,
                'input_variable': self.net_outflow,
            },
            head_to_production_coefficient={
                'bid_points': self.head_to_production_coefficient,
                'input_variable': self.head,
            }       
        )
        for k in self.PWparams.keys():
            self.PWparams[k].update(dict(
                owner= self,
                status_variable= self.status,
                polynomial= None,
                ))
        
#    def outflow(self, time=None, scenario=None):
#        return self.get_variable('outflow', time,
#            scenario=scenario, indexed=True)

    def spill(self, time=None, scenario=None):
        return self.get_variable('spill', time,
            scenario=scenario, indexed=True)

    def elevation(self, time=None, scenario=None):
        return self.get_variable('elevation', time,
            scenario=scenario, indexed=True)

    def elevation_tailwater(self, time=None, scenario=None):
        return self.PWmodels['flow_to_tailwater_elevation'].output(time)

    def head(self, time=None, scenario=None):
        return self.elevation(time, scenario)\
            - self.elevation_tailwater(time, scenario)

    def net_outflow(self, time=None, scenario=None):
        return self.outflow(time, scenario)\
               + self.spill(time, scenario)

    def net_inflow(self, t, times, other_hydro):
        return self.inflow_schedule[times[t]] + sum(
            self.upstream_unit_outflow(
                times, t, other_hydro[r]) for r in self.upstream_reservoirs)

    def net_flow(self, time=None, scenario=None):
        return self.PWmodels['flow_to_forebay_elevation'].output(
            time, scenario)

    def elevation_change(self, t, times):
        '''change in elevation between t and t-1'''
        prev = self.elevation(times[t - 1]) if t > 1 else self.volume_initial
        return self.elevation(times[t]) - prev
        
    def upstream_unit_outflow(self, times, t, upstream_gen):
        outflow_time = times.times[t] - \
            hours(upstream_gen.delay_downstream)
        if outflow_time < times.Start:
            out = upstream_gen.outflow_initial + upstream_gen.spill_initial
        else:
            tm_up = times[times.times.indexer_at_time(outflow_time)[0]]
            out = upstream_gen.net_outflow(tm_up)
        return out
    
    def outflow(self, time):
        '''flow output through turbine'''
        return self.PWmodel['head_to_production_coefficient'].output(time) * self.power(time)

    def create_variables(self, times):
        self.add_variable('power', index=times.set,
            low=self.pmin, high=self.pmax)
        self.add_variable('elevation', index=times.set,
            low=self.elevation_min, high=self.elevation_max)
        self.add_variable('outflow', index=times.set,
            low=self.outflow_min, high=self.outflow_max)
        self.add_variable('spill', index=times.set,
            low=self.spill_min, high=self.spill_max)
        self.PWmodels = {
            key: bidding.Bid(times=times, **self.PWparams[key]) 
            for key in self.PWparams.keys()}

    def create_constraints(self, times):
        hydro_gens = filter(
            lambda gen: getattr(gen,'is_hydro', False), 
            self._parent_problem().generators())
        
        # initial and final volumes
        self.add_constraint('elevation final', times.last(), 
            self.elevation(times.last()) >= self.elevation_final)

        for t, time in enumerate(times):
            # network balance
            self.add_constraint('water balance', time,
                self.elevation_change(t, times) == \
                    self.net_inflow(t, times, hydro_gens) - \
                    self.net_outflow(time))
#            # production
#            self.add_constraint(
#                'outflow', time,
#                self.outflow(time) == self.outflow_modeled(time))


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
