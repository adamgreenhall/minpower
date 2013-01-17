'''
Make two scenarios equal to the forecast, with equal probability
'''
import pandas as pd
forecast = pd.read_csv('wind_forecast.csv', 
    parse_dates=True, index_col=0, squeeze=True)
tz = forecast.index.tz
days = pd.date_range(forecast.index[0], forecast.index[-1], 
    freq='D', tz=tz)[:-1] - pd.DateOffset(hours=6)

for day in days:
    periods = 36 if day < days[-1] else 23
    trange = pd.date_range(day, periods=periods, freq='H', tz=tz)
    fcst = forecast.ix[trange]
    
    scenarios = pd.DataFrame([fcst.values, fcst.values], 
        index=[0,1], columns=[str(t) for t in fcst.index])
    scenarios['probability'] = [0.5, 0.5]
    scenarios.index.name = 'scenario'
    scenarios.to_csv('scenarios/scenarios-{}.csv'.format(day.date()))
