import pandas as pd
import numpy as np
from config import user_config
from commonscripts import update_attributes, hours, set_trace
from optimization import value
from coopr import pyomo
from generators import Generator
from schedule import is_init, get_tPrev
import bidding

default_max=dict(
    flow= 1e6,
    elevation= 1e4,
    volume= 1e7)

units=dict(
    # flow [kcfs * 1hr] = change in volume [kcfs * hr]
    flow_to_volume_change= 1.0,
)


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
            elevation_min=0, elevation_max=default_max['elevation'],
            head_min=0, head_max=None,
            outflow_min=0, outflow_max=default_max['flow'],
            net_outflow_min=0, net_outflow_max=None,            
            spill_min=0, spill_max=default_max['flow'],
            pmin=0, pmax=None,
            volume_min=0, volume_max=default_max['volume'],
            rampratemin=None, rampratemax=None,
            elevation_ramp_min=None, elevation_ramp_max=None,
            outflow_ramp_min=None, outflow_ramp_max=None,
            net_outflow_ramp_min=None, net_outflow_ramp_max=None,            
            inflow_schedule=None,
            elevation_target_min_schedule=None,
            elevation_target_max_schedule=None,
            volume_to_forebay_elevation=None,
            flow_to_tailwater_elevation=None,
            head_to_production_coefficient=None
            ):
        update_attributes(self, locals())  # load in inputs

        self.upstream_reservoirs = []
        self.is_hydro = True
        self.is_controllable = True
        self.is_stochastic = False
        self.faststart = False
        
        self.model_production = 'production_coefficient' if user_config.solver == 'ipopt' else 'two_var'
        # production coeff. formulation is non-linear but that's fine for ipopt
        # "simplified" formulation is only good for feasiblity issues
        # "two_var" formulation is the general purpose form (but takes a long time)


        self.build_pw_models()
        if self.outflow_max is None:
            try:
                self.outflow_max = self.flow_to_tailwater_elevation.indvar.max()
            except AttributeError:
                self.outflow_max = default_max['flow']
        self.init_optimization()
        self.flow_history = pd.DataFrame()
        

    def set_initial_condition(self,
        power=0, elevation=0, outflow=0, spill=0, volume=0, head=0,
        status=1):
        self.initial = dict(
            power=power,
            elevation=elevation,
            outflow=outflow,
            volume=volume,
            head=head,
            spill=spill)
        self.initial['net_outflow'] = \
            self.initial['outflow'] + self.initial['spill']
        # compatability with generator
        self.initial_status = True
        self.initial_power = self.initial['power']
        self.initial_status_hours = 0

    def get_final_condition(self, times, *a, **kw):
        tend = times.last()
        varnms = [
            'status', 'power',
            'elevation', 'volume', 'head',
            'outflow', 'spill',
            ]
        final = pd.Series({nm: value(getattr(self, nm)(tend)) for nm in varnms}, name=self.name)

        if self.PWmodels['volume_to_forebay_elevation'].is_pwl:
            # get the actual value for elevation
            final['elevation'] = \
                self.PWmodels['volume_to_forebay_elevation'].output_true(final['volume'])
#            hydro_gens = self._parent_problem().get_generators_hydro()
#            net_flows = np.array([
#                float(self.net_inflow(t, times, hydro_gens)) - value(self.net_outflow(tm))
#                for t, tm in enumerate(times)])
            
        # linear HACK - correct to the true values for head 
        if self.model_production == 'simplified':
            final['head'] = final['elevation'] - \
                self.PWmodels['flow_to_tailwater_elevation'].output_true(
                    final['spill'] + final['outflow'])

        if (final.ix[['head', 'volume', 'elevation']] == 0).any():
            print 'warning: zero final conditions'
            print final
            # raise ValueError('final conditions are zero')
        return final.to_dict()

    def _set_derived_init(self):
        '''after models have been built, set derived initial vars'''
        self.initial['head'] = \
            self.initial['elevation'] - \
            self.PWmodels['flow_to_tailwater_elevation'].output_true(
                self.initial['outflow'] + \
                self.initial['spill']
                )

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

            # set the min/max input domain
            max_or_none = lambda series: series.max() if series is not None else None
            min_or_none = lambda series: series.min() if series is not None else None
            minval, maxval, minout, maxout = None, None, None, None
            
            if output_name == 'el_fb':
                # input is over volume
                minval = min_or_none(self.volume_min)
                maxval = max_or_none(self.volume_max)
                minout = min_or_none(self.elevation_min)
                maxout = max_or_none(self.elevation_max)                
            elif output_name == 'el_tw':
                # input is net outflow
                minval = min_or_none(self.net_outflow_min)
                maxval = max_or_none(self.net_outflow_max)
                if type(obj) == pd.DataFrame:
                    minout, maxout = obj.depvar.min(), obj.depvar.max()
            
