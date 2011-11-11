"""
    Solution models, output, and display for power system
    optimization problems. Matplotlib and networkx are used for
    visualization.
"""

import logging
from collections import OrderedDict

from commonscripts import flatten,transpose,elementwiseAdd, getattrL,within,writeCSV,joindir,replace_all,update_attributes
from schedule import Timelist
from optimization import value,dual
import config

import matplotlib
import matplotlib.pyplot as plot

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
>>>>>>> doc overhaul bidding
    def __init__(self,power_system,times,problem,datadir='.'):
        update_attributes(self,locals(),exclude=['problem'])
        self.power_system.update_variables()
>>>>>>> major cleanup of results.py. still need to tackle the multistage commitments
        
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
        self._get_costs()

    def _get_problem_info(self,problem):
        self.status     =problem.statusText
        self.solve_time  =problem.solutionTime
        self.objective  =float(value(problem.objective))
        self.active_constraints = sum([dual(c)!=0 for c in problem.constraints.values()])
        self.total_constraints = len(problem.constraints)
    def _get_costs(self):
        generators=self.generators()
        gen_fuel_costs_pwlmodel   = [[value(gen.operatingcost(t)) for t in self.times] for gen in generators]
        gen_fuel_costs_polynomial = [[gen.truecost(t) for t in self.times] for gen in generators]
        self.fuelcost_generation=sum( c for c in flatten(gen_fuel_costs_pwlmodel) )
        self.truecost_generation=sum( c for c in flatten(gen_fuel_costs_polynomial) )
        self.load_shed = sum( sum(load.shed(t) for load in self.loads()) for t in self.times )
        self._get_cost_error()
    def _get_cost_error(self):
        try: self.costerror=abs(self.fuelcost_generation-self.truecost_generation)/self.truecost_generation
        except ZeroDivisionError: self.costerror=0
    def buses(self): return self.power_system.buses
    def lines(self): return self.power_system.lines
    def generators(self): return flatten( [[gen for gen in bus.generators] for bus in self.buses()] )
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
        else: plot.savefig(joindir(self.datadir,filename),bbox_inches='tight')
        plot.close()
    def show(self):
        '''Display the solution information to the terminal'''
        out=['']
        out.extend(['Solution information','-'*10,''])
        for t in self.times:
            out.append('{tm}: {start}'.format(tm=t,start=t.Start))
            out.extend(self.info_price(t))
            out.extend(self.info_generators(t))
            out.extend(self.info_loads(t))
            out.extend(self.info_buses(t))
            out.extend(self.info_lines(t))
        else:
            out.extend(self.info_cost())
            print '\n'.join(out)
    def info_status(self): return ['solved in {time:0.4f} sec'.format(time=self.solve_time)]
    def info_price(self,t): return ['price={}'.format(self.get_values('buses','price',t))]    
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
                'Pd={}'.format(self.get_values('generators','power',t))]
    def info_buses(self,t):
        buses=self.buses()
        out=['bus info:',
             'name={}'.format(getattrL(buses,'name')),
             'Pinj={}'.format([ bus.Pgen(t) - bus.Pload(t) for bus in buses]),
             'angle={}'.format(self.get_values('buses','angle',t)),
             'LMP={}'.format(self.get_values('buses','price',t))]    
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
             'price={}'.format(self.get_values('lines','price',t))]            
>>>>>>> major cleanup of results.py. still need to tackle the multistage commitments
    def info_cost(self):
        return ['objective cost={}'.format(self.objective),
        'linearized fuel cost of generation={}'.format(self.fuelcost_generation),
        ' non-linearized cost of generation={}'.format(self.truecost_generation),
        'percentage difference\t\t={diff:.2%}'.format(diff=self.costerror),
        ]


