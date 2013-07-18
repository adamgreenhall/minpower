import pandas as pd
import logging
from config import user_config
from commonscripts import update_attributes, bool_to_int, set_trace

from optimization import value, OptimizationObject
from schedule import is_init, get_tPrev

import bidding


class Generator(OptimizationObject):
    """
    A generator model.

    :param pmin: minimum real power
    :param pmax: maximum real power
    :param minuptime: min. time after commitment in on status (hours)
    :param mindowntime: min. time after de-commitment in off status (hours)
    :param rampratemax: max. positive change in real power over 1hr (MW/hr)
    :param rampratemin: max. negative change in real power over 1hr (MW/hr)
    :param startupramplimit: max. positive change in real power over the
        first hour after startup (MW/hr)
    :param shutdownramplimit: max. negative change in real power over the
        last hour before shutdown (MW/hr)
    :param costcurveequation: text describing a polynomial cost curve ($/MWh)
      see :meth:`~bidding.parsePolynomial` for more.
    :param heatratestring: text describing a polynomial heat rate curve (MBTU/MW).
        converts to cost curve when multiplied by fuelcost.
    :param fuelcost: cost of fuel ($/MBTU)
    :param startupcost: cost to commit ($)
    :param shutdowncost: cost to de-commit ($)
    :param mustrun: flag that forces commimtent to be on

    :param name: name of the generator
    :param index: numbering of the generator
    :param bus: bus name that the generator is connected to
    """

    def __init__(self, kind='generic',
                 pmin=0, pmax=500,
                 minuptime=0, mindowntime=0,
                 rampratemax=None, rampratemin=None,
                 costcurveequation='20P',
                 heatrateequation=None, fuelcost=1,
                 bid_points=None,
                 noloadcost=0,
                 startupcost=0, shutdowncost=0,
                 startupramplimit=None,
                 shutdownramplimit=None,
                 faststart=False,
                 mustrun=False,
                 name='', bus='system', index=None):

        update_attributes(self, locals())  # load in inputs

        # The formulation below requires that startup ramp limits are set.
        # The defaults are the normal ramp rate limits,
        # unless Pmin so high and Rmin/max small that startup is infeasible.
        # In that case the default is Pmin.

        if (self.startupramplimit is None) and (self.rampratemax is not None):
            if self.pmin > self.rampratemax:
                self.startupramplimit = self.pmin
            else:
                self.startupramplimit = self.rampratemax

        if (self.shutdownramplimit is None) and (self.rampratemin is not None):
            if (-1 * self.pmin < self.rampratemin):
                self.shutdownramplimit = -1 * self.pmin
            else:
                self.shutdownramplimit = self.rampratemin

        self.fuelcost = float(fuelcost)

        self.is_controllable = True
        self.is_stochastic = False
        self.commitment_problem = True
        self.build_cost_model()
        self.init_optimization()
        
        self.always_on = self.noloadcost == 0 and \
            self.startupcost == 0 and self.shutdowncost == 0

    def power(self, time=None, scenario=None):
        '''real power output at time'''
        if time is not None and is_init(time):
            return self.initial_power
        else:
            return self.get_variable('power', time, scenario=scenario, indexed=True)

    def power_available(self, time=None, scenario=None):
        '''power availble (constrained by pmax, ramprate, ...) at time'''
        if time is not None and is_init(time):
            return self.initial_power

        var_name = 'power_available' if self.commitment_problem \
            and self.reserve_required else 'power'
        return self.get_variable(var_name, time, scenario=scenario, indexed=True)

    def status(self, time=None, scenario=None):
        '''on/off status at time'''
        if self.always_on:
            return 1
        elif self.commitment_problem or user_config.dispatch_decommit_allowed:
            if time is not None and is_init(time):
                return self.initial_status
            else:
                return self.get_variable('status', time, scenario=scenario, indexed=True)
        else:
            return 1

    def status_change(self, t, times):
        '''is the unit changing status between t and t-1'''
        if t > 0:
            previous_status = self.status(times[t - 1])
        else:
            previous_status = self.initial_status
        return self.status(times[t]) - previous_status


    def cost(self, time, scenario=None, evaluate=False):
        '''total cost at time (operating + startup + shutdown)'''
        return self.operatingcost(time, scenario, evaluate) + \
            self.cost_startup(time, scenario, evaluate) + \
            self.cost_shutdown(time, scenario, evaluate)

    def penalty(self, time, scenario=None, evaluate=False):
        '''total penalty at time'''
        return 0

    def cost_startup(self, time, scenario=None, evaluate=False):
        if self.startupcost == 0 or not self.commitment_problem:
            return 0
        else:
            c = self.get_variable(
                'startupcost', time, scenario=scenario, indexed=True)
            return c if not evaluate else value(c)

    def cost_shutdown(self, time, scenario=None, evaluate=False):
        if self.shutdowncost == 0 or not self.commitment_problem:
            return 0
        else:
            c = self.get_variable(
                'shutdowncost', time, scenario=scenario, indexed=True)
            return c if not evaluate else value(c)

    def operatingcost(self, time=None, scenario=None, evaluate=False):
        '''cost of real power production at time (based on bid model approximation).'''
        return self.bids.output(time, scenario=scenario, evaluate=evaluate)

    def truecost(self, time, scenario=None):
        '''exact cost of real power production at time (based on exact bid polynomial).'''
        return value(self.status(time, scenario)) * self.bids.output_true(self.power(time, scenario))

    def incrementalcost(self, time, scenario=None):
        '''change in cost with change in power at time (based on exact bid polynomial).'''
        return self.bids.output_incremental(self.power(time, scenario)) if value(self.status(time, scenario)) else None

    def cost_first_stage(self, times):
        return sum(self.cost_startup(time) + self.cost_shutdown(time) for time in times)

    def cost_second_stage(self, times):
        return sum(self.operatingcost(time) for time in times)

