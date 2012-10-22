"""
Stochastic scenario models for schedules. 
"""
from coopr.pysp.scenariotree import ScenarioTree
from coopr.pysp.ef import create_ef_instance
from coopr.pysp.phutils import construct_scenario_instance
from coopr.pyomo import Set,Var,AbstractModel,Param,Constraint
from coopr.pysp.util.scenariomodels import scenario_tree_model
from coopr import pyomo

from coopr.pyomo import *
from coopr.pysp.phutils import *
from math import fabs, ceil

from optimization import OptimizationProblem
import gc,logging
from commonscripts import *

from pprint import pprint



def construct_simple_scenario_tree(probabilities, time_stage=None):
    '''Construct a simple scenario tree instance'''
    tree=scenario_tree_model

    prob_set = range(len(probabilities))
    if time_stage is None:
        scenario_names=['s{n}'.format(n=n) for n in prob_set]
        node_names=['n{n}'.format(n=n) for n in prob_set]
    else:
        scenario_names=['s{n}t{t}'.format(n=n, t=time_stage) for n in prob_set]
        node_names=['n{n}t{t}'.format(n=n, t=time_stage) for n in prob_set]
        

    tree.Stages.add('first stage','second stage')
    tree.Nodes.add('root')
    for nm in node_names: tree.Nodes.add(nm)
    tree.NodeStage['root']='first stage'
    for nm in node_names: tree.NodeStage[nm]='second stage'
    tree.Children['root']=node_names
    
    tree.ConditionalProbability['root']=1.0
    for i,pr in enumerate(probabilities): tree.ConditionalProbability[node_names[i]]=pr

    for nm in scenario_names: tree.Scenarios.add(nm)        
    for i,nm in enumerate(scenario_names): tree.ScenarioLeafNode[nm]=node_names[i]
    # tree.Scenarios.pprint()

    # note that stage variables still need definition
    # as do the values of the per scenario variables
    if time_stage>0: debug()
    return tree

def define_stage_variables(scenario_tree,power_system,times):
    # scenario_tree.Stages.pprint()
    # scenario_tree.StageVariables.pprint()

    #create sets of variable names (not actual variables) for each stage
    variables_first_stage=Set()
    variables_second_stage=Set()

    for gen in filter(lambda gen: getattr(gen,'has_scenarios',False)==False, power_system.generators()):
        # for each non stochastic generator
        if gen.is_controllable: variables_first_stage.add(str(gen.get_variable('status',indexed=True,time=None))+'[*]')
        variables_second_stage.add(str(gen.get_variable('power',indexed=True,time=None))+'[*]')
        #note - appending '[*]' to the indicies is required to get pysp to assign all the variables in the array to a shape
        
    # variables_first_stage.pprint()
    scenario_tree.StageVariables['first stage']=variables_first_stage
    scenario_tree.StageVariables['second stage']=variables_second_stage
    
    #power_system._model=power_system._model.create()
    #power_system._model.pprint()
    scenario_tree.StageCostVariable['first stage']=str(power_system.cost_first_stage())
    scenario_tree.StageCostVariable['second stage']=str(power_system.cost_second_stage())

def create_problem_with_scenarios(power_system,times,scenariotreeinstance,stage_hours,overlap_hours, stage_number):
    
    # delete old time stage variables
    debug()
    
    #for node in scenariotreeinstance.nodes:
        
    
    scenario_tree = ScenarioTree(scenarioinstance=power_system._model, scenariotreeinstance=scenariotreeinstance)


    if scenario_tree.validate()==False: 
        for s,scenario in enumerate(scenario_tree._scenarios):
            print s,scenario
        debug()
        raise ValueError('not a valid scenario tree')
    
    #construct scenario instances
    # gc.disable()
    gen_w_scenarios = power_system.get_generator_with_scenarios()
    
    scenario_instances={}
    time_names = [str(time) for time in times]
    Nt = len(times)
    for s,scenario in enumerate(scenario_tree._scenarios):
        #print 'scenario: {s}'.format(s=s)
        scenario_instance=power_system._model.clone()
        
        power=getattr(scenario_instance,'power_{}'.format(str(gen_w_scenarios)))
        #set the values of the parameter for this scenario
        logging.debug('setting scenario values for s%i'%s)
        scenario_vals = gen_w_scenarios._get_scenario_values(times, s=s)        
        for t in range(Nt): power[time_names[t]] = scenario_vals[t]
        
        #power.pprint()
        scenario_instance.preprocess()
        scenario_instances[scenario._name] = scenario_instance    

    scenario_tree.defineVariableIndexSets(scenario_instances)
    full_problem_instance=create_ef_instance(scenario_tree, scenario_instances)
    #full_problem_instance.pprint()
    
    def relax_non_anticipatory_constraints(): 
        #relax the non-anticipatory constraints on the generator status variables beyond the UC time horizon
        for time in times.post_horizon(stage_hours):
            logging.debug('get rid of NA constraint at '+str(time))
            for scenario in scenario_instances.keys():
                for gen in power_system.generators():
                    if not gen.is_controllable: continue
                    u=gen.status().name
                    #print 'clear constraint on {s}_{u}_{t}'.format(s=scenario,u=u,t=str(time))
                    full_problem_instance._clear_attribute('{s}_{u}_{t}'.format(s=scenario,u=u,t=str(time)))
    
    
    relax_non_anticipatory_constraints()
    
    power_system.stochastic_formulation=True
    power_system._stochastic_instance=full_problem_instance
    power_system._scenario_tree=scenario_tree
    power_system._scenario_instances=scenario_instances
    return power_system

def get_scenario_based_costs(scenario_tree,scenario_instances):
    #scenario_tree.pprintCosts(scenario_instances)
    costs=dict()
    for node in scenario_tree._tree_node_map.values():
        scenarios=node._scenarios
        if len(scenarios)==1: costs[node._scenarios[0]._name]=node.computeExpectedNodeCost(scenario_instances)
        else: continue
    return costs

def update_variables(power_system,times):
    '''Convert all variables into dictionaries of their solved values, keyed by scenario'''
    first_scenario=True
    variable_names=power_system._model.active_components(Var).keys()
    values=dict([(nm,{}) for nm in variable_names])
    for s,scenario in power_system._scenario_instances.items():
        for var_name,var in scenario.active_components(Var).items():
            if var.is_indexed(): values[var_name][s]=dict([(idx,var_val.value) for idx,var_val in var.iteritems()])
            else: values[var_name][s]=var.value
    power_system._per_scenario_values=values
        # for param_name,param in scenario.active_components(Param).items():
        #     for time in times:
        #         name=param_name+"[{t}]".format(t=str(time))
        #         if first_scenario:
        #             power_system.variables[name]={scenario_name: param[str(time)].value}
        #         else:
        #             power_system.variables[name][scenario_name]= param[str(time)].value
        
        #values=[params[0]['P_g2'][str(self.times[0])].value ]
#    for tree_node_name,tree_node in sorted(problem.scenario_tree._tree_node_map.items()):
#        for variable_name, (variable, match_template) in tree_node._stage._variables.iteritems():
#            indices = sorted(tree_node._variable_indices[variable.name])
#            solution_variable = tree_node._solutions[variable.name]
#            if (len(indices) == 1) and (indices[0] == None):
#                # if this is a singleton variable, then it should necessarily be active -
#                # otherwise, it wouldn't be referenced in the stage!!!
#                value = solution_variable[None].value
#                print tree_node_name+" "+variable.name+"="+str(value)
