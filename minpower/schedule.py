"""
Time and schedule related models.
"""

import dateutil
from commonscripts import hours,parseTime, readCSV,getclass_inlist, drop_case_spaces,transpose,frange,getattrL,getTimeFormat,writeCSV
from operator import attrgetter

class Time(object):
    """
    Describes a time interval.
    
    :param Start: time interval begins. A 
      :py:class:`datetime.datetime` object. 
      If a string is input, parsed using 
      :meth:`~commonscripts.parseTime`.
    :param End: time interval ends. Same parsing as :Start:.
    :param interval: the length of the time interval (optional).
      If specified :End: is optional. If not specified it is computed
      and stored as a :py:class:`datetime.timedelta` object.
    """
    def __init__(self,Start,End=None,interval=None,index=None,formatter=None):
        vars(self).update(locals()) #load in inputs
        if isinstance(Start, str): self.Start=parseTime(self.Start,formatter)
        if isinstance(End,   str): self.End=parseTime(self.End,formatter)
        
        if interval is None and End is None: self.End = self.Start + hours(1)
        if interval is None:   self.interval=self.End - self.Start
        elif End is None:      self.End=self.Start + self.interval
        else: #use both as check
            if self.End != self.Start + self.interval: 
                raise ValueError(
                '''End should be interval from Start: e!=s+i: 
                {e}!={s}+{i}
                {e}!={si}'''.format(e=self.End,s=self.Start,i=self.interval,si=self.Start + self.interval))
        self.intervalhrs=hours(self.interval)
    
    def Range(self,interval):
        intervalStepHrs=hours(interval)
        rangeLenHrs = hours(self.End-self.Start)
        return [self.Start + hours(t) for t in frange(0,rangeLenHrs,intervalStepHrs)]
    def time_passed_since(self,other): return self.End - other.Start
#    def __sub__(self, other): return self.End-other.Start
#    def __eq__(self, other): return self.__dict__ == other.__dict__ if type(other) is type(self) else False
#    def __ne__(self, other): return not self.__eq__(other)
#    def __cmp__(self, other): return self.__eq__(other) #cmp(self.Start,other.Start)
    def __str__(self): 
        try: return 't{ind:02d}'.format(ind=self.index)    
        except ValueError: return 't{ind}'.format(ind=self.index) #index is str    
    def __unicode__(self):
        return unicode(self.Start)+' to '+unicode(self.End)
    def __repr__(self): return repr(self.Start)
def make_times(datetimeL):
    '''convert list of :py:class:`datetime.datetime` objects to :class:`~schedule.Timelist` object'''
    S=datetimeL[0]
    I=datetimeL[1] - S #interval
    E=datetimeL[-1] + I #one past the last time
    times=Timelist(Start=S,End=E,interval=I)
    times.setInitial()
    return times

def make_times_basic(N):
    ''' make a :class:`schedule.Timelist` of N times, assume hourly interval.'''
    S=dateutil.parser.parse('0:00')
    I=dateutil.parser.parse('1:00')-S
    E=S+I*(N)    
    times=Timelist(Start=S,End=E,interval=I)
    times.setInitial()
    return times
    
