"""
    Solution models, output, and display for power system
    optimization problems. Matplotlib and networkx are used for
    visualization.
"""
import yaml
import logging
from collections import OrderedDict

from commonscripts import flatten,transpose,elementwiseAdd, getattrL,within,writeCSV,joindir,replace_all,update_attributes
from schedule import Timelist
from optimization import value,dual
import config,stochastic

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

def make_multistage_solution(power_system,*args,**kwargs):
    '''Create a multi stage solution object.'''
    if power_system.lines: logging.warning('no visualization for multistage SCUC yet')
    return Solution_UC_multistage(power_system,*args,**kwargs)

class Solution(object):
    '''
    Solution information template for a power system over times.
    Each problem type has its own class for visualization and 
    spreadsheet output, e.g. :class:`~solution.Solution_ED`. 
    '''
    def __init__(self,power_system,times,datadir='.'):
        update_attributes(self,locals())
        self._get_problem_info()
        self._get_costs()
        self._get_prices()
        self._get_outputs()
    def _get_problem_info(self):
        self.solve_time  =self.power_system.solution_time
        self.objective  =float(value(self.power_system.objective))
    def _get_outputs(self):
        self.generators_power =[self.get_values('generators','power',time) for time in self.times]
        self.generators_status=[[s==1 for s in self.get_values('generators','status',time)] for time in self.times]

    def _get_costs(self):
        generators=self.generators()
        times=getattr(self.times,'non_overlap_times',self.times)
        gen_fuel_costs_pwlmodel   = [[value(gen.operatingcost(t,evaluate=True)) for t in times] for gen in generators]
        gen_fuel_costs_polynomial = [[gen.truecost(t) for t in times] for gen in generators]
        self.totalcost_generation = sum(flatten([[float(gen.cost(t,evaluate=True)) for t in times] for gen in generators]))
        self.fuelcost_generation=float(sum( c for c in flatten(gen_fuel_costs_pwlmodel) ))
        self.fuelcost_true_generation=float(sum( c for c in flatten(gen_fuel_costs_polynomial) ))
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
                out.append('{tm}: {start}'.format(tm=t,start=t.Start))
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
    # def save(self,filename=None):
    #     if filename is None: filename=joindir(self.datadir,'solution.yaml')
    #     def get_time_listing(component,attr):
    #         try: return dict(zip(self.times.non_overlap_times,[self.get_values(component,attr,t) for t in self.times.non_overlap_times]))
    #         except AttributeError:
    #             return dict(zip(self.times,[self.get_values(component,attr,t) for t in self.times]))
    #     self.generators_status=get_time_listing('generators','status')
    #     self.generators_power=get_time_listing('generators','power')
    #     self.power_system=[]
    #     with open(filename,'w+') as f: yaml.dump(self,f)


class Solution_ED(Solution):
    def info_lines(self,t): return []
    def info_buses(self,t): return []
    def visualization(self,filename=None,show_cost_also=False):
        ''' economic dispatch visualization of linearized incremental cost'''
        if not do_plotting: return
        if filename is None: filename=joindir(self.datadir,'dispatch.png')
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
        
        self.savevisualization(filename=joindir(self.datadir,'dispatch.png'))
        
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
            
            self.savevisualization(filename='dispatch-cost.png')        
    def saveCSV(self,filename=None):
        '''economic dispatch generator solution values in spreadsheet form'''
        if filename is None: filename=joindir(self.datadir,'dispatch.csv')
        def niceTF(value): return 0 if value==0 else 1
        def nice_zeros(value): return 0 if value==0 else value
        
        t=self.times[0]
        generators=self.generators()
        output_loads= [load for load in self.loads() if getattr(load,'kind',None) in ['bidding','shifting']]
        fields,data=[],[]
        components=flatten([generators,output_loads])
        fields.append('name')
        data.append(getattrL(components,'name'))
        
        fields.append('u');   
        data.append([niceTF(value(g.status(t))) for g in components])
        
        fields.append('P')
        data.append([nice_zeros(value(g.power(t))) for g in components])
        
        fields.append('IC')
        data.append([nice_zeros(g.incrementalcost(t)) for g in components])
        
        writeCSV(fields,transpose(data),filename=filename)        
