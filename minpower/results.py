"""
    Solution models, output, and display for power system
    optimization problems. Matplotlib and networkx are used for
    visualization.
"""
import yaml
import logging
from collections import OrderedDict

from commonscripts import *
from schedule import TimeIndex
from optimization import value,dual
import config,stochastic
from config import user_config

for_publication=True

try:
    import matplotlib
    import matplotlib.pyplot as plot
    do_plotting=True
    #prettify plots
    plot.rc("xtick", direction="out")
    plot.rc("ytick", direction="out")
    plot.rc("ytick",labelsize='small')
    plot.rc("xtick",labelsize='small')
    plot.rc("legend",fancybox=True)
    if for_publication:
        plot.rc("font",size=16)
        plot.rc("font",family="serif")
except ImportError:
    logging.warning("Can't import matplotlib -- skipping plotting.")
    do_plotting=False

import pandas


def full_filename(filename):
    if user_config.output_prefix:
        filename = '{}-{}'.format(os.getpid(), filename)
    return joindir(user_config.directory, filename)

def classify_problem(times,power_system):
    '''
    Classify the type of problem: ED, OPF, UC, or SCUC.

    :param times: a :class:`~schedule.Timelist` object
    :param power_system: a :class:`~powersystems.PowerSystem` object
    '''
    if not power_system.lines and len(times)==1: kind='ED'
    elif len(times)==1: kind='OPF'
    elif not power_system.lines: kind='UC'
    else: kind='SCUC'

    if any(getattr(g,'is_stochastic',False) for g in power_system.generators()): kind='stochastic_'+kind
    return kind

def make_solution(power_system,times,**kwargs):
    '''
    Create a :class:`solution.Solution` object for a power system over times.

    :param times: a :class:`~schedule.Timelist` object
    :param power_system: a :class:`~powersystems.PowerSystem` object
    '''
    problem_type=dict(
        ED=Solution_ED,
        OPF=Solution_OPF,
        UC=Solution_UC,
        SCUC=Solution_SCUC,
        stochastic_UC=Solution_Stochastic_UC
        )
    kind=classify_problem(times,power_system)
    return problem_type[kind](power_system,times,**kwargs)

def make_multistage_solution(power_system, stage_times, stage_solutions):
    '''Create a multi stage solution object.'''
    if power_system.lines: logging.warning('no visualization for multistage SCUC yet')
    klass = MultistageStandalone if getattr(stage_solutions, 'path', False) else Solution_UC_multistage
    return klass(power_system, stage_times, stage_solutions)

