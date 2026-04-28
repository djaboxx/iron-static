> **Source**: https://docs.cycling74.com/apiref/lom/chainmixerdevice/  
> **Fetched**: 2026-04-27  

# ChainMixerDevice

This class represents a chain's mixer device in Live.

## Canonical Paths
[code] 
    live_set tracks N devices M chains L mixer_device
    
[/code]
[code] 
    live_set tracks N devices M return_chains L mixer_device
    
[/code]

## Children

### sends list of [DeviceParameter](</apiref/lom/deviceparameter/> "DeviceParameter") read-onlyobserve

[in Audio Effect Racks and Instrument Racks only]   
For Drum Racks, otherwise empty.

### chain_activator [DeviceParameter](</apiref/lom/deviceparameter/> "DeviceParameter") read-only

### panning [DeviceParameter](</apiref/lom/deviceparameter/> "DeviceParameter") read-only

[in Audio Effect Racks and Instrument Racks only]

### volume [DeviceParameter](</apiref/lom/deviceparameter/> "DeviceParameter") read-only

[in Audio Effect Racks and Instrument Racks only]