class Solution_OPF(Solution): 
    def visualization(self,filename=None): 
        '''power flow visualization'''
        if not do_plotting: return
        if filename is None: filename=joindir(self.datadir,'powerflow.png')
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
        self.savevisualization(filename)
        
    def saveCSV(self,filename=None,filename_lines=None):
        '''OPF generator and line power values in spreadsheet form''' 
        t=self.times[0]
        
        fields,data=[],[]
        fields.append('generator name');  data.append(self.get_values('generators','name'))
        fields.append('u');  data.append(self.get_values('generators','status',t))
        fields.append('P');  data.append(self.get_values('generators','power',t))
        fields.append('IC');  data.append(self.get_values('generators','incrementalcost',t))
        if filename is None: filename=joindir(self.datadir,'powerflow-generators.csv')
        writeCSV(fields,transpose(data),filename=filename)           
        
        
        fields,data=[],[]
        fields.append('from');  data.append(self.get_values('lines','From'))
        fields.append('to');  data.append(self.get_values('lines','To'))
        fields.append('power'); data.append(self.get_values('lines','power',t))
        fields.append('congestion shadow price'); data.append(self.line_prices[str(t)])
        if filename_lines is None: filename_lines=joindir(self.datadir,'powerflow-lines.csv') 
        writeCSV(fields,transpose(data),filename=filename_lines)        
    
    def info_price(self,t): return [] #built into bus info
class Solution_UC(Solution):
    def info_lines(self,t): return []
    def info_buses(self,t): return []
    def saveCSV(self,filename=None,save_final_status=False):
        '''generator power values and statuses for unit commitment'''
        if filename is None: filename=joindir(self.datadir,'commitment.csv')
        times=self.times
        fields,data=[],[]
        fields.append('times');  data.append([t.Start for t in times])
        fields.append('prices'); data.append([self.lmps[str(t)][0] for t in times]) 

        for g,gen in enumerate(self.generators()): 
            if gen.is_controllable:
                fields.append('status: '+str(gen.name))
                data.append([self.generators_status[t][g] for t,time in enumerate(times)])
            fields.append('power: '+str(gen.name))
            data.append([self.generators_power[t][g] for t,time in enumerate(times)])
        for load in self.loads():
            fields.append('load power: '+str(load.name))
            data.append([value(load.power(t)) for t in times])
            shed=[value(load.shed(t)) for t in times]
            if sum(shed)>0:
                fields.append('load shed: '+str(load.name))
                data.append(shed)
        writeCSV(fields,transpose(data),filename=filename)
        
        if save_final_status:
            filename=joindir(self.datadir,'statuses-final.csv')
            fields,data=[],[]
            fields.append('generators')
            data.append([gen.name for gen in self.generators()])
            
            t_final=self.times[-1]
            fields.append('status')
            data.append([gen.status(t_final) for gen in self.generators()])
            fields.append('hours')
            data.append([gen.gethrsinstatus(t_final,self.times) for gen in self.generators()])
            
            writeCSV(fields,transpose(data),filename=filename)
            
    def visualization(self,filename=None,withPrices=True,filename_DR=None):
        '''generator output visualization for unit commitment'''
        if not do_plotting: return
        if filename is None: filename=joindir(self.datadir,'commitment.png')
        prices=[self.lmps[str(t)][0] for t in self.times]
        stack_plot_UC(self,self.generators(),self.times,prices,self.datadir, withPrices=withPrices)
        self.savevisualization(filename)
        # DR_loads=filter(lambda d: getattr(d, 'kind','') in ['shifting','bidding','shifting-bidding'], self.loads())
        # if DR_loads:
        #     interval= int(DR_loads[0].interval_hours) if (len(self.times)<=24 and len(DR_loads)==1 and 'shifting' in getattr(DR_loads[0], 'kind','')) else None
        #     stack_plot_UC(DR_loads,self.times,prices,withPrices=withPrices,hours_tick_interval=interval)
        #     if filename_DR is None: filename_DR=joindir(self.datadir,'commitment-DR.png')
        #     self.savevisualization(filename_DR)
        

class Solution_SCUC(Solution_UC):
    def visualization(self): logging.warning('no visualization for SCUC. Spreadsheet output is valid, except for the price column is the price on first bus only.')
    
    
class Solution_UC_multistage(Solution_UC):
    '''
    Muti-stage unit commitment. Each stage represents one optimization problem.
    Each element of the list :param:stage_solutions is a :class:`~results.Solution_UC` object.
    
    '''
    def __init__(self,power_system,stage_times,datadir,stage_solutions):
        update_attributes(self,locals(),exclude=['stage_solutions','stage_times'])
        self.times=Timelist(flatten([list(times.non_overlap_times) for times in stage_times]))
        self.times.setInitial(stage_times[0].initialTime)
        
        self.objective = self._sum_over('objective',stage_solutions)
        self.solve_time = self._sum_over('solve_time',stage_solutions)
        #self.active_constraints = sum([dual(c)!=0 for nm,c in constraints.items()])
        #self.total_constraints = len(constraints)
        self._get_outputs(stage_solutions)
        self._get_costs(stage_solutions)
        self._get_prices(stage_solutions)
    def _sum_over(self,attrib,stage_solutions): return sum(getattr(sln, attrib) for sln in stage_solutions)     
    def _get_outputs(self,stage_solutions):
        self.generators_power=flatten([stage.generators_power for stage in stage_solutions])
        self.generators_status=flatten([stage.generators_status for stage in stage_solutions])
    def _get_costs(self,stage_solutions):
        self.fuelcost_generation=self._sum_over('fuelcost_generation',stage_solutions)
        self.fuelcost_true_generation=self._sum_over('fuelcost_true_generation',stage_solutions)
        self.totalcost_generation=self._sum_over('totalcost_generation',stage_solutions)
        self.load_shed=          self._sum_over('load_shed',stage_solutions)
        self._get_cost_error()       
    def info_cost(self):
        return ['objective cost={}'.format(self.objective),
        'total generation costs={}'.format(self.totalcost_generation),
        'linearized fuel cost of generation={}'.format(self.fuelcost_generation),
        ' non-linearized cost of generation={}'.format(self.fuelcost_true_generation),
        'percentage difference\t\t={diff:.2%}'.format(diff=self.costerror),
        ]
    
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