#  Added penalties to influence solution (not added to costs but are part of objective function)
    def penalties(self, times):
        '''total penalties at time (ramping(power) + Dump + etc)'''
        return sum(self.penalty(time) for time in times)

    def gethrsinstatus(self, times, stat):
        if not self.is_controllable:
            return 0

        end_status = stat.ix[stat.index[-1]]

        if (stat == end_status).all():
            intervals = len(stat)
            hrs = intervals * times.intervalhrs
            if self.initial_status == end_status:
                hrs += self.initial_status_hours
        else:
            noneq = stat[stat != end_status]
            if len(noneq) == 0:
                intervals = 0
            else:
                intervals = len(stat.ix[noneq.index[-1]:]) - 1

            hrs = intervals * times.intervalhrs

        return hrs

    def set_initial_condition(self, power=None,
        status=True, hoursinstatus=100):
        if power is None:
            # set default power as mean output
            power = (self.pmax - self.pmin) / 2
        if pd.isnull(power):
            raise ValueError('inital power cannot be null')
        self.initial_status = bool_to_int(status)
        self.initial_power = float(power * self.initial_status)  # note: this eliminates ambiguity of off status with power non-zero output
        self.initial_status_hours = hoursinstatus
        
        if not self.initial_status:
            self.always_on = False

    def get_final_condition(self, times):
        tFinal = times.last()
        status = pd.Series(
            [value(self.status(t)) for t in times], index=times.times)
        return dict(
               power=value(self.power(tFinal)),
               status=value(self.status(tFinal)),
               hoursinstatus=self.gethrsinstatus(times, status))

    def build_cost_model(self):
        '''
        parse the coefficients for the polynomial bid curve
        or custom bid points definition
        '''
        bid_params = dict(
            owner=self,
            input_variable=self.power,
            min_input=self.pmin,
            max_input=self.pmax,
            status_variable=self.status
        )

        if self.bid_points is None:
            # polynomial specification
            self.cost_breakpoints = user_config.breakpoints
            if getattr(self, 'heatrateequation', None):
                self.cost_coeffs = [self.fuelcost * coef
                                    for coef in bidding.parse_polynomial(self.heatrateequation)]
            else:
                self.cost_coeffs = bidding.parse_polynomial(
                    self.costcurveequation)

            bid_params['polynomial'] = self.cost_coeffs
            bid_params['constant_term'] = self.cost_coeffs[0]
            bid_params['num_breakpoints'] = self.cost_breakpoints
            if self.noloadcost != 0:
                raise ValueError('no load cost should be defined as part of the polynomial.')

        else:
            # do some simple validation and delay construction to bidding
            # object
            min_power_bid = self.bid_points.power.min()
            max_power_bid = self.bid_points.power.max()

            if min_power_bid > self.pmin:  # pragma: no cover
                self.pmin = min_power_bid
                logging.warning('{g} should have a min. power bid ({mpb}) <= to its min. power limit ({mpl})'.format(g=str(self), mpb=min_power_bid, mpl=self.pmin))

            if max_power_bid < self.pmax:  # pragma: no cover
                self.pmax = max_power_bid
                logging.warning('{g} should have a max. power bid ({mpb}) >= to its max. power limit ({mpl})'.format(g=str(self), mpb=max_power_bid, mpl=self.pmax))

            bid_params['polynomial'] = None
            bid_params['bid_points'] = self.bid_points
            bid_params['constant_term'] = self.noloadcost

        self.bid_params = bid_params

    def create_variables(self, times):
        '''
        Create the optimization variables for a generator over all times.
        Also create the :class:`bidding.Bid` objects and their variables.
        '''
        self.commitment_problem = len(times) > 1
        self.add_variable('power', index=times.set, low=0, high=self.pmax)

        if self.commitment_problem or user_config.dispatch_decommit_allowed \
            and not self.always_on:
            self.add_variable('status', index=times.set, kind='Binary',
                              fixed_value=1 if self.mustrun else None)

        if self.commitment_problem:
            # power_available exists for easier reserve requirement
            self.reserve_required = self._parent_problem().reserve_required
            if self.reserve_required:
                self.add_variable(
                    'power_available', index=times.set, low=0, high=self.pmax)
            if self.startupcost > 0:
                self.add_variable('startupcost', index=times.set,
                                  low=0, high=self.startupcost)
            if self.shutdowncost > 0:
                self.add_variable('shutdowncost', index=times.set,
                                  low=0, high=self.shutdowncost)

        self.bids = bidding.Bid(times=times, **self.bid_params)
        return

    def create_objective(self, times):
        return sum(self.cost(time) + self.penalty(time) for time in times)

    def create_constraints(self, times):
        '''create the optimization constraints for a generator over all times'''
        def roundoff(n):
            m = int(n)
            if n != m:  # pragma: no cover
                raise ValueError('min up/down times must be integer number of intervals, not {}'.format(n))
            return m

        if self.commitment_problem:
            # set initial and final time constraints
            tInitial = times.initialTimestr
            tEnd = len(times)
            if self.minuptime > 0:
                up_intervals_remaining = roundoff((self.minuptime - self.initial_status_hours) / times.intervalhrs)
                min_up_intervals_remaining_init = int(
                    min(tEnd, up_intervals_remaining * self.initial_status))
            else:
                min_up_intervals_remaining_init = 0
            if self.mindowntime > 0:
                down_intervals_remaining = roundoff((self.mindowntime - self.initial_status_hours) / times.intervalhrs)
                min_down_intervals_remaining_init = int(min(tEnd, down_intervals_remaining * (self.initial_status == 0)))
            else:
                min_down_intervals_remaining_init = 0
            # initial up down time
            if min_up_intervals_remaining_init > 0:
                self.add_constraint('minuptime', tInitial, 0 >= sum([(1 - self.status(times[t])) for t in range(min_up_intervals_remaining_init)]))
            if min_down_intervals_remaining_init > 0:
                self.add_constraint('mindowntime', tInitial, 0 == sum([self.status(times[t]) for t in range(min_down_intervals_remaining_init)]))

