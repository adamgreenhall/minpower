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
import config

import matplotlib
import matplotlib.pyplot as plot
from matplotlib.font_manager import FontProperties


def prettify_plots(for_publication=True):
    plot.rc("xtick", direction="out")
    plot.rc("ytick", direction="out")
    plot.rc("ytick",labelsize='small')
    plot.rc("xtick",labelsize='small')
    plot.rc("legend",fancybox=True)
    if for_publication:
        plot.rc("font",size=16)
        plot.rc("font",family="serif")
        
def prettify_axes(ax):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.get_xaxis().tick_bottom()
    ax.get_yaxis().tick_left()
prettify_plots()

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
    return kind

def make_solution(power_system,times,**kwargs):
    '''
    Create a :class:`solution.Solution` object for a power system over times.
    
    :param times: a :class:`~schedule.Timelist` object
    :param power_system: a :class:`~powersystems.PowerSystem` object    
    '''
    problem_type=dict(ED=Solution_ED, OPF=Solution_OPF, UC=Solution_UC, SCUC=Solution_SCUC)
    kind=classify_problem(times,power_system)
    return problem_type[kind](power_system,times,**kwargs)

def make_multistage_solution(power_system,*args,**kwargs):
    '''Create a multi stage solution object.'''
    if power_system.lines: logging.warning('no visualization for multistage SCUC yet')
    return Solution_UC_multistage(power_system,*args,**kwargs)

def make_multistage_solution_standalone(power_system,stage_times,datadir,stage_solution_files):
    #print 'stage files are:',stage_solution_files
    stage_solutions=[]
    generators=power_system.generators()
    for filename in stage_solution_files:
        with open(filename,'r') as f: stage_solutions.append(yaml.load(f))
    for sln in stage_solutions:
        for time in sln.times.non_overlap_times:
            for g,status in enumerate(sln.generators_status[time]):
                generators[g].add_variable('status', 'u', time,fixed_value=status)
            for g,power in enumerate(sln.generators_power[time]):
                generators[g].add_variable('power', 'P', time,fixed_value=power)
#        lmp_times=sorted(sln.lmps.keys())
#        for t,time in enumerate(sln.times):
#            sln.lmps[time]=sln.lmps[lmp_times[t]]
    return Solution_UC_multistage(power_system,stage_times,datadir,stage_solutions)


class Solution(object):
<<<<<<< HEAD
<<<<<<< HEAD
    def __init__(self,power_system,times,datadir='.',problem=None):
        power_system.update_variables()
        self.power_system=power_system
        self.times=times
        self.datadir=datadir
        
        self.buses=power_system.buses
        self.generators=flatten( [[gen for gen in bus.generators] for bus in self.buses] )
        self.loads     =flatten( [[ld  for ld   in bus.loads]     for bus in self.buses] )
        self.constraints=problem.constraints
        self.solveTime  =problem.solutionTime
<<<<<<< HEAD
        self.status     =problem.statusText()
        self.solved        =problem.status==1
=======
        self.status     =problem.statusText
<<<<<<< HEAD
        self.solved        =problem.status==1
        for g in self.generators: g.update_vars(times,problem)
        for l in self.loads: l.update_vars(times,problem)
<<<<<<< HEAD
>>>>>>> duals and variables now working with coopr. tests are still failing.
=======
        for b in self.buses: b.update_vars(times,problem)
        for l in self.lines: l.update_vars(times,problem)
>>>>>>> working coopr and pulp mix
=======
        self.solved     =problem.solved
>>>>>>> redo of results. now problem with duals
=======
=======
    '''
    Solution information template for a power system over times.
    Each problem type has its own class for visualization and 
    spreadsheet output, e.g. :class:`~solution.Solution_ED`. 
    '''
<<<<<<< HEAD
>>>>>>> doc overhaul bidding
    def __init__(self,power_system,times,problem,datadir='.'):
        update_attributes(self,locals(),exclude=['problem'])
=======
    def __init__(self,power_system,times,datadir='.'):
        update_attributes(self,locals())
>>>>>>> basic conversion of power_system to OptimziationProblem object
        self.power_system.update_variables()