class Solution(object):
    '''
    Solution information template for a power system over times.
    Each problem type has its own class for visualization and
    spreadsheet output, e.g. :class:`~solution.Solution_ED`.
    '''
    def __init__(self,power_system,times,datadir='.', is_stochastic=False):
        update_attributes(self,locals())
        self._get_problem_info()
        self._get_costs()
        self._get_prices()
        self._get_outputs()
    def _get_problem_info(self):
        self.solve_time  =self.power_system.solution_time
        self.objective  =float(value(self.power_system.objective))
    def _get_outputs(self):
        times_to_store = self.times.non_overlap()

        self.generators_power = gen_time_dataframe(
            self.generators(),
            times_to_store,
            values=[self.get_values('generators','power',time) for time in times_to_store]
            )
        self.generators_status = gen_time_dataframe(
            self.generators(),
            times_to_store,
            values=[self.get_values('generators','status',time) for time in times_to_store]
            )
        self.generators_status = self.generators_status.astype(int)
        return


    def _get_costs(self):
        generators=self.generators()
        times=self.times.non_overlap()
        gen_fuel_costs_pwlmodel   = [[value(gen.operatingcost(t,evaluate=True)) for t in times] for gen in generators]
        gen_fuel_costs_polynomial = [[gen.truecost(t) for t in times] for gen in generators]
        self.totalcost_generation = sum(flatten([[float(gen.cost(t,evaluate=True)) for t in times] for gen in generators]))
        self.fuelcost_generation=float(sum( c for c in flatten(gen_fuel_costs_pwlmodel) ))
        self.fuelcost_true_generation=float(sum( c for c in flatten(gen_fuel_costs_polynomial) ))
        self.load_shed_timeseries = Series(
            [sum(load.shed(t,evaluate=True) for load in self.loads()) for t in times],
            index = times.strings.index)
        self.load_shed = sum( sum(load.shed(t,evaluate=True) for load in self.loads()) for t in times )
        self._get_cost_error()
    def _get_cost_error(self):
        try: self.costerror=abs(self.fuelcost_generation-self.fuelcost_true_generation)/self.fuelcost_true_generation
        except ZeroDivisionError: self.costerror=0
    def _get_prices(self):
        self.lmps={}
        self.line_prices={}
        for t in self.times:
            self.lmps[str(t)]=[bus.price(t) for bus in self.buses()]
            self.line_prices[str(t)]=[line.price(t) for line in self.lines()]

    def buses(self): return self.power_system.buses
    def lines(self): return self.power_system.lines
    def generators(self): return self.power_system.generators()
    def loads(self): return flatten( [[ld for ld in bus.loads] for bus in self.buses()] )
    def get_values(self,kind='generators',attrib='power',time=None):
        '''Get the attributes of all objects of a certain kind at a given time.'''
        method={'generators':self.generators,'loads':self.loads,'lines':self.lines,'buses':self.buses}
        if time is not None: return [value(getattr(obj, attrib)(time)) for obj in method[kind]()]
        else: return [value(getattr(obj, attrib)) for obj in method[kind]()]

    def savevisualization(self,filename=None):
        '''Save the visualization to a file'''
        if filename is None: plot.show()
        else: plot.savefig(filename,bbox_inches='tight')
        plot.close()
    def show(self):
        '''Display the solution information to the terminal'''
        out=['']
        out.extend(['Solution information','-'*10,''])
        if len(self.times)<5:
            for t in self.times:
                if len(self.times)>1: out.append(t)
                out.extend(self.info_price(t))
                out.extend(self.info_generators(t))
                out.extend(self.info_loads(t))
                out.extend(self.info_buses(t))
                out.extend(self.info_lines(t))
        out.extend(self.info_cost())
        print '\n'.join(out)
    def info_status(self): return ['solved in {time:0.4f} sec'.format(time=self.solve_time)]
    def info_price(self,t): return ['price={}'.format(self.lmps[str(t)])]
    def info_generators(self,t):
        out=['generator info:']
        if len(self.buses())>1: out.append('bus={}'.format(self.get_values('generators','bus')))
        out.extend(['name={}'.format(self.get_values('generators','name')),
                    'u={}'.format(self.get_values('generators','status',t)),
                    'P={}'.format(self.get_values('generators','power',t)),
                    # 'Pavail={}'.format(self.get_values('generators','power_available',t)),
                    'IC={}'.format(self.get_values('generators','incrementalcost',t))])
        return out
    def info_loads(self,t):
        return ['load info:',
                'bus={}'.format(self.get_values('loads','bus')) if len(self.buses())>1 else '',
                'name={}'.format(self.get_values('loads','name')),
                'Pd={}'.format(self.get_values('loads','power',t))]
    def info_buses(self,t):
        buses=self.buses()
        out=['bus info:',
             'name={}'.format(getattrL(buses,'name')),
             'Pinj={}'.format([ bus.Pgen(t,evaluate=True) - bus.Pload(t,evaluate=True) for bus in buses]),
             'angle={}'.format(self.get_values('buses','angle',t) if len(buses)>1 else []),
             'LMP={}'.format(self.lmps[str(t)])]
        return out
    def info_lines(self,t):
        lines=self.lines()
        return ['line info:',
             'connecting={}'.format(zip(getattrL(lines,'From'),getattrL(lines,'To'))),
             'Pk={}'.format(self.get_values('lines','power',t)),
             'price={}'.format(self.line_prices[str(t)])]
    def info_cost(self):
        return ['objective cost={}'.format(self.objective),
        'total cost of generation={}'.format(self.totalcost_generation),
        'linearized fuel cost of generation={}'.format(self.fuelcost_generation),
        ' non-linearized cost of generation={}'.format(self.fuelcost_true_generation),
        'percentage difference\t\t={diff:.2%}'.format(diff=self.costerror),
        ]

    def _get_generator_cost(self, generators, times, P, u):
        init_status = gen_time_dataframe(
            generators, 
            [times.initialTime], 
            [[gen.initial_status for gen in generators]])
        status_change = pd.concat([init_status, u]).diff().ix[times.strings.index]

        cost = 0
        fixed_cost = 0

        cost = P.copy()
        fixed_cost = status_change.copy()

        for gen in generators:
            g = str(gen)
            cost[g] = cost[g].map(lambda power: gen.bids.output_true(power))
            fixed_cost[g][fixed_cost[g]==1] = fixed_cost[g][fixed_cost[g]==1] * gen.startupcost
            fixed_cost[g][fixed_cost[g]==-1] = fixed_cost[g][fixed_cost[g]==-1] * gen.shutdowncost

        return cost.sum().sum(), fixed_cost.sum().sum()

    def _get_observed_costs(self):
        generators=self.generators()
        times=self.times.non_overlap()

        P = self.observed_generator_power
        if self.is_stochastic:
            u = self.stage_generators_status
        elif user_config.deterministic_solve:
            u = self.generators_status
        else:
            # this is a deterministic problem - put status into a df
            self.stage_generators_status = gen_time_dataframe(self.generators(), times, values=self.generators_status).astype(int)
            u = self.stage_generators_status

            # here it is also easy to see the power difference in forecast/observed
            # self.observed_generator_power - gen_time_dataframe(self.generators(), times, values=self.generators_power)

        cost, fixed_cost = self._get_generator_cost(generators, times, P, u)

        if user_config.deterministic_solve:
            self.expected_fuelcost_generation = self.fuelcost_generation
            self.expected_totalcost_generation = self.totalcost_generation
            self.expected_load_shed = self.load_shed

        # TODO - stochastcic problem: get expected generation cost over all sceanrios

        self.fuelcost_generation = cost
        self.totalcost_generation = cost + fixed_cost

        self.load_shed_timeseries = self.loads()[0].schedule - P.sum()

        self.load_shed = sum(sum(load.schedule[time] for time in times) for load in self.loads()) - P.sum().sum()


    def _calc_gen_power(self, sln, scenario_prefix=None):
        '''calculate generator power from a resolved solution using the observed stochastic gen's power'''
        gen_with_scenarios = self.power_system.get_generator_with_scenarios()
        times = self.times.non_overlap()

        power = gen_time_dataframe(self.generators(), times)

        pfx = ('' if scenario_prefix is None else scenario_prefix+'_') + 'power_'

        for gen in self.generators():

            if gen == gen_with_scenarios:
                get_val = lambda time: gen.observed_values[time]
            elif gen.is_controllable:
                # yuck - parse the power out of the native pyomo solution object
                # trying to avoid loading the instance - because it is different from the mainline stochastic solution
                get_val = lambda time: sln.variable[pfx+'{g}({t})'.format(g=str(gen),t=str(time))]['Value']
            else:
                get_val = lambda time: gen.schedule[time]

            for time, tstr in times.strings.to_dict().items():
                power[str(gen)][time] = get_val(tstr)
        return power