#            # initial ramp rate
#            if self.rampratemax is not None:
#                if self.initial_power + self.rampratemax < self.pmax:
#                    E = self.power(
#                        times[0]) - self.initial_power <= self.rampratemax
#                    self.add_constraint('ramp lim high', tInitial, E)

#            if self.rampratemin is not None:
#                if self.initial_power + self.rampratemin > self.pmin:
#                    E = self.rampratemin <= self.power(
#                        times[0]) - self.initial_power
#                    self.add_constraint('ramp lim low', tInitial, E)

            # calculate up down intervals
            min_up_intervals = roundoff(self.minuptime / times.intervalhrs)
            min_down_intervals = roundoff(self.mindowntime / times.intervalhrs)

            # reserve
            if self.reserve_required:
                def reserve_req(model, t):
                    return self.power(t) <= self.power_available(t)
                self.add_constraint_set('max gen power avail', times.set, reserve_req)

            # ramping power
            if self.rampratemax is not None:
                def ramp_max(model, t):
                    tPrev = get_tPrev(t, model, times)
                    ramp_limit = self.rampratemax * self.status(tPrev)
                    if self.startupramplimit is not None:
                        ramp_limit += self.startupramplimit * (
                            self.status(t) - self.status(tPrev))
                        # + self.pmax * (1 - self.status(times[t]))
                    return self.power_available(t) - self.power(tPrev) <= ramp_limit

                self.add_constraint_set('ramp limit high', times.set, ramp_max)

