> **Source**: https://docs.cycling74.com/apiref/lom/groove/  
> **Fetched**: 2026-04-27  

# Groove

This class represents a groove in Live.   
  
_Available since Live 11.0._  
All grooves are stored in Live's groove pool.

## Canonical Paths
[code] 
    live_set groove_pool grooves N
    
[/code]
[code] 
    live_set tracks N clip_slots M clip groove
    
[/code]

## Children

### base int

Get/set the groove's base grid (index based setter).   
0 = 1/4   
1 = 1/8   
2 = 1/8T   
3 = 1/16   
4 = 1/16T   
5 = 1/32

### name symbol observe

Get/set/observe the name of the groove.

### quantization_amount float observe

Get/set/observe the groove's quantization amount.

### random_amount float observe

Get/set/observe the groove's random amount.

### timing_amount float observe

Get/set/observe the groove's timing amount.

### velocity_amount float observe

Get/set/observe the groove's velocity amount.