class Solution_ED(Solution):
    def info_lines(self,t): return []
    def info_buses(self,t): return []
    def visualization(self, show_cost_also=False):
        ''' economic dispatch visualization of linearized incremental cost'''
        if not do_plotting: return
        t=self.times[0]
        price=self.lmps[str(t)][0]
        generators,loads=self.generators(),self.loads()

        plotted_gens,names_gens,plotted_loads,names_loads=[],[],[],[]
        minGen=min(getattrL(generators,'Pmin'))
        maxGen=max(getattrL(generators,'Pmax'))

        #save a plot of the price space - illustrating equal IC
        ax=plot.axes()
        for gen in generators:
            if gen.status(t):
                in_range,out_range=gen.bids.output_incremental_range()
                if gen.bids.is_pwl:
                    line,=plot.step(in_range,out_range,where='pre',linestyle='-')
                else:
                    line,=plot.plot(in_range,out_range,linestyle='-', )
                plotted_gens.append(line)
                P=value(gen.power(t))
                IC=gen.incrementalcost(t)
                plot.plot(P,IC,'.',c=line.get_color(), markersize=8, linewidth=2, alpha=0.7)
                names_gens.append(gen.name)
        if price is not None:
            grayColor='.75'
            plot.plot([minGen,maxGen],[price,price],'--k',color=grayColor)
            plot.text(maxGen, price, '{p:0.2f} $/MWh'.format(p=price),color=grayColor,horizontalalignment='right')

        plot.xlabel('P [MWh]')
        if plotted_loads:     plot.ylabel('Marginal Cost-Benifit [$/MWh]')
        else:                plot.ylabel('Marginal Cost [$/MWh]')
        prettify_axes(ax)

        #plot.xlim(xmin=0,xmax=)
        ymin,_ = plot.ylim()
        if ymin<0: plot.ylim(ymin=0)

        legendGens=plot.legend(plotted_gens, names_gens, fancybox=True,title='Generators:',loc='best')
        if plotted_loads:
            plot.legend(plotted_loads, names_loads, fancybox=True,title='Loads:',loc='best')
            plot.gca().add_artist(legendGens) #add first legend to the axes manually bcs multiple legends get overwritten

        self.savevisualization(filename=full_filename('dispatch.png'))

        if show_cost_also:
            #show a plot of the cost space, illustrating the linearization
            plot.figure()
            gensPlotted_price=plotted_gens
            plotted_gens,names_gens,plotted_loads,names_loads=[],[],[],[]
            for g,gen in enumerate(generators):
                if gen.status(t):
                    plotted_gens.append( gen.cost_model.plot(P=value(gen.power(t)),linestyle='-',color=gensPlotted_price[g].get_color()) )
                    names_gens.append(gen.name)
            for load in loads:
                if load.kind=='bidding':
                    plotted_loads.append( load.bid(t).plot(P=value(load.power(t)),linestyle=':') )
                    names_loads.append(load.name)
            plot.xlabel('P [MWh]')
            if plotted_loads:     plot.ylabel('Cost-Benifit [$/h]')
            else:                plot.ylabel('Cost [$/h]')
            legendGens=plot.legend(plotted_gens, names_gens, fancybox=True,title='Generators:',loc='best')
            if plotted_loads:
                plot.legend(plotted_loads, names_loads, fancybox=True,title='Loads:',loc='best')
                plot.gca().add_artist(legendGens) #add first legend to the axes manually bcs multiple legends get overwritten

            self.savevisualization(filename=full_filename('dispatch-cost.png'))

    def saveCSV(self):
        '''economic dispatch generator solution values in spreadsheet form'''
        def niceTF(value): return 0 if value==0 else 1
        def nice_zeros(value): return 0 if value==0 else value

        t=self.times[0]
        generators=self.generators()
        output_loads= [load for load in self.loads() if getattr(load,'kind',None) in ['bidding','shifting']]
        fields,data=[],[]
        components=flatten([generators,output_loads])
        fields.append('name')
        data.append(getattrL(components,'name'))
        
        if user_config.dispatch_decommit_allowed:
            fields.append('u')
            data.append([niceTF( value(g.status(t)) and value(g.power(t))>0) for g in components])

        fields.append('P')
        data.append([nice_zeros(value(g.power(t))) for g in components])

        fields.append('IC')
        data.append([nice_zeros(g.incrementalcost(t)) for g in components])

        writeCSV(fields,transpose(data),filename=full_filename('dispatch.csv'))