#               # EQ19 from Carrion and Arroyo - has a conflicting
#               # definition of shutdown power, available after shutdown hour?
#                if self.shutdownramplimit is not None:
#                    # if shutting down, available power must be reduced
#                    self.add_constraint('ramp lim high shutdown', time,
#                        self.power_available(times[t-1]) <= self.pmax * self.status(time) + \
#                        self.shutdownramplimit * -1 * self.status_change(t, times)
#                        )


            if self.rampratemin is not None:
                def ramp_min(model, t):
                    tPrev = get_tPrev(t, model, times)
                    ramp_limit = self.rampratemin * self.status(t)
                    # + self.pmax * (1 - self.status(times[t-1]))
                    if self.shutdownramplimit is not None:
                        ramp_limit += self.shutdownramplimit * \
                            (-1 * (self.status(t) - self.status(tPrev)))

                    return ramp_limit <= self.power_available(t) - self.power(tPrev)
                self.add_constraint_set('ramp limit low', times.set, ramp_min)

            # start up and shut down costs
            if self.startupcost > 0:
                def startupcostmin(model, t):
                    tPrev = get_tPrev(t, model, times)
                    return self.cost_startup(t) >= self.startupcost * (
                        self.status(t) - self.status(tPrev))
                self.add_constraint_set('startup cost min', times.set, startupcostmin)

                # these tightening constraints make stochastic problems take a very long time
