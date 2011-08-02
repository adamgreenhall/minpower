"""
Solution models, output, and display for power system
optimization problems. Matplotlib and networkx are used for
vizualization.
"""
	
import os,sys,types,logging
from collections import OrderedDict

from commonscripts import flatten,getColumn,transpose,elementwiseAdd, getattrL,hours,within,subset,writeCSV,colormap,joindir
from schedule import Timelist
from optimization import value,dual

import matplotlib
import matplotlib.pyplot as plot

def classifyProblem(times=None,lines=None):
    if not lines and len(times)==1: kind='ED'
    elif len(times)==1:    kind='OPF'
    elif not lines:        kind='UC'
    else: kind='SCUC'    
    return kind

def makeSolution(lines=None,times=None,**kwargs):
    kindMap=dict(ED=Solution_ED, OPF=Solution_OPF, UC=Solution_UC, SCUC=Solution_SCUC)
    kind=classifyProblem(times,lines)
    classMaker=kindMap[kind]
    return classMaker(lines=lines,times=times,**kwargs)

def makeMultistageSolution(lines,**kwargs):
    if lines: raise NotImplementedError('no visualization for multistage SCUC yet')
    return Solution_multistageUC(**kwargs)
    
class Solution(object):
    def __init__(self,problem,buses,lines,times,datadir):
        vars(self).update(subset(locals(),['buses','lines','times','datadir']))
        self.generators=flatten( [[gen for gen in bus.generators] for bus in buses] )
        self.loads     =flatten( [[ld  for ld   in bus.loads]     for bus in buses] )
        self.constraints= problem.constraints
        self.solveTime  =problem.solutionTime
        self.status     =problem.statusText()
        self.solved        =problem.status==1
        
        if not self.solved: 
            logging.error('Problem solve was not completed. Status {s}.'.format(s=self.status))
            return
        
        self.objective  =float(value(problem.objective))
        self.activeConstraints = sum([dual(c)!=0 for nm,c in problem.constraints.items()])
        self.totalConstraints = len(problem.constraints)
        self.calcCosts()
        self.calcPrices(problem.constraints)
    def show(self):
        if not self.solved: return
        print '\nSolution information:\n----------------------'
        for t in self.times:
            print '{tm}: {start}'.format(tm=t,start=t.Start)
            self.info_price(t)
            self.info_generators(t)
            self.info_loads(t)
            self.info_buses(t)
            self.info_lines(t)
        self.info_cost()               

    def savevisualization(self,filename=None):
        if not self.solved: return
        if filename is None: plot.show()
        else: plot.savefig(joindir(self.datadir,filename),bbox_inches='tight')
        plot.close()

    def info_status(self):
        if self.solved: print('{stat} in {time:0.4f} sec'.format(stat=self.status,time=self.solveTime))
        else: print(self.solveStatus)
    def info_price(self,t):
        print ' price=', [ bus.price[t] for bus in self.buses ]    
    def info_generators(self,t):
        print ' generator info:'
        if len(self.generators)<10:
            if len(self.buses)>1: print '  bus={L}'.format(L=getattrL(self.generators,'bus'))
            print '  name=', getattrL(self.generators,'name')
            print '  u=',   [value(gen.u[t]) if gen.isControllable else ' ' for gen in self.generators]
            if len(self.times)>1: print '  du=', [value(gen.startup[t]) or value(gen.shutdown[t]) if gen.isControllable else ' ' for gen in self.generators]
            print '  Pg=',  [value(gen.P(t)) for gen in self.generators]
            print '  IC=', [gen.incrementalcost(t) for gen in self.generators]
        else: #lots of generators
            activeGens = [gen for gen in self.generators if hasattr(gen,'u') or not gen.isControllable]
            print '  name=', [gen.name for gen in activeGens]
            print '  Pg=',  [value(gen.P(t)) for gen in activeGens]
            print '  IC=', [gen.incrementalcost(t) for gen in activeGens]    
    def info_loads(self,t):
        print ' load info:'
        print '  bus={}'.format(getattrL(self.loads,'bus')) if len(self.buses)>1 else ''
        print '  name=', getattrL(self.loads,'name')
        print '  Pd=',   [value(load.P(t)) for load in self.loads]
    def info_buses(self,t):
        print ' bus info:'
        print '  name =', getattrL(self.buses,'name')
        print '  Pinj =', [ value(bus.Pgen(t)) - value(bus.Pload(t)) for bus in self.buses]
        if len(self.buses)>1: print '  angle =', [ value(bus.angle[t]) for bus in self.buses]
        print '  LMP  =', [ bus.price[t] for bus in self.buses ]        
    def info_lines(self,t):
        print ' line info:'
        print '  connecting=', zip(getattrL(self.lines,'From'),getattrL(self.lines,'To'))            
        print '  Pk =', [value(line.P[t]) for line in self.lines]
        
        try: duals=[dual(self.constraints['lineLimitHi_'+line.iden(t)])+dual(self.constraints['lineLimitLow_'+line.iden(t)]) for line in self.lines]
        except TypeError: duals=None #from duals not supported
        print '  mu=', duals
    def calcCosts(self):
        self.fuelcost_generation=float(sum( flatten([[value(gen.operatingcost(t)) for t in self.times] for gen in self.generators]) ))
        self.truecost_generation=float(sum( flatten([[gen.truecost(t) for t in self.times] for gen in self.generators]) ))
        try: self.costerror=abs(self.fuelcost_generation-self.truecost_generation)/self.truecost_generation
        except ZeroDivisionError: self.costerror=0
    def calcPrices(self,constraints):
        for bus in self.buses:
            for t in self.times:    
                bus.price[t] = dual(constraints['powerBalance_'+bus.iden(t)])        
    def info_cost(self):
        print 'objective cost=',self.objective
        print 'linearized fuelcost of generation=',self.fuelcost_generation
        print 'non-linearized cost of generation=',self.truecost_generation
        print 'percentage difference\t\t={diff:.2%}'.format(diff=self.costerror)

    
