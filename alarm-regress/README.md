# Alarm-regress Development Utility Tools
  
## alarm-regress:

Regression script to read alarm definition spec and create and validate alarms in VSD.
NOTE: This script uses CloudMgmt-Sim (XMPP CLient) and jmsclient (JMS Messages Consumer)

### Setup

1. Download and extract [jmsclient](https://github.mv.usa.alcatel.com/CNA/javalib/tree/master/javalib-jmsclient) 
        Note: No setup required.

2. Clone and compile CNA-Server (alarm-regression needs CloudMgmt-sim from CNA project)

3. Update alarm-regress/alarmregress.properties

     3.1. jmsclient home

     3.2. cloudmgmt home

     3.3. vsd server ip & hostname

Step 4: Run regression (use -help for more options)

```
     alarm-regerss/runAlarmRegression.py
```

### Usage

```
Usage   : ./runAlarmRegression.py [Option]
          Option -list : list all alarm definitions
                 -name {alarm-name} : run regression for specific alarm name
                 -code {alarm-code} : run regression for specific alarm code
                 -mo {mo-name} : run regression for specific managed object
Example : ./runAlarmRegression.py -name MAC_LOOP_ERROR

```