#                def startupcostmax(model, t):
#                    return self.cost_startup(t) <= self.startupcost * self.status(t)
#                self.add_constraint_set('startup cost max', times.set, startupcostmax)
#
#                def startupcostmax_prev(model, t):
#                    tPrev = get_tPrev(t, model, times)
#                    return self.cost_startup(t) <= self.startupcost * (1 - self.status(tPrev))
#                self.add_constraint_set('startup cost max prev', times.set, startupcostmax_prev)

            if self.shutdowncost > 0:
                def shutdowncost(model, t):
                    tPrev = get_tPrev(t, model, times)
                    return self.cost_shutdown(t) >= self.shutdowncost * -1 * (self.status(t) - self.status(tPrev))
                self.add_constraint_set('shutdown cost', times.set, shutdowncost)

            # note: costs must be >= constraints
            # for very large problems with >= constraints,
            # the solver may not always force the costs down to their minimum
            # however, the == formulation is incorrect and will not allow
            # unit shutdowns if the unit has a startup cost
            # solution is to use the min and max constraints together.

            # TODO: convert these to constraint list form
            for t, time in enumerate(times):

                # min up time
                if t >= min_up_intervals_remaining_init and self.minuptime > 0:
                    no_shut_down = range(t, min(tEnd, t + min_up_intervals))
                    min_up_intervals_remaining = min(tEnd - t, min_up_intervals)
                    E = sum([self.status(times[s]) for s in no_shut_down]) >= min_up_intervals_remaining * self.status_change(t, times)
                    self.add_constraint('min up time', time, E)
                # min down time
                if t >= min_down_intervals_remaining_init and self.mindowntime > 0:
                    no_start_up = range(t, min(tEnd, t + min_down_intervals))
                    min_down_intervals_remaining = min(
                        tEnd - t, min_down_intervals)
                    E = sum([1 - self.status(times[s]) for s in no_start_up]) >= min_down_intervals_remaining * -1 * self.status_change(t, times)
                    self.add_constraint('min down time', time, E)



        # min/max power limits
        # these always apply (even if not a UC problem)
        if self.pmin > 0:
            def min_power(model, t):
                return self.power(t) >= self.status(t) * self.pmin
            self.add_constraint_set('min gen power', times.set, min_power)

        def max_power(model, t):
            return self.power_available(t) <= self.status(t) * self.pmax
        self.add_constraint_set('max gen power', times.set, max_power)

        return

    def __str__(self):
#  Prefer more descriptive names, implemented change assumes names are always set.  The former 
#      might be safer
#        return 'g{ind}'.format(ind=self.index)
#        return 'g{ind}-{name}'.format(name=self.name,ind=self.index)
        return self.name


class Generator_nonControllable(Generator):
    """
    A generator with a fixed schedule.
    """
    def __init__(self,
                 schedule=None,
                 fuelcost=1,
                 costcurveequation='0',
                 bid_points=None,
                 noloadcost=0,
                 mustrun=False,
                 faststart=False,
                 sheddingallowed=False,
                 pmin=0, pmax=None,
                 name='', index=None, bus='system', kind='wind',
                 observed_values=None,
                 **kwargs):

        update_attributes(self, locals())  # load in inputs
        self.is_controllable = False
        self.startupcost = 0
        self.shutdowncost = 0
        self.fuelcost = float(fuelcost)
        self.build_cost_model()
        self.init_optimization()
        self.is_stochastic = False
        self.shedding_mode = sheddingallowed and user_config.economic_wind_shed

    def power(self, time, scenario=None):
        if self.shedding_mode:
            power = self.get_variable('power_used', time,
                                      scenario=scenario, indexed=True)
        else:
            power = self.power_available(time)
        return power

    def status(self, time=None, scenarios=None):
        return True

    def power_available(self, time=None, scenario=None):
        return self.get_parameter('power', time, indexed=True)

    def shed(self, time, scenario=None, evaluate=False):
        Pused = self.power(time, scenario=scenario)
        Pavail = self.power_available(time, scenario=scenario)
        if evaluate:
            Pused = value(Pused)
            Pavail = value(Pavail)
        return Pavail - Pused

    def set_initial_condition(self, power=0, status=1, hoursinstatus=0):  #pragma: no cover
        self.initial_power = power
        self.initial_status = status
        self.initial_status_hours = hoursinstatus

    def get_final_condition(self, times):
        tend = times.last()
        return dict(
            status=1,
            power=value(self.power(tend)),
            hoursinstatus=0)

    def create_variables(self, times):
        if self.shedding_mode:
            self.create_variables_shedding(times)
        self.add_parameter('power', index=times.set,
                           values=dict([(t, self.get_scheduled_ouput(t)) for t in times]))
        self.create_bids(times)

    def create_bids(self, times):
        self.bids = bidding.Bid(
            polynomial=self.cost_coeffs,
            owner=self,
            times=times,
            fixed_input=True,
            status_variable=lambda *args: True,
            input_variable=self.power
        )

    def create_variables_shedding(self, times):
        self.add_variable('power_used', index=times.set, low=0)

    def create_constraints(self, times):
        if self.shedding_mode:
            for time in times:
                self.add_constraint('max_power', time,
                                    self.power(time) <= self.power_available(time))

    def cost(self, time, scenario=None, evaluate=False):
        return self.operatingcost(time, scenario=scenario, evaluate=evaluate)

    def penalty(self, time, scenario=None, evaluate=False):
        return 0

    def operatingcost(self, time=None, scenario=None, evaluate=False):
        return self.bids.output(time, scenario=scenario) + \
            user_config.cost_wind_shedding * self.shed(time, scenario=scenario, evaluate=evaluate)

    def truecost(self, time, scenario=None):
        return self.cost(time)

    def incrementalcost(self, time, scenario=None):
        return self.bids.output_incremental(self.power(time))

    def cost_startup(self, time, scenario=None):
        return 0

    def cost_shutdown(self, time, scenario=None):
        return 0

    def cost_first_stage(self, times):
        return 0

    def cost_second_stage(self, times):
        return sum(self.cost(time) for time in times)

