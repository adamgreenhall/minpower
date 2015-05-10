from minpower.config import user_config, parse_command_line_config
from minpower.get_data import _load_raw_data, _parse_raw_data, setup_times
from minpower.commonscripts import joindir, set_trace
from minpower.powersystems import PowerSystem
from minpower.solve import create_solve_problem
import pandas as pd
import argparse


def initial_dispatch(directory='.', output_filename='initial.csv'):
    user_config.directory = directory
    user_config.dispatch_decommit_allowed = True

    generators_data, loads_data, lines_data, init_data = _load_raw_data()

    init_data = pd.DataFrame()

    timeseries, times, generators_data, loads_data = \
        setup_times(generators_data, loads_data)

    # get rid of a bunch of stuff to make this an ED problem
    generators_data['power'] = None
    loads_data['power'] = None
    for i, snm in generators_data.pop('schedulename').dropna().iterkv():
        generators_data.ix[i, 'power'] = timeseries[snm].values[0]

    for i, snm in loads_data.pop('schedulename').dropna().iterkv():
        loads_data.ix[i, 'power'] = timeseries[snm].values[0]

    for i, snm in generators_data.pop('observedname').dropna().iterkv():
        generators_data.ix[i, 'power'] = timeseries[snm].values[0]

    valid_columns = pd.Index([
        'name', 'pmin', 'pmax',
        'fuelcost', 'heatrateequation', 'costcurveequation',
        'sheddingallowed',
        'power'])

    generators_data = generators_data[generators_data.columns & valid_columns]

    generators, loads, lines, times, scenario_values, data = \
        _parse_raw_data(generators_data, loads_data,
                        lines_data, init_data)

    power_system = PowerSystem(generators, loads, lines)
    sln = create_solve_problem(power_system, times)

    # save a csv of the dispatch
    dispatch = pd.DataFrame({
        'power': sln.generators_power.ix[0].values,
        'status': sln.generators_status.ix[0].values},
        index=[gen.name for gen in sln.generators])
    dispatch.ix[dispatch.status == 0, 'power'] = 0
    dispatch.index.name = 'name'
    dispatch.to_csv(joindir(user_config.directory, output_filename))

    print(dispatch)


def main():
    parser = argparse.ArgumentParser('Initial dispatch tool',
                                     description='''Get the initial dispatch for a case. Runs a economic
        dispatch for the first hour of a commitment problem, but allows 
        generators to turn off to minimize cost.''')
    parser.add_argument('--output_filename', default='initial.csv')

    # parse all of the standard minpower options
    args = parse_command_line_config(parser)
    initial_dispatch(args['directory'], args['output_filename'])

if __name__ == '__main__':
    main()