class Solution_ED(Solution):
    def __init__(self,**kwargs):
        super( Solution_ED, self ).__init__(**kwargs)    
        #for ED problem there is just one price
        self.price=self.buses[0].price[self.times[0]]
        
    def info_lines(self,t): pass
    def info_buses(self,t): pass
    def vizualization(self):
        ''' economic dispatch visualization '''
        if not self.solved: return
        t=self.times[0]
        price=self.price
        generators,loads=self.generators,self.loads
        
        gensPlotted,genNames,loadsPlotted,loadNames=[],[],[],[]
        minGen=min(getattrL(generators,'Pmin'))
        maxGen=max(getattrL(generators,'Pmax'))
        if price is not None: 
            grayColor='.75'
            plot.plot([minGen,maxGen],[price,price],'--k',color=grayColor)
            plot.text(maxGen, price, '{p:0.2f} $/MWh'.format(p=price),color=grayColor,horizontalalignment='right')
        for gen in generators:
            if gen.u[t]:
                gensPlotted.append( gen.costModel.plotDeriv(P=value(gen.P(t)),linestyle='-') )
                genNames.append(gen.name)
        for load in loads: 
            if load.kind=='bidding': 
                loadsPlotted.append( load.bid[t].plotDeriv(P=value(load.P(t)),linestyle=':') )
                loadNames.append(load.name)
        legendGens=plot.legend(gensPlotted, genNames, fancybox=True,title='Generators:',loc='upper right')
        if loadsPlotted:
            legendLoads=plot.legend(loadsPlotted, loadNames, fancybox=True,title='Loads:',loc='upper left')
            plot.gca().add_artist(legendGens) #add first legend to the axes manually bcs multiple legends get overwritten

        plot.xlabel('P [MWh]')
        plot.ylabel('Marginal Cost/Benifit [$/MWh]')
        plot.ylim(ymin=0)        
        
        self.savevisualization(filename='marginalCostWorth.png')    
    def saveCSV(self,filename='dispatch.csv'):
        if not self.solved: return
        t=self.times[0]
        generators,loads=self.generators,self.loads
            
        fields,data=[],[]
        fields.append('generator name');  data.append(getattrL(generators,'name'))
        fields.append('u');  data.append([value(g.u[t]) for g in generators])
        fields.append('P');  data.append([value(g.P(t)) for g in generators])
        fields.append('IC');  data.append([g.incrementalcost(t) for g in generators])
            
        writeCSV(fields,transpose(data),filename=joindir(self.datadir,filename))        