>>>>>>> major cleanup of results.py. still need to tackle the multistage commitments
        
        #objgraph.show_backrefs([problem.variables.values()[0]], filename='variable-backref-post-solve.png')
        #objgraph.show_chain(
        #    objgraph.find_backref_chain( problem.variables.values()[0],inspect.ismodule),filename='variable-backref-post-solve-module-chain.png')
        
<<<<<<< HEAD
        if not problem.solved: 
            logging.error('Problem solve was not completed. Status {s}.'.format(s=problem.status))
            return
<<<<<<< HEAD
        
<<<<<<< HEAD
<<<<<<< HEAD
=======
        for gen in self.generators: gen.update_vars(times, problem)
            
>>>>>>> added matplotlib back in
        self.objective  =float(value(problem.objective))
<<<<<<< HEAD
        self.activeConstraints = sum([dual(c)!=0 for nm,c in problem.constraints.items()])
=======
        
        
        #self.activeConstraints = sum([dual(c)!=0 for nm,c in problem.constraints.items()])
>>>>>>> debugging solution constraint problem
        self.totalConstraints = len(problem.constraints)
        self.calcCosts()
        self.calcPrices(problem.constraints)
=======
        self.objective  =float(value(problem.objective))
#        for c in problem.constraints.values():
#            print c, getattr(c,'dual',None)
#        self.activeConstraints = sum([c.dual!=0 for c in problem.constraints.values()])
        self.totalConstraints = len(problem.constraints)
        self.calcCosts()
<<<<<<< HEAD
        self.calcPrices(problem)
>>>>>>> duals and variables now working with coopr. tests are still failing.
    def show(self):
=======
    def savevisualization(self,filename=None):
>>>>>>> redo of results. now problem with duals
        if not self.solved: return
=======
        self._get_problem_info(problem)
=======
        self._get_problem_info()
>>>>>>> basic conversion of power_system to OptimziationProblem object
        self._get_costs()
        self._get_prices()
        self.power_system.clear_constraints()
        #gc.collect()
        #objgraph.show_backrefs([problem.constraints.values()[0]], filename='constraints-backref-post-solve.png')
        #objgraph.show_chain(objgraph.find_backref_chain(objgraph.by_type('Constraint')[0],inspect.ismodule),filename='constraint-backref-post-solve-chain.png')
        #leakers=objgraph.get_leaking_objects()
        #objgraph.show_most_common_types(objects=leakers)
        #objgraph.show_refs(leakers[:3], refcounts=True, filename='leakers.png')
    def _get_problem_info(self):
        self.solve_time  =self.power_system.solution_time
        self.objective  =float(value(self.power_system.objective))

    def _get_costs(self):
        generators=self.generators()
        times=getattr(self.times,'non_overlap_times',self.times)
        gen_fuel_costs_pwlmodel   = [[value(gen.operatingcost(t)) for t in times] for gen in generators]
        gen_fuel_costs_polynomial = [[gen.truecost(t) for t in times] for gen in generators]
        self.totalcost_generation = sum(flatten([[float(gen.cost(t)) for t in times] for gen in generators]))
        self.fuelcost_generation=float(sum( c for c in flatten(gen_fuel_costs_pwlmodel) ))
        self.fuelcost_true_generation=float(sum( c for c in flatten(gen_fuel_costs_polynomial) ))
        self.load_shed = sum( sum(load.shed(t) for load in self.loads()) for t in times )
        self._get_cost_error()
    def _get_cost_error(self):
        try: self.costerror=abs(self.fuelcost_generation-self.fuelcost_true_generation)/self.fuelcost_true_generation
        except ZeroDivisionError: self.costerror=0
    def _get_prices(self):
        self.lmps={}
        self.line_prices={}
        for t in self.times: 
            self.lmps[str(t)]=self.get_values('buses','price',t)
            self.line_prices[str(t)]=self.get_values('lines','price',t)
        
    def buses(self): return self.power_system.buses
    def lines(self): return self.power_system.lines
    def generators(self): return self.power_system.generators()
    def loads(self): return flatten( [[ld for ld in bus.loads] for bus in self.buses()] )
    def get_values(self,kind='generators',attrib='power',time=None):
        '''Get the attributes of all objects of a certain kind at a given time.'''
        method={'generators':self.generators,'loads':self.loads,'lines':self.lines,'buses':self.buses}
        if time is not None: return [getattr(obj, attrib)(time) for obj in method[kind]()]
        else: return [getattr(obj, attrib) for obj in method[kind]()]
        
    def savevisualization(self,filename=None):