class Solution_OPF(Solution):
    def visualization(self,filename=None):
        '''power flow visualization'''
        if not do_plotting: return

        try: import networkx as nx
        except ImportError:
            logging.warning("Could'nt import networkx -- skipping plotting.")
            return

        buses,lines,t=self.buses(),self.lines(),self.times[0]

        G=nx.DiGraph()
        for bus in buses:
            Pinj=value(bus.Pgen(t)) - value(bus.Pload(t))
            G.add_node(bus.name, Pinj=Pinj)
        for line in lines:
            P=value(line.power(t))
            if P>=0: G.add_edge(line.From,line.To,P=P,Plim=line.Pmax)
            else: G.add_edge(line.To,line.From,P=-P,Plim=-line.Pmin)

        pos=nx.spectral_layout(G)
        Pinj=[ndata['Pinj'] for bus,ndata in G.nodes(data=True) if 'Pinj' in ndata]
        nx.draw(G,node_color=Pinj,pos=pos,node_size=1500,alpha=.7,cmap=plot.cm.get_cmap('RdYlBu'),fontsize=30)
        cb=plot.colorbar(shrink=.8)
        cb.set_label('injected power [MW]',fontsize=15)

        Plines=[edata['P'] for _,t,edata in G.edges(data=True) if 'P' in edata]
        atLimLines=[(f,t) for f,t,edata in G.edges(data=True) if within(edata['P'],val=edata['Plim'],eps=1e-3) ]
        nx.draw_networkx_edges(G,edge_color='0.6',pos=pos,width=Plines,alpha=0.5)
        nx.draw_networkx_edges(G,edgelist=atLimLines,edge_color='r',pos=pos,width=Plines,alpha=0.5)
        self.savevisualization(full_filename('powerflow.png'))

    def saveCSV(self):
        '''OPF generator and line power values in spreadsheet form'''
        t=self.times[0]

        fields,data=[],[]
        fields.append('generator name');  data.append(self.get_values('generators','name'))
        fields.append('u');  data.append(self.get_values('generators','status',t))
        fields.append('P');  data.append(self.get_values('generators','power',t))
        fields.append('IC');  data.append(self.get_values('generators','incrementalcost',t))

        writeCSV(fields,transpose(data),filename=full_filename('powerflow-generators.csv'))


        fields,data=[],[]
        fields.append('from');  data.append(self.get_values('lines','From'))
        fields.append('to');  data.append(self.get_values('lines','To'))
        fields.append('power'); data.append(self.get_values('lines','power',t))
        fields.append('congestion shadow price'); data.append(self.line_prices[str(t)])

        writeCSV(fields,transpose(data),filename=full_filename('powerflow-lines.csv'))

    def info_price(self,t): return [] #built into bus info