#            if type(minval) == pd.Series or type(maxval) == pd.Series:
#                raise NotImplementedError('time varying curves not yet implemented')
            minmaxes = pd.Series(dict(
                min_input=minval, max_input=maxval,
                min_output=minout, max_output=maxout
                )).dropna()
                            
            params.update(minmaxes.to_dict())
            return params

        ftw_pw_type = 'EQ'
        try:
            ftw_pw_type = {'convex':'LB', 'concave':'UB'}[
                    bidding.pwl_convexity(self.flow_to_tailwater_elevation)]
        except AttributeError:
            pass 
        
        self.PWparams = dict(
            volume_to_forebay_elevation= pw_or_poly(
                self.volume_to_forebay_elevation,
                self.volume,
                output_name='el_fb',
                pw_constr_type='EQ',
                ),
                # in general these curves are concave (unlike cost curves)
                # and so setting the bounds as upper limits makes
                #  this a linear constraints problem
            flow_to_tailwater_elevation= pw_or_poly(
                self.flow_to_tailwater_elevation,
                self.net_outflow,
                output_name= 'el_tw',
                pw_constr_type= 'LB',
                force_no_build= (self.model_production == 'simplified'),
                # simplified problem doesn't use head or tailwater as
                #   optimization variables - don't build them                
                ),
        )
        
        self.PWparams['head_to_production_coefficient']= pw_or_poly(
            self.head_to_production_coefficient,
            self.head,
            output_name= 'production_coef',
            force_no_build= self.model_production != 'production_coefficient')

        if self.model_production == 'two_var':
            self._build_two_var_pw()
                                    
        for k in self.PWparams.keys():
            self.PWparams[k].update(dict(
                owner= self,
                status_variable= self.status,
                ))

    def _build_two_var_pw(self):
        # two variable PWL formulation
        pointsA = bidding._drop_dup_slopes(
            self.head_to_production_coefficient).indvar.values

        pointsB = [
            self.outflow_min.unique_val() or 0,
            self.outflow_max.unique_val() or default_max['flow']]

        index = pd.MultiIndex.from_arrays([
            np.repeat(pointsA, len(pointsB)),
            np.tile(pointsB, len(pointsA))],
            names=['pointsA', 'pointsB'])
        pointsOut = pd.Series([
            outflow * self.head_to_production_coefficient.set_index('indvar').ix[head, 'depvar']
            for head, outflow in index], index=index, name='output')
            
        self.PWparams['head_outflow_to_production'] = dict(
            inputA=self.head,
            inputB=self.outflow,
            pointsA=pointsA,
            pointsB=pointsB,
            pointsOut=pointsOut,
            output_name='power_production',
            output_var=self.power,
            owner= self,
            status_variable=self.status,
            )


    def rebuild_two_var_production_model(self):
        times = self._times
        self.model_production = 'two_var'
        self._remove_component('power production')  # remove quad. constraint
        self._build_two_var_pw()
        self.PWmodels['head_outflow_to_production'] = bidding.TwoVarPW(
            times=times, **self.PWparams['head_outflow_to_production'])


    def _var_get(self, varnm, time=None, scenario=None):
        if time is None:
            return self.get_var(varnm)
        elif is_init(time):
            return self.initial[varnm]
        else:
            return self.get_var(varnm, time, scenario)


    def power(self, *a, **k):
        return self._var_get('power', *a, **k)
    def outflow(self, *a, **k):
        return self._var_get('outflow', *a, **k)
    def elevation(self, *a, **k):
        return self._var_get('elevation', *a, **k)
    def volume(self, *a, **k):
        return self._var_get('volume', *a, **k)
    def spill(self, *a, **k):
        return self._var_get('spill', *a, **k)
    def head(self, *a, **k):
        return self._var_get('head', *a, **k)
    def net_outflow(self, *a, **k):
        return self._var_get('net_outflow', *a, **k)


    def net_inflow(self, t, times, other_hydro):
        if t == -1 and times.initialTime in self.flow_history.index \
            and 'incremental_inflows' in self.flow_history.columns:
            inflow_inc = self.flow_history.incremental_inflows.ix[times.initialTime]
        elif t == -1:
            # assume the inflow was the same in the initial hour
            inflow_inc = self.inflow_schedule[times[0]]
        else:
            inflow_inc = self.inflow_schedule[times[t]]
        inflow_upstream = sum(
            self.upstream_unit_outflow(
                times, t, other_hydro[r])
            for r in self.upstream_reservoirs)
            
        return inflow_inc + inflow_upstream

    def upstream_unit_outflow(self, times, t, upstream_gen):
        if not times.is_hourly:
            raise NotImplementedError('times currently must be hourly')

        # TODO - assumes hourly interval and rounds lag to nearest whole hour
        outflow_time = pd.Timestamp(times.times[0] + hours(t) - \
            hours(round(upstream_gen.delay_downstream)))

        if outflow_time < times.Start:
            if len(upstream_gen.flow_history): 
                net_outflow = upstream_gen.flow_history[['outflow', 'spill']].sum(axis=1)
                out = net_outflow.ix[outflow_time]
            else:
                # assume initial inflows have been the same at all times in the past
                out = upstream_gen.initial['outflow'] + \
                      upstream_gen.initial['spill']
        else:
            tm_up = times[times.times.indexer_at_time(outflow_time)[0]]
            out = upstream_gen.net_outflow(tm_up)
        return out

    def create_variables(self, times):
        self.add_variable('power', index=times.set,
            low=self.pmin, high=self.pmax, kind='NonNegativeReals')
        self.add_variable('elevation', index=times.set,
            low=self.elevation_min, high=self.elevation_max,
            kind='NonNegativeReals')
        self.add_variable('volume', index=times.set,
            low=0, high=default_max['volume'],
            kind='NonNegativeReals')
        self.add_variable('outflow', index=times.set,
            low=self.outflow_min, high=self.outflow_max,
            kind='NonNegativeReals')

        self.add_variable('net_outflow', index=times.set,
            low=self.net_outflow_min,
            high= default_max['flow'] or self.net_outflow_max,
            kind='NonNegativeReals')

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
        # HACK
        self._times = times
        
    def create_constraints(self, times):
        hydro_gens = filter(
            lambda gen: getattr(gen,'is_hydro', False),
            self._parent_problem().generators())

        # final elevations
        tLast = times.non_overlap().last()
        tLast_horizon = times.last()
        if self.elevation_target_min_schedule is not None:
            self.add_constraint('elevation final min', tLast,
                self.elevation(tLast) >= self.elevation_target_min_schedule.ix[tLast])
            if tLast_horizon != tLast:
                self.add_constraint('elevation final horizon min', tLast_horizon,
                    self.elevation(tLast_horizon) >= self.elevation_target_min_schedule.ix[tLast_horizon])

        if self.elevation_target_max_schedule is not None:
            self.add_constraint('elevation final max', tLast,
                self.elevation(tLast) <= self.elevation_target_max_schedule.ix[tLast])
            if tLast_horizon != tLast:
                self.add_constraint('elevation final horizon max', tLast_horizon,
                    self.elevation(tLast_horizon) <= self.elevation_target_min_schedule.ix[tLast_horizon])
        
        if len(self.flow_history) == 0: 
            # assume elevation was equal to initial at all past times
            # TODO - assumes hourly intervals
            elevation_history = pd.Series(self.initial['elevation'],
                index=pd.date_range(
                    times.times[0] - pd.DateOffset(hours=24),
                    times.times[0] - pd.DateOffset(hours=1),
                    freq='H'))
        else:
            elevation_history = self.flow_history.elevation

        def prev_elv(time, offset_hrs=24):
            # TODO - assumes hourly intervals
            tprev = time + pd.DateOffset(hours=offset_hrs)
            if tprev in elevation_history.index:
                return elevation_history[tprev]
            else:
                tidx = (times.times == tprev).tolist().index(True)
                return self.elevation(times[tidx])


        self.add_constraint_set('modeled elevation', times.set, lambda model, t:
            self.elevation(t) == self.PWmodels['volume_to_forebay_elevation'].output(t))



        self.add_constraint_set('modeled net outflow', times.set,
            lambda model, t:
            self.net_outflow(t) == self.outflow(t) + self.spill(t))

        
        if self.model_production == 'simplified':
            # this is a simplification of the HPC
            # where the production coefficient is based on the INITIAL head only
            # note that this means that head is not constrained in the problem
            
            hpc_val = self.PWmodels['head_to_production_coefficient'].output_true(
                self.initial['head'])
            self.add_constraint_set('power production', times.set,
                lambda model, t:
                self.power(t) == hpc_val * self.outflow(t))
        else:
            # otherwise head is modeled as a variable
            self.add_constraint_set('modeled head', times.set, lambda model, t:
                self.head(t) == self.elevation(t) - \
                self.PWmodels['flow_to_tailwater_elevation'].output(t))         

        if self.model_production == 'two_var': 
            pass 
            # the full two variable PWL modeling sets up constraints that bound
            #  power production relative to the curves created
        elif self.model_production == 'production_coefficient':
            # this formulation is quadratic and does not work with MIP solvers
            self.add_constraint_set('power production', times.set,
                lambda model, t:
                self.power(t) <= \
                    self.PWmodels['head_to_production_coefficient'].output(t) *\
                    self.outflow(t))
            
                
        for t, time in enumerate(times):
            tmstmp = times.times[t]
            tPrev = times[t-1]
            self.add_constraint('water balance', time,
                self.volume(time) - self.volume(tPrev) == \
                units['flow_to_volume_change'] * (self.net_inflow(t - 1, times, hydro_gens) - \
                self.net_outflow(tPrev)))