class Timelist(object):
    """
    A container for :class:`schedule.Time` objects.
    
    :param list_of_times: a tuple, list, or existing :class:`~schedule.Timelist` object
    :param Start: a :py:class:`datetime.datetime` object
    :param End: a :py:class:`datetime.datetime` object
    :param interval: a :py:class:`datetime.timedelta` object
    
    If ``Start``, ``End``, ``interval`` are specified as 
    then a uniformly spaced list of times is generated. 
    Otherwise the list is created from ``list_of_times``.
    """
    def __init__(self, list_of_times=None,initialTime=None,Start=None,End=None,interval=None):
        if Start and End and interval:
            steps=hours(End-Start)/hours(interval)
            if steps==int(steps): steps=int(steps)
            else: raise ValueError('Times must be integer interval. j/i={j}/{i} must be an integer.'.format(i=hours(End-Start),j=hours(interval))) 
            self.times=[Time(Start=Start+i*interval,interval=interval,index=i) for i in range(steps)]
        else:                 
            self.times = ()
            if list_of_times is not None:
                if type(list_of_times) == type(self.times): self.times = list_of_times
                elif isinstance(list_of_times, Timelist): self.times = list_of_times.times[:]
                else: self.times = tuple(list_of_times)
        
        interval=self.times[0].interval
        
        for t in self.times: 
            if t.interval != interval: raise ValueError('time intervals within list varies at {t}. This time has interval {i}. List (1st element) has interval of {li}.:'.format(t=t.Start,i=t.interval,li=interval))
        else: 
            self.interval = interval
            self.intervalhrs = hours(self.interval)
            
        self.Start = self.times[0].Start
        self.End = self.times[-1].End
        self.span = self.End - self.Start
        self.spanhrs = hours(self.span)
        self.setInitial(initialTime)
        
    def __repr__(self): return repr(self.times)
    def __contains__(self, item): return item in self.times
    def __len__(self): return len(self.times)
    def __getitem__(self, i): return self.times[i]
    def __getslice__(self, i, j): return self.times[i:j]
    def index(self,val): return self.times.index(val)
    def setInitial(self,initialTime=None): 
        if initialTime: self.initialTime= initialTime
        else: self.initialTime = Time(Start=self.Start-self.interval, interval=self.interval,index='Init')
        self.wInitial = tuple([self.initialTime] + list(self.times))
    def subdivide(self,division_hrs=24,interval_hrs=None,overlap_hrs=0,offset_hrs=0):
        """
        Subdivide a list of times into serval stages,  each stage
        spanning `division_hrs` with intervals of `interval_hrs`.
        
        :param hoursperdivision: time span of each stage (excluding overlap)
        :param interval_hrs: (optional) time span of each interval
          for each stage. If not specified, `intervalhrs` is used.
        :param overlap_hrs: (optional) overlap between time stages, default is 0 
        
        typical use:
        
        >>> t=make_times_basic(8)
        >>> t.subdivide(division_hrs=4)
        [[1,2,3,4],[5,6,7,8]]
        
        but should also be able to handle longer intervals:
        
        >>> t.subdivide(division_hrs=4,interval_hrs=2)
        [[1,3],[5,7]]
        
        and handle arbitary overlaps:
        
        >>> t.subdivide(division_hrs=4,overlap_hrs=2)
        [[1,2,3,4,5,6],[4,5,6,7,8]]
        
        """
        def timeslice(tStart,tEnd,index): return Time(Start=tStart,End=tEnd,index=index)
        
        if interval_hrs is None: interval_hrs=self.intervalhrs
        span_intervals= division_hrs/interval_hrs
        overlap_intervals = overlap_hrs/interval_hrs
        offset_intervals = offset_hrs/interval_hrs
        intervals={'span':span_intervals,'overlap':overlap_intervals,'offset':offset_intervals}
        for nm,val in intervals.items():
            if val!=int(val): 
                msg='for time subdivision {nm} must be an integer number of intervals (is {val})'.format(nm=nm,val=val)
                raise ValueError(msg)
            intervals[nm]=int(val)
            
        if interval_hrs==self.intervalhrs and division_hrs==self.intervalhrs: return self
        elif interval_hrs==self.intervalhrs: 
            newtimesL=divide_into_stages(self,**intervals)
        elif interval_hrs>self.intervalhrs:
            steps=interval_hrs/self.intervalhrs
            if steps==int(steps): steps=int(steps)
            else: raise ValueError('Native Timelist interval is i={i}, while proposed interval is j={j}. j/i must be an integer.'.format(i=self.intervalhrs,j=interval_hrs))
            
            longertimeL = Timelist([timeslice(self[i].Start, self[i+steps-1].End,i) for i in range(0,len(self)-steps+1,steps)])
            newtimesL = divide_into_stages(longertimeL,**intervals)

        for t,stage in enumerate(newtimesL): 
            if t>0:        stage.setInitial( newtimesL[t-1][-1-intervals['overlap']] )
            elif t==0: stage.setInitial( self.initialTime )
            stage.non_overlap_times = stage[:-1-int(intervals['overlap'])+1] if intervals['overlap']>0 else stage
        else:
            #the last stage has no overlap and may not cover the whole division
            stage.non_overlap_times = stage
        return newtimesL
        