class Solution_UC(Solution):
    def info_lines(self,t): return []
    def info_buses(self,t): return []
    def saveCSV(self, save_final_status=False):
        '''generator power values and statuses for unit commitment'''

        # mutlistage UC
        # for stochastic: output is the generators' power under observed wind
        self.generators_power.to_csv(full_filename('commitment-power.csv'))
        self.generators_status.to_csv(full_filename('commitment-status.csv'))

    def visualization(self, withPrices=True):
        '''generator output visualization for unit commitment'''
        if not do_plotting: return

        prices=[self.lmps[str(t)][0] for t in self.times]
        stack_plot_UC(self, self.generators(), self.times, prices, withPrices=withPrices)
        self.savevisualization(full_filename('commitment.png'))


class Solution_SCUC(Solution_UC):
    def visualization(self): logging.warning('no visualization for SCUC. Spreadsheet output is valid, except for the price column is the price on first bus only.')


class Solution_UC_multistage(Solution_UC):
    '''
    Muti-stage unit commitment. Each stage represents one optimization problem.
    Each element of the list :param:stage_solutions is a :class:`~results.Solution_UC` object.

    '''
    def __init__(self,power_system, stage_times, stage_solutions):
        update_attributes(self,locals(),exclude=['stage_solutions','stage_times'])

        self.is_stochastic = any(sln.is_stochastic for sln in stage_solutions)
        times = pd.concat([times.non_overlap().strings for times in stage_times]).index
        self.times=TimeIndex(times)
        self.times.set_initial(stage_times[0].initialTime)

        self.objective = self._sum_over('objective',stage_solutions)
        self.solve_time = self._sum_over('solve_time',stage_solutions)
        #self.active_constraints = sum([dual(c)!=0 for nm,c in constraints.items()])
        #self.total_constraints = len(constraints)
        self._get_outputs(stage_solutions)
        self._get_costs(stage_solutions)
        self._get_prices(stage_solutions)
    def _sum_over(self,attrib,stage_solutions): return sum(getattr(sln, attrib) for sln in stage_solutions)

    def _get_outputs(self,stage_solutions):
        '''the outputs under observed wind'''
        if self.is_stochastic or user_config.deterministic_solve:
            self.generators_power = pd.concat([stage.observed_generator_power for stage in stage_solutions])
            self.generators_status = pd.concat([stage.stage_generators_status for stage in stage_solutions])
        else:
            self.generators_power  = pd.concat([stage.generators_power for stage in stage_solutions])
            self.generators_status = pd.concat([stage.generators_status for stage in stage_solutions])

    def _get_costs(self,stage_solutions):
        self.fuelcost_generation=self._sum_over('fuelcost_generation',stage_solutions)
        self.totalcost_generation=self._sum_over('totalcost_generation',stage_solutions)
        self.load_shed = self._sum_over('load_shed',stage_solutions)

        if user_config.deterministic_solve:
            self.expected_fuelcost_generation = self._sum_over('expected_fuelcost_generation',stage_solutions)
            self.expected_totalcost_generation = self._sum_over('expected_totalcost_generation',stage_solutions)
            self.expected_load_shed = self._sum_over('expected_load_shed',stage_solutions)

        if not self.is_stochastic:
            self.fuelcost_true_generation=self._sum_over('fuelcost_true_generation',stage_solutions)
            self._get_cost_error()



    def info_cost(self):
        resolved = (self.is_stochastic or user_config.deterministic_solve)
        expected = 'expected ' if resolved else ''
        observed = 'observed ' if resolved else ''

        out = [
        '{}objective cost={}'.format(expected, self.objective),
        'total {}generation costs={}'.format(observed, self.totalcost_generation),
        'linearized {}fuel cost of generation={}'.format(observed, self.fuelcost_generation),
        ]
        if user_config.deterministic_solve:
            out.extend([
                'total expected generation cost = {}'.format(self.expected_totalcost_generation)
            ])