#            # elevation ramping constraints over 24hrs
#            if self.elevation_ramp_max is not None and \
#                not user_config.ignore_ramping_constraints:
#                self.add_constraint('elevation ramp max', time,
#                    self.elevation(time) - prev_elv(tmstmp, -24) \
#                    <= 24 * self.elevation_ramp_max[time])
#            if self.elevation_ramp_min is not None and \
#                not user_config.ignore_ramping_constraints:
#                self.add_constraint('elevation ramp min', time,
#                    self.elevation(time) - prev_elv(tmstmp, -24) \
#                    >= 24 * self.elevation_ramp_min[time])
                

        # ramping constraints
        if not user_config.ignore_ramping_constraints:
            self.add_ramp_constraints(self.power,
                self.rampratemin, self.rampratemax, times)
            self.add_ramp_constraints(self.net_outflow,
                self.net_outflow_ramp_min, self.net_outflow_ramp_max, times)
            self.add_ramp_constraints(self.outflow,
                self.outflow_ramp_min, self.outflow_ramp_max, times)
            self.add_ramp_constraints(self.elevation,
                self.elevation_ramp_min, self.elevation_ramp_max, times, include_t0=False)
                
    def add_ramp_constraints(self, var, minlim, maxlim, times, include_t0=True):
        name = var(None).name
        if minlim is not None:
            self.add_constraint_set('{} ramp limit low'.format(name), times.set,
            lambda model, t:
            var(t) - var(get_tPrev(t, model, times)) >= float(minlim[t]) 
            if (include_t0 or t != times[0]) else pyomo.Constraint.Feasible)
        if maxlim is not None:
            self.add_constraint_set('{} ramp limit high'.format(name), times.set,
            lambda model, t:
            var(t) - var(get_tPrev(t, model, times)) <= float(maxlim[t])
            if (include_t0 or t != times[0]) else pyomo.Constraint.Feasible)
            
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