<<<<<<< HEAD
>>>>>>> major cleanup of results.py. still need to tackle the multistage commitments
=======
        '''Save the visualization to a file'''
>>>>>>> doc overhaul bidding
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
             'Pinj={}'.format([ bus.Pgen(t) - bus.Pload(t) for bus in buses]),
             'angle={}'.format(self.get_values('buses','angle',t)),
             'LMP={}'.format(self.lmps[str(t)])]    
        return out    
    def info_lines(self,t):
<<<<<<< HEAD
        print ' line info:'
        print '  connecting=', zip(getattrL(self.lines,'From'),getattrL(self.lines,'To'))            
        print '  Pk =', [value(line.power(t)) for line in self.lines]
        print '  mu=', [line.price(t) for line in self.lines]
    def calcCosts(self):
        gen_fuel_costs_pwlmodel   = [[value(gen.operatingcost(t)) for t in self.times] for gen in self.generators]
        gen_fuel_costs_polynomial = [[gen.truecost(t) for t in self.times] for gen in self.generators]
        self.fuelcost_generation=float(sum( [c for c in flatten(gen_fuel_costs_pwlmodel) if c is not None] ))
        self.truecost_generation=float(sum( [c for c in flatten(gen_fuel_costs_polynomial) if c is not None] ))
        try: self.costerror=abs(self.fuelcost_generation-self.truecost_generation)/self.truecost_generation
        except ZeroDivisionError: self.costerror=0
<<<<<<< HEAD
<<<<<<< HEAD
    def calcPrices(self,constraints):
        for bus in self.buses:
            for t in self.times:    
                bus.price[t] = dual(constraints['powerBalance_'+bus.iden(t)])        
=======
    def calcPrices(self,problem):
<<<<<<< HEAD
        for bus in self.buses:
            for t in self.times:    
                bus.price[t] = bus.getprice(t,problem)
>>>>>>> duals and variables now working with coopr. tests are still failing.
=======
        for t in self.times:    
            for bus in self.buses:  bus.price[t] = bus.getprice(t,problem)
            for line in self.lines: line.price[t] = line.getprice(t,problem)
    
>>>>>>> working coopr and pulp mix
=======
>>>>>>> redo of results. now problem with duals
=======
        lines=self.lines()
        return ['line info:',
             'connecting={}'.format(zip(getattrL(lines,'From'),getattrL(lines,'To'))),       
             'Pk={}'.format(self.get_values('lines','power',t)),
<<<<<<< HEAD
<<<<<<< HEAD
             'price={}'.format(self.get_values('lines','price',t))]            
>>>>>>> major cleanup of results.py. still need to tackle the multistage commitments
=======
             'price={}'.format(self.line_prices[t])]            
>>>>>>> store prices, clear constraints
=======
             'price={}'.format(self.line_prices[str(t)])]            
>>>>>>> setting up pympler test
    def info_cost(self):
        return ['objective cost={}'.format(self.objective),
        'total cost of generation={}'.format(self.totalcost_generation),
        'linearized fuel cost of generation={}'.format(self.fuelcost_generation),
        ' non-linearized cost of generation={}'.format(self.fuelcost_true_generation),
        'percentage difference\t\t={diff:.2%}'.format(diff=self.costerror),
        ]
    def save(self,filename=None):
        if filename is None: filename=joindir(self.datadir,'solution.yaml')
        def get_time_listing(component,attr):
            try: return dict(zip(self.times.non_overlap_times,[self.get_values(component,attr,t) for t in self.times.non_overlap_times]))
            except AttributeError:
                return dict(zip(self.times,[self.get_values(component,attr,t) for t in self.times]))
        self.generators_status=get_time_listing('generators','status')
        self.generators_power=get_time_listing('generators','power')
        self.power_system=[]
        with open(filename,'w+') as f: yaml.dump(self,f)