class Solution_ED(Solution):
    def info_lines(self,t): return []
    def info_buses(self,t): return []
    def vizualization(self,show_cost_also=False):
        ''' economic dispatch visualization of linearized incremental cost'''
        t=self.times[0]
        price=self.buses()[0].price(t)
        generators,loads=self.generators(),self.loads()
        
        gensPlotted,genNames,loadsPlotted,loadNames=[],[],[],[]
        minGen=min(getattrL(generators,'Pmin'))
        maxGen=max(getattrL(generators,'Pmax'))

        #save a plot of the price space - illustrating equal IC
        for gen in generators:
            if gen.status(t):
                gensPlotted.append( gen.cost_model.plot_derivative(P=value(gen.power(t)),linestyle='-') )
                genNames.append(gen.name)
        for load in loads: 
            if load.kind=='bidding': 
                loadsPlotted.append( load.bid(t).plot_derivative(P=value(load.power(t)),linestyle=':') )
                loadNames.append(load.name)
        if price is not None: 
            grayColor='.75'
            plot.plot([minGen,maxGen],[price,price],'--k',color=grayColor)
            plot.text(maxGen, price, '{p:0.2f} $/MWh'.format(p=price),color=grayColor,horizontalalignment='right')
        
        plot.xlabel('P [MWh]')        
        if loadsPlotted:     plot.ylabel('Marginal Cost-Benifit [$/MWh]')
        else:                plot.ylabel('Marginal Cost [$/MWh]')

        
        ymin,_ = plot.ylim()
        if ymin<0: plot.ylim(ymin=0)        

        legendGens=plot.legend(gensPlotted, genNames, fancybox=True,title='Generators:',loc='best')
        if loadsPlotted:
            plot.legend(loadsPlotted, loadNames, fancybox=True,title='Loads:',loc='best')
            plot.gca().add_artist(legendGens) #add first legend to the axes manually bcs multiple legends get overwritten
        
        self.savevisualization(filename='dispatch.png')
        
        if show_cost_also:
            #show a plot of the cost space, illustrating the linearization
            plot.figure()
            gensPlotted_price=gensPlotted
            gensPlotted,genNames,loadsPlotted,loadNames=[],[],[],[]
            for g,gen in enumerate(generators):
                if gen.status(t):
                    gensPlotted.append( gen.cost_model.plot(P=value(gen.power(t)),linestyle='-',color=gensPlotted_price[g].get_color()) )
                    genNames.append(gen.name)
            for load in loads: 
                if load.kind=='bidding': 
                    loadsPlotted.append( load.bid(t).plot(P=value(load.power(t)),linestyle=':') )
                    loadNames.append(load.name)        
            plot.xlabel('P [MWh]')
            if loadsPlotted:     plot.ylabel('Cost-Benifit [$/h]')
            else:                plot.ylabel('Cost [$/h]')
            legendGens=plot.legend(gensPlotted, genNames, fancybox=True,title='Generators:',loc='best')
            if loadsPlotted:
                plot.legend(loadsPlotted, loadNames, fancybox=True,title='Loads:',loc='best')
                plot.gca().add_artist(legendGens) #add first legend to the axes manually bcs multiple legends get overwritten
            
            self.savevisualization(filename='dispatch-cost.png')        
    def saveCSV(self,filename='dispatch.csv'):
        '''economic dispatch generator solution values in spreadsheet form'''
        t=self.times[0]
        generators=self.generators()
        
        fields,data=[],[]
        fields.append('generator name');  data.append(getattrL(generators,'name'))
        fields.append('u');  data.append([value(g.status(t)) for g in generators])
        fields.append('P');  data.append([value(g.power(t)) for g in generators])
        fields.append('IC');  data.append([g.incrementalcost(t) for g in generators])
        writeCSV(fields,transpose(data),filename=joindir(self.datadir,filename))        