def divide_into_stages(L, span=0,overlap=0,offset=0):
    """divide list into stage_size-sized chunks, with optional overlap."""
    stages=[]
    for i in xrange(offset, len(L), span): 
        stages.append( Timelist(L[i:i+span+overlap]) )
    else:
        #the last stage has no overlap and can contain less than the full stage_size intervals
        stages[-1]=Timelist(L[i:])
    return stages
     
def make_schedule(filename,times=None):
    """
    Read time and power information from spreadsheet file.
    """
    time_column_names=['time','t','times']
    
    data,fields=readCSV(filename)
    if len(fields)!=2: raise ValueError('Schedules must be made from spreadsheets with two columns - time and amount.')
    time_col,amount_col=None,None
    for f,field in enumerate(fields): 
        if drop_case_spaces(field) in time_column_names: 
            time_col=f
            amount_col=f+1
            break
            
    data_power=transpose(data)[amount_col]
    if times is None: times=make_times(parse_timestrings(transpose(data)[time_col]))
    return Schedule(times,data_power)
    
class Schedule(object):
    """
    Describes a schedule of times and corresponding power values.
    A container for a dictionary keyed by
    :py:class:`~schedule.Time` objects.
    """
    def __init__(self,times=None,P=None):
        self.energy=dict(zip(times,P))
        self.interval=times.interval
        self.intervalhrs = times.intervalhrs
        self.maxvalue=max(self.energy.values())
    def __imul__(self,multiplier):
        """
        Multiplies each power value in schedule by a multiplier.        
        Usage: schedule*=.9 
        would give a schedule with 90 percent of the power.
        """
        for t,p in self.energy.items():
            self.energy[t]=p*multiplier
        return self
    def times(self):
        return Timelist(sorted(self.energy.keys(),key=attrgetter('Start','End')))
    def __repr__(self):
        return repr(sorted([(str(t),p) for t,p in self.energy.items()]))    
    def get_energy(self,timeperiod):
        """
        get the amount of energy in a time period 
        
        if the timeperiod is in the schedule things are simple:

        >>> times=Timelist([Time(Start='1:00'),Time(Start='2:00'),Time(Start='3:00')])
        >>> energy=[100,210,100]
        >>> s=Schedule(energy=energy,times=times)
        >>> s.get_energy(times[0])
        100

        If the timeperiod spans multiple schedule times, energy should
        be summed over each schedule time which the timeperiod contains:

        >>> tLarger=Time(Start='1:00',End='3:00')
        >>> s.get_energy(tLarger)
        310.0
        """
        try: return self.energy[timeperiod]
        except KeyError:
            times=self.energy.keys()
            if timeperiod.interval>self.interval: 
                #energy of time is sum all energy in times within
                tstarts=timeperiod.Range(self.interval)
                period_Times=getclass_inlist(times,tstarts,attribute='Start')
                return sum([self.get_energy(t) for t in period_Times]) *self.intervalhrs
            elif timeperiod.interval==self.interval:
                t=getattrL(times,'Start').index(timeperiod.Start)
                return self.get_energy(times[t])
            else: raise
    def saveCSV(self,filename='schedule.csv'):
        data=sorted(self.energy.items(),key=lambda t_e: t_e[0].Start)
        data=[(row[0].Start,row[1]) for row in data]
        fields=['times','energy']
        writeCSV(fields,data,filename=filename)
class FixedSchedule(Schedule):
    '''A simple "schedule" which has only one power output''' 
    def __init__(self,times=None,P=None): self.energy=P
    def get_energy(self,timeperiod=None): return self.energy
    def __repr__(self): return 'FixedSchedule<energy={}>'.format(self.energy)
def just_one_time():
    """For a single-time problem, generate a Timelist with just one time in it."""
    return Timelist([Time(Start='0:00',index=0)])
def parse_timestrings(timestringsL):
    """
    Convert list of strings to list of :py:class:`datetime.datetime`
    objects using :meth:`dateutil.parser.parse`.
    """
    fmt=getTimeFormat(timestringsL[0])
    return [dateutil.parser.parse(string,**fmt) for string in timestringsL]


if __name__ == "__main__":
    import doctest
    doctest.testmod()