class Solution_ED(Solution):
    def info_lines(self,t): return []
    def info_buses(self,t): return []
    def visualization(self,filename=None,show_cost_also=False):
        ''' economic dispatch visualization of linearized incremental cost'''
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
                plotted_gens.append( gen.cost_model.plot_derivative(P=value(gen.power(t)),linestyle='-') )
                names_gens.append(gen.name)
        for load in loads: 
            if load.kind=='bidding': 
                plotted_loads.append( load.bid(t).plot_derivative(P=value(load.power(t)),linestyle=':') )
                names_loads.append(load.name)
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
        
        self.savevisualization(filename='dispatch.png')
        
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
        data.append([niceTF(g.status(t)) for g in components])
        
        fields.append('P')
        data.append([nice_zeros(g.power(t)) for g in components])
        
        fields.append('IC')
        data.append([nice_zeros(g.incrementalcost(t)) for g in components])
        
        writeCSV(fields,transpose(data),filename=filename)        
class Solution_OPF(Solution): 
    def visualization(self,filename=None): 
        '''power flow visualization'''
        if filename is None: filename=joindir(self.datadir,'powerflow.png')
        import networkx as nx
        buses,lines,t=self.buses(),self.lines(),self.times[0]
        
        G=nx.DiGraph()
        for bus in buses:
            Pinj=value(bus.Pgen(t)) - value(bus.Pload(t))
            G.add_node(bus.name, Pinj=Pinj)
        for line in lines:
            P=line.power(t)
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

        for gen in self.generators(): 
            if gen.is_controllable:
                fields.append('status: '+str(gen.name))
                data.append([1 if value(gen.status(t))==1 else 0 for t in times])
            fields.append('power: '+str(gen.name))
            data.append([value(gen.power(t)) for t in times])
        for load in self.loads():
            fields.append('load power: '+str(load.name))
            data.append([value(load.power(t)) for t in times])
            shed=[value(load.shed(t)) for t in times]
            print 'shed',sum(shed)
            if sum(shed)>0:
                fields.append('load shed: '+str(load.name))
                data.append(shed)
        writeCSV(fields,transpose(data),filename=filename)
<<<<<<< HEAD
    
<<<<<<< HEAD
    def visualization(self,filename='commitment.png',withPrices=True,withInitial=False,seperate_legend=False):
        '''generator output visualization for unit commitment'''
<<<<<<< HEAD
        times,generators,loads=self.times,self.generators(),self.loads()
        if len(generators)<=5: fewunits=True
        else: fewunits=False
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
    
        times,generators,loads=self.times,self.generators,self.loads
        prices=[self.buses[0].price[t] for t in self.times]

=======
        
        times,generators,loads=self.times,self.generators,self.loads
        prices=[self.buses[0].price(t) for t in self.times]
=======
        prices=[self.buses()[0].price(t) for t in self.times]
>>>>>>> major cleanup of results.py. still need to tackle the multistage commitments
=======
        prices=[self.lmps[t][0] for t in self.times]
>>>>>>> store prices, clear constraints
        
>>>>>>> duals and variables now working with coopr. tests are still failing.
        bigFont={'fontsize':15}
        figWidth=.85; figLeft=(1-figWidth)/2
        yLabel_pos={'x':-0.09,'y':0.5}
        
        fig=plot.figure(figsize=(10, 4), dpi=120)
        ax=plot.axes([figLeft,.1,figWidth,.6])
        ax.set_ylabel('energy [MWh]',ha='center',**bigFont)
        ax.yaxis.set_label_coords(**yLabel_pos)
        prettify_axes(ax)
        
        alpha_initialTime=0.2
        
        gensPlotted,loadsPlotted,yLabels=[],[],[]
        
        T=[t.Start for t in times.wInitial]
        barWidth = times.intervalhrs / 24.0 #maplotlib dates have base of 1day
        initWidth = times.initialTime.intervalhrs / 24.0        
        stackBottom=[0]*len(T)
        
        
        def addtostackplot(ax,time,power,color, gensPlotted,stackBottom):
            #add initial time to stackplot
            if withInitial:
                ax.bar(time[0],power[0],bottom=stackBottom[0],color=color, edgecolor=color, alpha=alpha_initialTime, width=initWidth)
            #add commitment times to stackplot
            plt=ax.bar(time[1:],power[1:],bottom=stackBottom[1:],color=color, edgecolor=color,width=barWidth)
            #add power to stack bottom
            stackBottom=elementwiseAdd(power,stackBottom)
            #add to list of gens plotted
            gensPlotted.append(plt[0])
            return gensPlotted,stackBottom