class Solution_OPF(Solution): 
    def vizualization(self): 
        if not self.solved: return
        import networkx as nx
        buses,lines,t=self.buses,self.lines,self.times[0]
        
        G=nx.DiGraph()
        for bus in buses:
            Pinj=value(bus.Pgen(t)) - value(bus.Pload(t))
            G.add_node(bus.name, Pinj=Pinj)
        for line in lines:
            P=value(line.P[t])
            if P>=0: G.add_edge(line.From,line.To,P=P,Plim=line.Pmax)
            else: G.add_edge(line.To,line.From,P=-P,Plim=-line.Pmin)
        
        pos=nx.spectral_layout(G)
        Pinj=[ndata['Pinj'] for bus,ndata in G.nodes(data=True) if 'Pinj' in ndata]
        nx.draw(G,node_color=Pinj,pos=pos,node_size=1500,alpha=.7,cmap=plot.cm.RdYlBu,fontsize=30)
        cb=plot.colorbar(shrink=.8)
        cb.set_label('injected power [MW]',fontsize=15)
            
        Plines=[edata['P'] for f,t,edata in G.edges(data=True) if 'P' in edata]
        atLimLines=[(f,t) for f,t,edata in G.edges(data=True) if within(edata['P'],val=edata['Plim'],eps=1e-3) ]
        nx.draw_networkx_edges(G,edge_color='0.6',pos=pos,width=Plines,alpha=0.5)
        nx.draw_networkx_edges(G,edgelist=atLimLines,edge_color='r',pos=pos,width=Plines,alpha=0.5)
                
        self.savevisualization(filename='powerflow.png')
    def saveCSV(self,filename='powerflow'): 
        t=self.times[0]
        generators,loads,lines=self.generators,self.loads,self.lines
            
        fields,data=[],[]
        fields.append('generator name');  data.append(getattrL(generators,'name'))
        fields.append('u');  data.append([value(g.u[t]) for g in generators])
        fields.append('P');  data.append([value(g.P(t)) for g in generators])
        fields.append('IC');  data.append([g.incrementalcost(t) for g in generators])
        writeCSV(fields,transpose(data),filename=joindir(self.datadir,filename+'-generators.csv'))           
        
        fields,data=[],[]
        fields.append('from');  data.append(getattrL(lines,'From'))
        fields.append('to');  data.append(getattrL(lines,'To'))
        fields.append('power'); data.append([value(line.P[t]) for line in lines])

        try: duals=[dual(self.constraints['lineLimitHi_'+line.iden(t)])+dual(self.constraints['lineLimitLow_'+line.iden(t)]) for line in self.lines]
        except TypeError: duals=['not supported']*len(lines) #from duals not supported
        fields.append('congestion shadow price'); data.append(duals)
        writeCSV(fields,transpose(data),filename=joindir(self.datadir,filename+'-lines.csv'))        
    
    def info_price(self,t): pass #built into bus info