class Solution_Stochsatic(Solution):
    def __init__(self,power_system,times,datadir='.'):
        update_attributes(self,locals())
        self.scenarios=sorted(self.power_system._scenario_instances.keys())
        self.power_system._scenario_tree.snapshotSolutionFromInstances(self.power_system._scenario_instances)
        stochastic.update_variables(self.power_system,times)
        
        self._get_problem_info()
        self._get_costs()
        self._get_prices()
        self._get_outputs()
        
    def _get_costs(self):
        instances=self.power_system._scenario_instances
        tree=self.power_system._scenario_tree
        root_node = tree._stages[0]._tree_nodes[0]
        self.expected_cost = root_node.computeExpectedNodeCost(instances)
        self.cost_per_scenario=stochastic.get_scenario_based_costs(tree,instances)
    def _get_cost_error(self): pass
#        try: self.costerror=abs(self.fuelcost_generation-self.fuelcost_true_generation)/self.fuelcost_true_generation
#        except ZeroDivisionError: self.costerror=0
    def _get_prices(self): pass
#        self.lmps={}
#        self.line_prices={}
#        for t in self.times: 
#            self.lmps[str(t)]=self.get_values('buses','price',t)
#            self.line_prices[str(t)]=self.get_values('lines','price',t)
    def info_cost(self):
        return ["expected cost= {}".format(self.expected_cost),
                "scenario costs: {}".format(self.cost_per_scenario)]
    def info_generators(self,t):
        out=['generator info:']
        if len(self.buses())>1: out.append('bus={}'.format(self.get_values('generators','bus')))
        out.extend(['name={}'.format(self.get_values('generators','name')),
                    'u={}'.format(self.get_values('generators','status',t))])
        return out
    def show(self):
        '''Display the solution information to the terminal'''
        #self.problem.scenario_tree.pprintSolution()
        out=['']
        out.extend(['Solution information','-'*20])
        out.extend(self.info_cost())
        
        for t in self.times:
                out.append('{tm}: {start}'.format(tm=t,start=t.Start))
                out.extend(self.info_generators(t))
        print '\n'.join(out)
        #P=self.generators()[2].power(self.times[0])
        #print P.name,values

    def get_values(self,kind='generators',attrib='power',time=None,scenario=None):
        '''Get the attributes of all objects of a certain kind at a given time and scenario.'''
        method={'generators':self.generators,'loads':self.loads,'lines':self.lines,'buses':self.buses}
        if time is not None:
            out=[]
            for obj in method[kind]():
                var=getattr(obj, attrib)(time)
                var.pprint()
                #self.power_system.show_model()
                self.power_system._stochastic_instance.pprint()
                barf
                try: out.append(var)
                except AttributeError: out.append(var)
                except KeyError: out.append(var.name)
            return out
        else: return [getattr(obj, attrib) for obj in method[kind]()]
    def value(self,var,scenario): 
        try: return self.power_system.variables[var.name][scenario]
        except AttributeError: var
class Solution_Stochastic_UC(Solution_Stochsatic):
    def saveCSV(self,filename=None):
        '''generator power values and statuses for unit commitment'''
        if filename is None: filename=joindir(self.datadir,'commitment.csv')
        data=[]
        fields=['generators','times','scenarios','power','status']
        for gen in self.generators():
            for time in self.times:
                for scenario in self.scenarios:
                    try: row=[gen.name,str(time.Start),scenario,self.value(gen.power(time),scenario),self.value(gen.status(time),scenario)]
                    except KeyError:
                        print gen.power(time) 
                        raise
                    data.append(row)
        writeCSV(fields,data,filename=filename)


def _colormap(numcolors,colormapName='gist_rainbow',mincolor=1):
    cm = matplotlib.cm.get_cmap(colormapName)
    return [cm(1.*i/numcolors) for i in range(mincolor,numcolors+mincolor)]      

def stack_plot_UC(solution,generators,times,prices,
                  datadir=None,
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
        figlegend.savefig(joindir(datadir,'commitment-legend.png'))
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
