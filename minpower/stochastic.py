"""
Stochastic scenario models for schedules. 
"""
from coopr.pyomo import AbstractModel, Set, Param, Boolean, Var
from coopr.pysp.scenariotree import ScenarioTree
from coopr.pysp.ef import create_ef_instance
import gc, logging

def construct_simple_scenario_tree(probabilities, time_stage=None):
    '''Construct a simple scenario tree instance'''
    tree=new_scenario_tree_model()

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
    return tree

def define_stage_variables(scenario_tree, power_system, times):
    # scenario_tree.Stages.pprint()
    # scenario_tree.StageVariables.pprint()

    #create sets of variable names (not actual variables) for each stage
    variables_first_stage = Set()
    variables_second_stage = Set()

    for gen in power_system.get_generators_without_scenarios():
        # for each non stochastic generator
        if gen.is_controllable: 
            variables_first_stage.add(
                str(gen.get_variable('status',indexed=True,time=None))+'[*]')
            variables_second_stage.add(
                str(gen.get_variable('power',indexed=True,time=None))+'[*]')
        # note - appending '[*]' to the indicies is required to get 
        # pysp to assign all the variables in the array to a shape
        
    # variables_first_stage.pprint()
    scenario_tree.StageVariables['first stage'] = variables_first_stage
    scenario_tree.StageVariables['second stage'] = variables_second_stage
    
    #power_system._model=power_system._model.create()
    #power_system._model.pprint()
    scenario_tree.StageCostVariable['first stage'] = str(power_system.cost_first_stage())
    scenario_tree.StageCostVariable['second stage'] = str(power_system.cost_second_stage())

def create_problem_with_scenarios(power_system,times,scenariotreeinstance,stage_hours,overlap_hours, stage_number):
        
    #for node in scenariotreeinstance.nodes:
    
    scenario_tree = ScenarioTree(
        scenarioinstance=power_system._model, 
        scenariotreeinstance=scenariotreeinstance)


    if not scenario_tree.validate(): 
        for s,scenario in enumerate(scenario_tree._scenarios):
            print s,scenario
        raise ValueError('not a valid scenario tree')

    gen = power_system.get_generator_with_scenarios()
    
    scenario_instances = {}

    #construct scenario instances
    gc.disable()  
    for s,scenario in enumerate(scenario_tree._scenarios):
        scenario_instance = power_system._model.clone()
        
        power=getattr(scenario_instance,'power_{}'.format(str(gen)))
        #set the values of the parameter for this scenario
        logging.debug('setting scenario values for s%i'%s)
        scenario_vals = gen._get_scenario_values(times, s=s)        
        for t, time in enumerate(times): power[time] = scenario_vals[t]
        
        #power.pprint()
        scenario_instance.preprocess()
        scenario_instances[scenario._name] = scenario_instance    

    gc.enable()
    scenario_tree.defineVariableIndexSets(scenario_instances)
    full_problem_instance = create_ef_instance(scenario_tree, scenario_instances)
    # could generate cvar here
    #full_problem_instance.pprint()
    
    #relax the non-anticipatory constraints on the generator status variables beyond the UC time horizon
    for time in times.post_horizon():
        logging.debug('get rid of NA constraint at '+str(time))
        for scenario in scenario_instances.keys():
            for gen in power_system.generators():
                if not gen.is_controllable: continue
                u=gen.status().name
                #print 'clear constraint on {s}_{u}_{t}'.format(s=scenario,u=u,t=str(time))
                full_problem_instance._clear_attribute('{s}_{u}_{t}'.format(s=scenario,u=u,t=str(time)))
    
        
    power_system.stochastic_formulation = True
    power_system._stochastic_instance = full_problem_instance
    power_system._scenario_tree = scenario_tree
    power_system._scenario_instances = scenario_instances
    return power_system

def get_scenario_based_costs(scenario_tree,scenario_instances):
    #scenario_tree.pprintCosts(scenario_instances)
    costs=dict()
    for node in scenario_tree._tree_node_map.values():
        scenarios=node._scenarios
        if len(scenarios)==1: 
            costs[node._scenarios[0]._name] = \
                node.computeExpectedNodeCost(scenario_instances)
        else: 
            continue
    return costs

def update_variables(power_system,times):
    '''Convert all variables into dictionaries of their solved values, keyed by scenario'''
    variable_names = power_system._model.active_components(Var).keys()
    values=dict([(nm, {}) for nm in variable_names])
    for s, scenario in power_system._scenario_instances.items():
        for var_name, var in scenario.active_components(Var).items():
            if var.is_indexed(): 
                    values[var_name][s] = dict(
                        [(idx, var_val.value) for idx, var_val in var.iteritems()])
            else: 
                    values[var_name][s] = var.value
    power_system._per_scenario_values = values


def new_scenario_tree_model():
    # https://software.sandia.gov/trac/coopr/browser/coopr.pysp/trunk/coopr/pysp/util/scenariomodels.py
    scenario_tree_model = AbstractModel()

    # all set/parameter values are strings, representing the names of various entities/variables.

    scenario_tree_model.Stages = Set(ordered=True)
    scenario_tree_model.Nodes = Set()

    scenario_tree_model.NodeStage = Param(scenario_tree_model.Nodes,
        within=scenario_tree_model.Stages)
    scenario_tree_model.Children = Set(scenario_tree_model.Nodes,
        within=scenario_tree_model.Nodes, ordered=True)
    scenario_tree_model.ConditionalProbability = Param(
        scenario_tree_model.Nodes)

    scenario_tree_model.Scenarios = Set(ordered=True)
    scenario_tree_model.ScenarioLeafNode = Param(scenario_tree_model.Scenarios,
        within=scenario_tree_model.Nodes)

    scenario_tree_model.StageVariables = Set(scenario_tree_model.Stages)
    scenario_tree_model.StageCostVariable = Param(scenario_tree_model.Stages)

    # scenario data can be populated in one of two ways. the first is "scenario-based",
    # in which a single .dat file contains all of the data for each scenario. the .dat
    # file prefix must correspond to the scenario name. the second is "node-based",
    # in which a single .dat file contains only the data for each node in the scenario
    # tree. the node-based method is more compact, but the scenario-based method is
    # often more natural when parameter data is generated via simulation. the default
    # is scenario-based.
    scenario_tree_model.ScenarioBasedData = Param(within=Boolean,
        default=True, mutable=True)

    # do we bundle, and if so, how?
    scenario_tree_model.Bundling = Param(within=Boolean,
        default=False, mutable=True)
    scenario_tree_model.Bundles = Set() # bundle names
    scenario_tree_model.BundleScenarios = Set(scenario_tree_model.Bundles)
    
    return scenario_tree_model