#                'value of perfect information={}'.format(),
        if not resolved:
            out.extend([
                ' non-linearized cost of generation={}'.format(self.fuelcost_true_generation),
                'percentage difference\t\t={diff:.2%}'.format(diff=self.costerror),
            ])
        return out

    def _get_prices(self,stage_solutions):
        self.lmps={}
        for stage in stage_solutions: self.lmps.update(stage.lmps)
    def show(self):
        out=[]
        out.extend(self.info_status())
        out.extend(self.info_cost())
        out.extend(self.info_shedding())
        print '\n'.join(out)
    def info_generators(self): return []
    def info_loads(self): return []
    def info_status(self):
        return ['solved multistage problem in a total solver time of {time:0.4f} sec'.format(time=self.solve_time)]
    def info_shedding(self):
        return ['total load shed={}MW'.format(self.load_shed) if self.load_shed>0 else '']


class Solution_Stochastic(Solution):
    def __init__(self,power_system,times,datadir='.', is_stochastic=True):
        update_attributes(self,locals())
        self.scenarios=sorted(self.power_system._scenario_instances.keys())

        self._get_problem_info()
        self._get_outputs()
        self._get_costs()
        self._get_prices()


    def _get_outputs(self):
        generators= self.power_system.generators()
        self.generators_power=dict([(s,{}) for s in self.scenarios])
        self.generators_status=dict([(s,{}) for s in self.scenarios])
        for s in self.scenarios:
            for time in self.times:
                self.generators_power[s][time] =[value(gen.power(time,s)) for gen in generators]
                self.generators_status[s][time] =[value(gen.status(time,s))==1 for gen in generators]

        times_to_store = self.times.non_overlap()
        self.stage_generators_status = gen_time_dataframe(
            self.generators(),
            times_to_store,
            values=[self.generators_status[self.scenarios[0]][time] for time in times_to_store]
            )
        self.stage_generators_status = self.stage_generators_status.astype(int)

        return

    def _get_costs(self):
        instances=self.power_system._scenario_instances
        tree=self.power_system._scenario_tree
        root_node = tree._stages[0]._tree_nodes[0]
        self.expected_cost = root_node.computeExpectedNodeCost(instances)
        self.cost_per_scenario=stochastic.get_scenario_based_costs(tree,instances)

    def _get_cost_error(self): pass