<<<<<<< HEAD

=======
        
>>>>>>> duals and variables now working with coopr. tests are still failing.
        if not fewunits:
            #group generators by kind
            allkinds=['nuclear','coal','naturalgas','wind','other']
            colors = dict(nuclear='PowderBlue',coal='SkyBlue',naturalgas='LightSlateGray',wind='SteelBlue',other='Aquamarine')
            genbykind=OrderedDict(zip(allkinds,[None]*len(allkinds)))
            for gen in generators:
                kind=gen.kind if gen.kind in allkinds else 'other'
                if genbykind[kind] is None:
                    genbykind[kind]=[value(gen.power(t)) for t in times.wInitial]
                else:
<<<<<<< HEAD
                    genbykind[kind]=elementwiseAdd([value(gen.P(t)) for t in times.wInitial],genbykind[kind])
<<<<<<< HEAD

=======
=======
                    genbykind[kind]=elementwiseAdd([value(gen.power(t)) for t in times.wInitial],genbykind[kind])
>>>>>>> fix for linear cost curves - now: cost=a*u+b*P
            
>>>>>>> duals and variables now working with coopr. tests are still failing.
            for kind,Pgen in genbykind.iteritems():
                if Pgen is None: continue
                gensPlotted,stackBottom=addtostackplot(ax,T,Pgen,colors[kind], gensPlotted,stackBottom)
                yLabels.append(kind)
<<<<<<< HEAD
        
        else: 
            #show all generators individually 
            #sort generators by merit order by 1.committed hrs (and then by 2. energy)
            generators=sorted(generators,reverse=True,
                key=lambda gen: 
                    ( sum(value(gen.u[t]) if hasattr(gen,'u') else 0 for t in times), #committed hrs
                      sum(value(gen.P(t)) for t in times) #energy
                    ))
            colors=colormap(len(generators),colormapName='Blues')
            for g,gen in enumerate(generators):
                Pgen=[value(gen.P(t)) for t in times.wInitial]
                gensPlotted,stackBottom=addtostackplot(ax,T,Pgen,colors[g], gensPlotted,stackBottom)
                yLabels.append(gen.name)      

        #show demand response loads
        stackBottom=stackBottom[1:] #loads don't have initial time info
        
        convert_to_GW=True if max(stackBottom)>20000 else False
        
=======
        
        else: 
            #show all generators individually 
            #sort generators by 1.committed hrs (and then by 2. energy)
#            generators=sorted(generators,reverse=True,
#                              key=lambda gen: 
#                              ( sum(value(gen.status(t)) for t in times), #committed hrs
#                               sum(value(gen.power(t)) for t in times) #energy
#                               ))
            colors=_colormap(len(generators),colormapName='Blues')
            for g,gen in enumerate(generators):
                Pgen=[gen.power(t) for t in times.wInitial]
                gensPlotted,stackBottom=addtostackplot(ax,T,Pgen,colors[g], gensPlotted,stackBottom)
                yLabels.append(gen.name)
        
        #show demand response loads
        stackBottom=stackBottom[1:] #loads don't have initial time info
        
        convert_to_GW=True if max(stackBottom)>20000 else False
        
<<<<<<< HEAD
>>>>>>> duals and variables now working with coopr. tests are still failing.
        for d,load in enumerate(loads):
=======
        for load in loads:
>>>>>>> cleanup
            color='.8' #gray
            if load.kind in ['shifting','bidding']:
                Pd=[value(load.power(t)) for t in times]
                stackBottom=elementwiseAdd([-1*P for P in Pd],stackBottom)
                plt=ax.bar(T[1:],Pd,bottom=stackBottom,alpha=.5,color=color,edgecolor=color,width=barWidth,hatch="/")
                loadsPlotted.append(plt[0])
                yLabels.append(load.name)
                if fewunits: colors.append(color)
                else: colors[load.kind] = color
            else: pass
        
        #show prices
        if withPrices and any(prices):
            prices=replace_all(prices, config.cost_load_shedding, None)
            prices_wo_none=[p for p in prices if p is not None]
            if prices_wo_none:
                axesPrice = plot.axes([figLeft,.75,figWidth,.2],sharex=ax)
                plt=axesPrice.step(T[1:]+[times.End],prices+[prices[-1]],  where='post') #start from 1 past initial time
                axesPrice.set_ylabel('price\n[$/MWh]',ha='center',**bigFont)
                axesPrice.yaxis.set_label_coords(**yLabel_pos)
                plot.setp(axesPrice.get_xticklabels(), visible=False)
                #format the price axis nicely
                plot.ylim((.9*min(prices_wo_none),1.1*max(prices_wo_none)))
                axesPrice.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(5))
                prettify_axes(axesPrice)
        ax.xaxis_date()
        plottedL=loadsPlotted[::-1]+gensPlotted[::-1]
        ax.legend(plottedL, yLabels[::-1],loc='lower right')
        
        for label in ax.get_xticklabels():
            label.set_ha('right')
            label.set_rotation(30)        
        
        #format the time axis nicely
        if filename is not None:
            if 24*7>times.spanhrs>48:
                ax.xaxis.set_major_locator(matplotlib.dates.DayLocator())
                ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%Y-%m-%d'))
                ax.xaxis.set_minor_locator(matplotlib.dates.HourLocator())
            elif times.spanhrs<48:
                ax.xaxis.set_major_locator(matplotlib.dates.HourLocator())
                ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H:%M'))
        #otherwise use defaults
        #else: leave the xaxis for interactive zooming  
        
        #format the power axis nicely
        if convert_to_GW:
            labels_power=ax.get_yticks()
            labels_power=[P/1000 for P in labels_power]
            ax.set_yticklabels(labels_power)
            ax.set_ylabel('energy [GWh]',ha='center',**bigFont)
        ax.autoscale_view()        
=======
        prices=[self.lmps[t][0] for t in self.times]
<<<<<<< HEAD
        stack_plot_UC(self.generators(),self.times,prices,withPrices=withPrices,withInitial=withInitial)

>>>>>>> moved UC visualization to independent function to allow for post solve vis. from csv for multi stage problems
=======
        stack_plot_UC(self.generators(),self.times,prices,self.datadir,withInitial,withPrices,seperate_legend)
>>>>>>> add seperate legend for UC viz. option
=======
=======
        
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
            
>>>>>>> clean up handling of solving for duals (no need to test for if need to resolve)
    def visualization(self,filename=None,withPrices=True,withInitial=False,filename_DR=None):
        '''generator output visualization for unit commitment'''
        if filename is None: filename=joindir(self.datadir,'commitment.png')
        prices=[self.lmps[str(t)][0] for t in self.times]
        stack_plot_UC(self.generators(),self.times,prices,self.datadir,withPrices=withPrices,withInitial=withInitial)
>>>>>>> setting up pympler test
        self.savevisualization(filename)
        DR_loads=filter(lambda d: getattr(d, 'kind','') in ['shifting','bidding','shifting-bidding'], self.loads())
        if DR_loads:
            interval= int(DR_loads[0].interval_hours) if (len(self.times)<=24 and len(DR_loads)==1 and 'shifting' in getattr(DR_loads[0], 'kind','')) else None
            stack_plot_UC(DR_loads,self.times,prices,withPrices=withPrices,hours_tick_interval=interval)
            if filename_DR is None: filename_DR=joindir(self.datadir,'commitment-DR.png')
            self.savevisualization(filename_DR)
        

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
        
        self._get_costs(stage_solutions)
        self._get_prices(stage_solutions)
    def _sum_over(self,attrib,stage_solutions): return sum(getattr(sln, attrib) for sln in stage_solutions)     
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
        return ['solved multistage problem in a in total of {time:0.4f} sec'.format(time=self.solve_time)]
    def info_shedding(self):
        return ['total load shed={}MW'.format(self.load_shed) if self.load_shed>0 else '']