class Solution_OPF(Solution): 
    def vizualization(self,filename='powerflow.png'): 
        '''power flow visualization'''
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
        
    def saveCSV(self,filename='powerflow'):
        '''OPF generator and line power values in spreadsheet form''' 
        t=self.times[0]
        
        fields,data=[],[]
        fields.append('generator name');  data.append(self.get_values('generators','name'))
        fields.append('u');  data.append(self.get_values('generators','status',t))
        fields.append('P');  data.append(self.get_values('generators','power',t))
        fields.append('IC');  data.append(self.get_values('generators','incrementalcost',t))
        writeCSV(fields,transpose(data),filename=joindir(self.datadir,filename+'-generators.csv'))           
        
        fields,data=[],[]
        fields.append('from');  data.append(self.get_values('lines','From'))
        fields.append('to');  data.append(self.get_values('lines','To'))
        fields.append('power'); data.append(self.get_values('lines','power',t))
        fields.append('congestion shadow price'); data.append(self.get_values('lines','price',t))
        writeCSV(fields,transpose(data),filename=joindir(self.datadir,filename+'-lines.csv'))        
    
    def info_price(self,t): return [] #built into bus info
class Solution_UC(Solution):
    def info_lines(self,t): return []
    def info_buses(self,t): return []
    def saveCSV(self,filename='commitment.csv'):
        '''generator power values and statuses for unit commitment'''
        times=self.times
        bus=self.buses()[0]
        fields,data=[],[]
        fields.append('times');  data.append([t.Start for t in times])
        fields.append('prices'); data.append([bus.price(t) for t in times])
        for gen in self.generators(): 
            if gen.isControllable:
                fields.append('status: '+str(gen.name))
                data.append([1 if value(gen.status(t))==1 else 0 for t in times])
            fields.append('power: '+str(gen.name))
            data.append([value(gen.power(t)) for t in times])
        for load in self.loads():
            fields.append('load power: '+str(load.name))
            data.append([value(load.power(t)) for t in times])
        
        writeCSV(fields,transpose(data),filename=joindir(self.datadir,filename))
    
    def vizualization(self,filename='commitment.png',withPrices=True):
        '''generator output visualization for unit commitment'''
        times,generators,loads=self.times,self.generators(),self.loads()
        if len(generators)<=5: fewunits=True
        else: fewunits=False
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
        
>>>>>>> duals and variables now working with coopr. tests are still failing.
        bigFont={'fontsize':15}
        figWidth=.85; figLeft=(1-figWidth)/2
        yLabel_pos={'x':-0.09,'y':0.5}
        
        plot.figure(figsize=(10, 4), dpi=120)
        ax=plot.axes([figLeft,.1,figWidth,.6])
        ax.set_ylabel('energy [MWh]',ha='center',**bigFont)
        ax.yaxis.set_label_coords(**yLabel_pos)
        
        alpha_initialTime=0.2
        
        gensPlotted,loadsPlotted,yLabels=[],[],[]
        
        T=[t.Start for t in times.wInitial]
        barWidth = times.intervalhrs / 24.0 #maplotlib dates have base of 1day
        initWidth = times.initialTime.intervalhrs / 24.0        
        stackBottom=[0]*len(T)
        
        
        def addtostackplot(ax,time,power,color, gensPlotted,stackBottom):
            #add initial time to stackplot
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
            generators=sorted(generators,reverse=True,
                              key=lambda gen: 
                              ( sum(value(gen.status(t)) for t in times), #committed hrs
                               sum(value(gen.power(t)) for t in times) #energy
                               ))
            colors=_colormap(len(generators),colormapName='Blues')
            for g,gen in enumerate(generators):
                Pgen=[value(gen.power(t)) for t in times.wInitial]
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
        self.savevisualization(filename)

class Solution_SCUC(Solution_UC):
    def vizualization(self): logging.warning('no visualization for SCUC. Spreadsheet output is valid, except for the price column is the price on first bus only.')
    
    
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
    def _sum_over(self,attrib,stage_solutions): return sum(getattr(sln, attrib) for sln in stage_solutions)     
    def _get_costs(self,stage_solutions):
        self.fuelcost_generation=self._sum_over('fuelcost_generation',stage_solutions)
        self.truecost_generation=self._sum_over('truecost_generation',stage_solutions)
        self.load_shed=          self._sum_over('load_shed',stage_solutions)
        self._get_cost_error()       

    def show(self):
        out=[]
        out.extend(self.info_status())
        out.extend(self.info_cost())
        out.extend(self.info_shedding())
        print '\n'.join(out)
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