class Solution_UC(Solution):
    def info_lines(self,t): pass
    def info_buses(self,t): pass
    def saveCSV(self,filename='commitment.csv'): 
        if not self.solved: return
        times=self.times
            
        fields,data=[],[]
        fields.append('times');  data.append([t.Start for t in times])
        fields.append('prices'); data.append([self.buses[0].price[t] for t in times])
        for gen in self.generators: 
            if gen.isControllable:
                fields.append('status: '+str(gen.name));
                data.append([value(gen.u[t]) for t in times])
            fields.append('power: '+str(gen.name));
            data.append([value(gen.P(t)) for t in times])
        #for load in self.loads:
        #    fields.append(str(load.name)+' power');
        #    data.append([value(load.P(t)) for t in times])
            
        writeCSV(fields,transpose(data),filename=joindir(self.datadir,filename))
        
    def vizualization(self,**kwargs):
        if not self.solved: return
        if len(self.generators)<5: 
            self.vizualization_fewunits(**kwargs)
        else: vizualization_bykind(**kwargs)
    def vizualization_bykind(self,withPrices=True,filename='commitment.png'):
        times,generators,loads=self.times,self.generators,self.loads
        prices=[self.buses[0].price[t] for t in self.times]

        
        bigFont={'fontsize':15}
        figWidth=.85; figLeft=(1-figWidth)/2
        yLabel_pos={'x':-0.09,'y':0.5}
        
        fig=plot.figure(figsize=(10, 4), dpi=120)
        ax=plot.axes([figLeft,.1,figWidth,.6])
        ax.set_ylabel('energy [MWh]',ha='center',**bigFont)
        ax.yaxis.set_label_coords(**yLabel_pos)
        
        #for plotting group generators by kind
        allkinds=['nuclear','coal','naturalgas','wind','other']
        genbykind=OrderedDict(zip(allkinds,[None]*len(allkinds)))
        for gen in generators:
            kind=gen.kind if gen.kind in allkinds else 'other'
            if genbykind[kind] is None:
                genbykind[kind]=[value(gen.P(t)) for t in times.wInitial]
            else:
                genbykind[kind]=elementwiseAdd([value(gen.P(t)) for t in times.wInitial],genbykind[kind])
        
        T=[t.Start for t in times.wInitial]
        barWidth = times.intervalhrs / 24.0 #maplotlib dates have base of 1day
        initWidth = times.initialTime.intervalhrs / 24.0
        
        stackBottom=[0]*len(T)
        colors = dict(nuclear='LightSlateGrey',coal='DarkGrey',naturalgas='Gainsboro',wind='LightGreen',other='Beige')
        
        gensPlotted,loadsPlotted,yLabels=[],[],[]
        
        for kind,Pgen in genbykind.iteritems():
            if Pgen is None: continue
            ax.bar(T[0],Pgen[0],bottom=stackBottom[0],color=colors[kind], alpha=.2,edgecolor=colors[kind],width=initWidth) #initial time only
            
            
            plt=ax.bar(T[1:],Pgen[1:],bottom=stackBottom[1:],color=colors[kind], alpha=1,edgecolor=colors[kind],width=barWidth)
            gensPlotted.append(plt[0])
            stackBottom=elementwiseAdd(Pgen,stackBottom)
            yLabels.append(kind)
        else: 
            stackBottom=stackBottom[1:] #loads don't have initial time info
            #if max(stackBottom)>20000: #could convert to GW here
        
        for d,load in enumerate(loads):
            color='.8'
            if load.kind in ['shifting','bidding']:
                Pd=[value(load.P(t)) for t in times]
                stackBottom=elementwiseAdd([-1*P for P in Pd],stackBottom)
                plt=ax.bar(T[1:],Pd,bottom=stackBottom,alpha=.5,color=color,edgecolor=color,width=barWidth,hatch="/")
                loadsPlotted.append(plt[0])
                yLabels.append(load.name)
                colors.append(color)
            else: pass
        
        
        if withPrices:        
            axesPrice = plot.axes([figLeft,.75,figWidth,.2],sharex=ax)
            plt=axesPrice.step(T[1:]+[times.End],prices+[prices[-1]],  where='post') #start from 1 past initial time
            axesPrice.set_ylabel('price\n[$/h]',ha='center',**bigFont)
            axesPrice.yaxis.set_label_coords(**yLabel_pos)
            plot.setp(axesPrice.get_xticklabels(), visible=False)
            axesPrice.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(5))
            
        ax.xaxis_date()
        plottedL=loadsPlotted[::-1]+gensPlotted[::-1]
        ax.legend(plottedL, yLabels[::-1])#,loc='upper left')
        
        for label in ax.get_xticklabels():
            label.set_ha('right')
            label.set_rotation(30)        
        
        if filename is not None:
            if 24*7>times.spanhrs>48:
                ax.xaxis.set_major_locator(matplotlib.dates.DayLocator())
                ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%d-%m-%Y'))
                ax.xaxis.set_minor_locator(matplotlib.dates.HourLocator())
            elif times.spanhrs<24:
                ax.xaxis.set_major_locator(matplotlib.dates.HourLocator())
                ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H:%M'))
            #otherwise use defaults
        #else: leave the xaxis for interactive zooming  
        ax.autoscale_view()        
        self.savevisualization(filename)        
    def vizualization_fewunits(self,withPrices=True,filename='commitment.png'):
        times,generators,loads=self.times,self.generators,self.loads
        prices=[self.buses[0].price[t] for t in self.times]

        
        bigFont={'fontsize':15}
        figWidth=.85; figLeft=(1-figWidth)/2
        yLabel_pos={'x':-0.09,'y':0.5}
        
        fig=plot.figure(figsize=(10, 4), dpi=120)
        ax=plot.axes([figLeft,.1,figWidth,.6])
        ax.set_ylabel('energy\nMWh',ha='center',**bigFont)
        ax.yaxis.set_label_coords(**yLabel_pos)
        
        #for plotting sort generators by merit order by 1.committed hrs (and then by 2. energy)
        generators=sorted(generators,reverse=True,
            key=lambda gen: 
                ( sum(value(gen.u[t]) if hasattr(gen,'u') else 0 for t in times), #committed hrs
                  sum(value(gen.P(t)) for t in times) #energy
                ))
        
        T=[t.Start for t in times.wInitial]
        barWidth = times.intervalhrs / 24.0 #maplotlib dates have base of 1day
        initWidth = times.initialTime.intervalhrs / 24.0
        
        stackBottom=[0]*len(T)
        colors=colormap(len(generators),colormapName='Blues')
        gensPlotted,loadsPlotted,yLabels=[],[],[]
        
        for g,gen in enumerate(generators):
            Pgen=[value(gen.P(t)) for t in times.wInitial]
            ax.bar(T[0],Pgen[0],bottom=stackBottom[0],color=colors[g], alpha=.2,edgecolor=colors[g],width=initWidth) #initial time only
            plt=ax.bar(T[1:],Pgen[1:],bottom=stackBottom[1:],color=colors[g], alpha=1,edgecolor=colors[g],width=barWidth)
            gensPlotted.append(plt[0])
            stackBottom=elementwiseAdd(Pgen,stackBottom)
            yLabels.append(gen.name)
        else: stackBottom=stackBottom[1:] #loads don't have initial time info
        for d,load in enumerate(loads):
            color='.8'
            if load.kind in ['shifting','bidding']:
                Pd=[value(load.P(t)) for t in times]
                stackBottom=elementwiseAdd([-1*P for P in Pd],stackBottom)
                plt=ax.bar(T[1:],Pd,bottom=stackBottom,alpha=.5,color=color,edgecolor=color,width=barWidth,hatch="/")
                loadsPlotted.append(plt[0])
                yLabels.append(load.name)
                colors.append(color)
            else: pass
        
        if withPrices:        
            axesPrice = plot.axes([figLeft,.75,figWidth,.2],sharex=ax)
            plt=axesPrice.step(T[1:]+[times.End],prices+[prices[-1]],  where='post') #start from 1 past initial time
            axesPrice.set_ylabel('price\n$/h',ha='center',**bigFont)
            axesPrice.yaxis.set_label_coords(**yLabel_pos)
            plot.setp(axesPrice.get_xticklabels(), visible=False)
            axesPrice.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(5))
            
        ax.xaxis_date()
        plottedL=loadsPlotted[::-1]+gensPlotted[::-1]
        ax.legend(plottedL, yLabels[::-1])#,loc='upper left')
        
        for label in ax.get_xticklabels():
            label.set_ha('right')
            label.set_rotation(30)        
        
        if filename is not None:
            if 24*7>times.spanhrs>48:
                ax.xaxis.set_major_locator(matplotlib.dates.DayLocator())
                ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%d-%m-%Y'))
                ax.xaxis.set_minor_locator(matplotlib.dates.HourLocator())
            elif times.spanhrs<24:
                ax.xaxis.set_major_locator(matplotlib.dates.HourLocator())
                ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H:%M'))
            #otherwise use defaults
        #else: leave the xaxis for interactive zooming  
        ax.autoscale_view()        
        self.savevisualization(filename)