#  Added Penalties to influence solution
    def penalties(self, times):
        return sum(self.penalty(time) for time in times)

    def get_scheduled_ouput(self, time):
        return float(self.schedule.ix[time])

    def set_power_to_observed(self, times):
        power = self.power_available()
        for time in times:
            power[time] = self.observed_values[time]


class Generator_Stochastic(Generator_nonControllable):
    """
    A generator with a stochastic power output.
    """
    def __init__(self,
                 scenario_values=None,
                 costcurveequation='0',
                 fuelcost=1,
                 bid_points=None, noloadcost=0,
                 mustrun=False,
                 faststart=False,
                 pmin=0, pmax=None,
                 name='', index=None, bus='system', kind='wind',
                 observed_values=None,
                 schedule=None,
                 sheddingallowed=False,
                 **kwargs):
        update_attributes(self, locals())  # load in inputs
        self.is_controllable = False

        self.is_stochastic = not \
            (user_config.perfect_solve or user_config.deterministic_solve)
        self.build_cost_model()
        self.init_optimization()
        self.startupcost = 0
        self.shutdowncost = 0
        self.fuelcost = float(fuelcost)
        self.shedding_mode = sheddingallowed and user_config.economic_wind_shed

    def power(self, time, scenario=None):
        return self.get_variable(
            'power_used' if self.shedding_mode else 'power',
            time=time, scenario=scenario, indexed=True)

    def power_available(self, time=None, scenario=None):
        return self.get_variable('power',
                                 time=time, scenario=scenario, indexed=True)

    def _get_scenario_values(self, times, s=0):
        # scenario values are structured as a pd.Panel
        # with axes: day, scenario, {prob, [hours]}
        # the panel has items which are dates
        return self.scenario_values[times.Start.date()]\
                .ix[s].drop('probability')\
                [range(len(times))]\
                .values.tolist()

    def _get_scenario_probabilities(self, times):
        # if any of the scenario values are defined, we want them
        return self.scenario_values[
            times.Start.date()].probability.dropna()

    def create_variables(self, times):
        if self.shedding_mode:
            self.create_variables_shedding(times)

        if self.is_stochastic:
            # initialize parameter set to first scenario value
            scenario_one = self._get_scenario_values(times, s=0)
            self.add_parameter('power', index=times.set, nochecking=True,
                values=dict(zip(times, scenario_one)))
        else:
            # set to forecast values
            self.add_parameter('power', index=times.set,
               values=dict([(t, self.get_scheduled_ouput(t)) for t in times]))

        self.create_bids(times)
        return
