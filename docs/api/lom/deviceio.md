> **Source**: https://docs.cycling74.com/apiref/lom/deviceio/  
> **Fetched**: 2026-04-27  

# DeviceIO

This class represents an input or output bus of a Live device.

## Properties

### available_routing_channels dictionary read-onlyobserve

The available channels for this input/output bus. The channels are represented as a _dictionary_ with the following key:   
`available_routing_channels` [list]   
The list contains _dictionaries_ as described in _routing_channel_.

### available_routing_types dictionary read-onlyobserve

The available types for this input/output bus. The types are represented as a _dictionary_ with the following key:   
`available_routing_types` [list]   
The list contains _dictionaries_ as described in _routing_type_.

### default_external_routing_channel_is_none bool

1 = the default routing channel for External routing types is none.   
  
_Available since Live 11.0._

### routing_channel dictionary observe

The current routing channel for this input/output bus. It is represented as a _dictionary_ with the following keys:   
`display_name` [symbol]   
`identifier` [symbol]   
Can be set to any of the values found in _available_routing_channels._

### routing_type dictionary observe

The current routing type for this input/output bus. It is represented as a _dictionary_ with the following keys:   
`display_name` [symbol]   
`identifier` [symbol]   
Can be set to any of the values found in _available_routing_types._