<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
def get_stage_solution(problem,buses,times):
<<<<<<< HEAD
        solution=dict()
        solution['objective']=float(value(problem.objective))
        solution['solve-time']=problem.solutionTime
        solution['status'] = ( problem.status,problem.statusText() )
        solution['stagecost']               =sum(flatten(flatten([[[value(gen.cost(t)) for t in times] for gen in bus.generators] for bus in buses]) ))
        solution['fuelcost_generation']=sum(flatten(flatten([[[value(gen.operatingcost(t)) for t in times] for gen in bus.generators] for bus in buses]) ))
        solution['truecost_generation']=sum(flatten(flatten([[[value(gen.truecost(t))      for t in times] for gen in bus.generators] for bus in buses]) ))
        solution['load_shed']=0
        
        for t in times:
            sln=dict()
            for bus in buses: 
                sln['price_'+bus.iden(t)]=bus.getprice(problem.constraints,t)
                #reduce memory by setting variables to their value (instead of pulp object)
                if t==times[0]:
                    for gen in bus.generators: gen.fix_timevars(times)
                    for load in bus.loads: load.fix_timevars(times)
                for load in bus.loads:
                    shed=load.shed(t)
                    if shed: 
                        logging.warning('Load shedding of {} MWh occured at {}.'.format(shed,str(t.Start)))
                        solution['load_shed']+=shed
            
            solution[t]=sln
        return solution
=======
=======
def get_stage_solution(problem,buses,times,overlap_hours=0):
>>>>>>> fixed results with overlap, by adding non_overlap_times to each stage time
    solution=dict()
    solution['objective']=float(value(problem.objective))
    solution['solve-time']=problem.solutionTime
    solution['status'] = ( problem.status,problem.statusText )
    solution['fuelcost_generation']=sum(flatten(flatten([[[value(gen.operatingcost(t)) for t in times.non_overlap_times] for gen in bus.generators] for bus in buses]) ))
    solution['truecost_generation']=sum(flatten(flatten([[[value(gen.truecost(t))      for t in times.non_overlap_times] for gen in bus.generators] for bus in buses]) ))
    solution['load_shed']=0

    #reduce memory by setting variables to their value (instead of full Variable object)
    for bus in buses:
        for gen in bus.generators: gen.fix_vars(times,problem)
        for load in bus.loads: load.update_variables(times,problem)
    
    for t in times.non_overlap_times:
        sln=dict()
        for bus in buses: 
            sln['price_'+bus.iden(t)]=bus.getprice(t,problem)
            
            for load in bus.loads:
                shed=load.shed(t)
                if shed: 
                    logging.warning('Load shedding of {} MWh occured at {}.'.format(shed,str(t.Start)))
                    solution['load_shed']+=shed
        
        solution[t]=sln
    return solution
>>>>>>> duals and variables now working with coopr. tests are still failing.
=======

#def get_stage_solution(problem,power_system,times,overlap_hours=0):
#    solution=dict()
#    solution['objective']=float(value(problem.objective))
#    solution['solve time']=problem.solutionTime
#    solution['status'] = ( problem.status,problem.statusText )
#    solution['fuel cost generation']=sum(flatten(flatten([[[value(gen.operatingcost(t)) for t in times.non_overlap_times] for gen in bus.generators] for bus in buses]) ))
#    solution['true cost generation']=sum(flatten(flatten([[[value(gen.truecost(t))      for t in times.non_overlap_times] for gen in bus.generators] for bus in buses]) ))
#    solution['load shed']=0
#
#    #reduce memory by setting variables to their value (instead of full Variable object)
#    for bus in buses:
#        for gen in bus.generators: gen.fix_vars(times,problem)
#        for load in bus.loads: load.update_variables(times,problem)
#    
#    for t in times.non_overlap_times:
#        sln=dict()
#        for bus in buses: 
#            sln['price_'+bus.iden(t)]=bus.getprice(t,problem)            
#            for load in bus.loads:
#                shed=load.shed(t)
#                if shed: 
#                    logging.warning('Load shedding of {} MWh occured at {}.'.format(shed,str(t.Start)))
#                    solution['load_shed']+=shed
#        
#        solution[t]=sln
#    return solution

>>>>>>> rework of multistage results - testing
def write_last_stage_status(buses,stagetimes):
    t=stagetimes.initialTime
    logging.warning('saving stage status for its initial time: {}'.format(t.Start))
    generators = buses[0].generators
    
    fields,data=[],[]
    fields.append('generator name');  data.append(getattrL(generators,'name'))
    fields.append('u');  data.append([value(g.status(t)) for g in generators])
    fields.append('P');  data.append([value(g.power(t)) for g in generators])
    fields.append('hours in status');  data.append([value(g.initialStatusHours) for g in generators])
    writeCSV(fields,transpose(data),filename='stagestatus{}.csv'.format(t.End))          