class Solution_SCUC(Solution):
    def info_price(self,t): pass #built into bus info
    def vizualization(self): raise NotImplementedError('need to implement vizualization for SCUC')
    def saveCSV(self,filename='commitment.csv'): raise NotImplementedError
class Solution_multistageUC(Solution_UC):
    def __init__(self,problemsL,times,stageTimes,buses,datadir):
        vars(self).update(locals())
        self.times=Timelist(flatten([list(tL) for tL in stageTimes]))
        self.times.setInitial(stageTimes[0].initialTime)
        if all([p.status==1 for p in problemsL]): 
            self.status = p.statusText()
            self.solved = 1
        self.objective = float(value(sum([p.objective for p in problemsL])))
        self.solveTime = sum([p.solutionTime for p in problemsL])
        constraints = dict()
        for p in problemsL: constraints.update(p.constraints)
        self.activeConstraints = sum([dual(c)!=0 for nm,c in constraints.items()])
        self.totalConstraints = len(constraints)
        self.generators=flatten( [[gen for gen in bus.generators] for bus in buses] )
        self.loads     =flatten( [[ld  for ld   in bus.loads]     for bus in buses] )
        self.calcCosts()
        self.calcPrices(constraints)        
    def show(self):
        self.info_status()
        if not self.solved: return
        self.info_cost()
        self.vizualization()
    def info_status(self):
        if self.solved: print('{stat} in total of {time:0.4f} sec'.format(stat=self.status,time=self.solveTime))
        else: print(self.solveStatus)