#    def _get_prices(self):
#        self.lmps={}
#        self.line_prices={}
#        for t in self.times:
#            self.lmps[str(t)]=[bus.price(t) for bus in self.buses()]
#            self.line_prices[str(t)]=[line.price(t) for line in self.lines()]



    def info_cost(self):
        return ["expected cost= {}".format(self.expected_cost),
                "scenario costs: {}".format(self.cost_per_scenario)]
    def info_generators(self,s):
        out=['  name={}'.format(','.join(gen.name for gen in self.generators()))]
        for time in self.times:
            out.extend(['  {} power={}'.format(str(time),self.generators_power[s][time]),
                        '  {} status={}'.format(str(time),self.generators_status[s][time])])
        return out
    def show(self):
        '''Display the solution information to the terminal'''
        #self.problem.scenario_tree.pprintSolution()
        out=['']
        out.extend(['Solution information','-'*20])
        out.extend(self.info_cost())

        for s in self.scenarios:
                out.append('scenario {s}:'.format(s=s))
                out.extend(self.info_generators(s))
        print '\n'.join(out)
        #P=self.generators()[2].power(self.times[0])
        #print P.name,values

class Solution_Stochastic_UC(Solution_Stochastic):
    def saveCSV(self):
        '''generator power values and statuses for stochastic unit commitment'''
        data=[]
        fields=['generators','times','scenarios','power','status']
        for g,gen in enumerate(self.generators()):
            for time in self.times:
                for scenario in self.scenarios:
                    row=[gen.name,
                         str(time.Start),
                         scenario,
                         self.generators_power[scenario][time][g],
                         self.generators_status[scenario][time][g]
                         ]
                    data.append(row)
        writeCSV(fields,data,filename=full_filename('commitment.csv'))


def _colormap(numcolors,colormapName='gist_rainbow',mincolor=1):
    cm = matplotlib.cm.get_cmap(colormapName)
    return [cm(1.*i/numcolors) for i in range(mincolor,numcolors+mincolor)]

def stack_plot_UC(solution,generators,times,prices,
                  withPrices=True,
                  seperate_legend=False,
                  hours_tick_interval=None
                  ):
    withPrices=withPrices and any(prices)
    font_big={'fontsize':15}
    figWidth=.85; figLeft=(1-figWidth)/2
    yLabel_pos={'x':-0.12,'y':0.5}

    fig=plot.figure(figsize=(10, 4), dpi=180)
    ax=plot.axes([figLeft,.1,figWidth,.6])
    ax.set_ylabel('energy [MWh]',ha='center',**font_big)
    ax.yaxis.set_label_coords(**yLabel_pos)
    prettify_axes(ax)

    alpha_initialTime=0.2

    gens_plotted,legend_labels=[],[]

    T=[t.Start for t in times]
    bar_width = times.intervalhrs / 24.0 #maplotlib dates have base of 1day
    stack_bottom=[0]*len(T)


    def addtostackplot(ax,time,power,color, gens_plotted,stack_bottom):
        #add commitment times to stackplot
        plt=ax.bar(time,power,bottom=stack_bottom,color=color, linewidth=.01, width=bar_width)
        #add power to stack bottom
        stack_bottom=elementwiseAdd(power,stack_bottom)
        #add to list of gens plotted
        gens_plotted.append(plt[0])
        return gens_plotted,stack_bottom

    if len(generators)<=5:
        colors=_colormap(len(generators),colormapName='Blues')
        for g,gen in enumerate(generators):
            Pgen=[solution.generators_power[t][g] for t,time in enumerate(times)]#[value(gen.power(t)) for t in times]
            gens_plotted,stack_bottom=addtostackplot(ax,T,Pgen,colors[g], gens_plotted,stack_bottom)
            legend_labels.append(gen.name)
    else:
        #group generators by kind
        kind_map=dict(ngst='shoulder NG',ngcc='shoulder NG',nggt='peaker NG',chp='CHP')
        ordered_kinds=['nuclear','coal','CHP','other','shoulder NG','peaker NG','wind']
        colors=_colormap(len(ordered_kinds),colormapName='Blues')
        power_by_kind=OrderedDict(zip(ordered_kinds,[None]*len(ordered_kinds)))
        for g,gen in enumerate(generators):
            kind=gen.kind.lower() if gen.kind.lower() in ordered_kinds else kind_map.get(gen.kind.lower(),'other')
            if power_by_kind[kind] is None:
                power_by_kind[kind]= [solution.generators_power[t][g] for t,time in enumerate(times)]#[value(gen.power(t)) for t in times]
            else:
                power_by_kind[kind]=elementwiseAdd([solution.power_generation[t][g] for t,time in enumerate(times)],power_by_kind[kind]) #[value(gen.power(t)) for t in times]

        for kind,Pgen in power_by_kind.iteritems():
            if Pgen is None: continue
            gens_plotted,stack_bottom=addtostackplot(ax,T,Pgen,colors[ordered_kinds.index(kind)], gens_plotted,stack_bottom)
            legend_labels.append(kind)

    convert_to_GW=True if max(stack_bottom)>20000 else False

    #show prices
    if withPrices:
        prices=replace_all(prices, config.cost_load_shedding, None)
        prices_wo_none=[p for p in prices if p is not None]
        if prices_wo_none:
            axes_price = plot.axes([figLeft,.75,figWidth,.2],sharex=ax)
            axes_price.step(T+[times.End],prices+[prices[-1]],  where='post') #start from 1 past initial time
            axes_price.set_ylabel('price\n[$/MWh]',ha='center',**font_big)
            axes_price.yaxis.set_label_coords(**yLabel_pos)
            plot.setp(axes_price.get_xticklabels(), visible=False)
            #format the price axis nicely
            plot.ylim((.9*min(prices_wo_none),1.1*max(prices_wo_none)))
            axes_price.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(5))
            prettify_axes(axes_price)

    ax.xaxis_date()

    for label in ax.get_xticklabels():
        label.set_ha('right')
        label.set_rotation(30)

    #format the time axis nicely
    if hours_tick_interval is None:
        if 24*10>times.spanhrs>48:
            ax.xaxis.set_major_locator(matplotlib.dates.DayLocator())
            ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_minor_locator(matplotlib.dates.HourLocator())
        elif times.spanhrs<48:
            ax.xaxis.set_major_locator(matplotlib.dates.HourLocator())
            ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H:%M'))
        #otherwise use defaults
    else:
        ax.xaxis.set_major_locator(matplotlib.dates.HourLocator(interval=hours_tick_interval))
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H:%M'))


    #format the power axis nicely
    if convert_to_GW:
        labels_power=ax.get_yticks()
        labels_power=[P/1000 for P in labels_power]
        ax.set_yticklabels(labels_power)
        ax.set_ylabel('energy [GWh]',ha='center',**font_big)
    ax.autoscale_view()

    #add the legend
    plottedL=gens_plotted[::-1]