def colormap(numcolors,colormapName='gist_rainbow',mincolor=1):
=======
def _colormap(numcolors,colormapName='gist_rainbow',mincolor=1):
>>>>>>> doc overhaul bidding
    cm = matplotlib.cm.get_cmap(colormapName)
    return [cm(1.*i/numcolors) for i in range(mincolor,numcolors+mincolor)]      

<<<<<<< HEAD
def stack_plot_UC(generators,times,prices,datadir,withInitial=False,withPrices=True,seperate_legend=False):
=======
def stack_plot_UC(generators,times,prices,
                  datadir=None,
                  withInitial=False,
                  withPrices=True,
                  seperate_legend=False,
                  hours_tick_interval=None
                  ):
>>>>>>> setting up pympler test
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
    
    T=[t.Start for t in times.wInitial]
    bar_width = times.intervalhrs / 24.0 #maplotlib dates have base of 1day
    initWidth = times.initialTime.intervalhrs / 24.0        
    stack_bottom=[0]*len(T)
    
    
    def addtostackplot(ax,time,power,color, gens_plotted,stack_bottom):
        #add initial time to stackplot
        if withInitial:
            ax.bar(time[0],power[0],bottom=stack_bottom[0],color=color, linewidth=.01, alpha=alpha_initialTime, width=initWidth)
        #add commitment times to stackplot
        plt=ax.bar(time[1:],power[1:],bottom=stack_bottom[1:],color=color, linewidth=.01, width=bar_width)
        #add power to stack bottom
        stack_bottom=elementwiseAdd(power,stack_bottom)
        #add to list of gens plotted
        gens_plotted.append(plt[0])
        return gens_plotted,stack_bottom
    
    if len(generators)<=5:
        colors=_colormap(len(generators),colormapName='Blues')
        for g,gen in enumerate(generators):
            if withInitial: Pgen=[gen.power(t) for t in times.wInitial]
            else: Pgen=[gen.power(t) if t!=times.initialTime else 0 for t in times.wInitial]
            gens_plotted,stack_bottom=addtostackplot(ax,T,Pgen,colors[g], gens_plotted,stack_bottom)
            legend_labels.append(gen.name)
    else:     
        #group generators by kind
        kind_map=dict(ngst='shoulder NG',ngcc='shoulder NG',nggt='peaker NG',chp='CHP')
        ordered_kinds=['nuclear','coal','CHP','other','shoulder NG','peaker NG','wind']
        colors=_colormap(len(ordered_kinds),colormapName='Blues')
        power_by_kind=OrderedDict(zip(ordered_kinds,[None]*len(ordered_kinds)))
        for gen in generators:
            kind=gen.kind.lower() if gen.kind.lower() in ordered_kinds else kind_map.get(gen.kind.lower(),'other')
            if power_by_kind[kind] is None:
                power_by_kind[kind]=[value(gen.power(t)) for t in times.wInitial]
            else:
                power_by_kind[kind]=elementwiseAdd([value(gen.power(t)) for t in times.wInitial],power_by_kind[kind])
        
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
            axes_price.step(T[1:]+[times.End],prices+[prices[-1]],  where='post') #start from 1 past initial time
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
    legend_font=FontProperties()
    legend_font.set_size('small')
    
    if seperate_legend:
        figlegend = plot.figure()
<<<<<<< HEAD
        figlegend.legend(plottedL, yLabels[::-1],prop=legend_font,loc='center')
        figlegend.savefig(joindir(datadir,'commitment-legend.png'))
        plot.close(figlegend)
    else:
        ax.legend(plottedL, yLabels[::-1],prop=legend_font)#,loc='center left', bbox_to_anchor=(1, 0.5))
    
=======
        figlegend.legend(plottedL, legend_labels[::-1],prop=legend_font,loc='center')
        figlegend.savefig(joindir(datadir,'commitment-legend.png'))
        plot.close(figlegend)
    else:
        ax.legend(plottedL, legend_labels[::-1],prop=legend_font)#,loc='center left', bbox_to_anchor=(1, 0.5))

>>>>>>> setting up pympler test
def shrink_axis(ax,percent_horizontal=0.20,percent_vertical=0):
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * (1-percent_horizontal), box.height*(1-percent_vertical)])
    