#    shrink_axis(ax,0.30)
#    if withPrices: shrink_axis(axes_price,0.30)
    legend_font=matplotlib.font_manager.FontProperties()
    legend_font.set_size('small')

    if seperate_legend:
        figlegend = plot.figure()
        figlegend.legend(plottedL, legend_labels[::-1],prop=legend_font,loc='center')
        figlegend.savefig(full_filename('commitment-legend.png'))
        plot.close(figlegend)
    else:
        ax.legend(plottedL, legend_labels[::-1],prop=legend_font)#,loc='center left', bbox_to_anchor=(1, 0.5))

def prettify_axes(ax):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.get_xaxis().tick_bottom()
    ax.get_yaxis().tick_left()
def shrink_axis(ax,percent_horizontal=0.20,percent_vertical=0):
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * (1-percent_horizontal), box.height*(1-percent_vertical)])


class MultistageStandalone(Solution_UC_multistage):
    def __init__(self, power_system, stage_times, store):

        self.is_stochastic = power_system.is_stochastic
        self._resolved = self.is_stochastic or user_config.deterministic_solve
        times = pd.concat([times.non_overlap().strings for times in stage_times]).index
        self.times=TimeIndex(times)
        self.times.set_initial(stage_times[0].initialTime)

        self.objective = store['expected_cost'].sum()
        if self._resolved:
            self.observed_cost = store['observed_cost'].sum()
        self.generators_power = store['power']
        self.generators_status = store['status']

        self.load_shed = store['load_shed'].sum()
        self.solve_time = store['solve_time'].sum()

    def info_cost(self):
        resolved = self._resolved
        expected = 'expected ' if resolved else ''
        observed = 'observed ' if resolved else ''

        out = ['{}objective cost={}'.format(expected, self.objective)]
        if resolved: out.append(
            'total {}generation costs={}'.format(observed, self.observed_cost))

        return out
