> **Source**: https://docs.cycling74.com/apiref/lom/compressordevice/  
> **Fetched**: 2026-04-27  

# CompressorDevice

This class represents a Compressor device in Live.   
A CompressorDevice shares all of the children, functions and properties of a Device; listed below are the members unique to it.

## Properties

### available_input_routing_channels dict read-onlyobserve

The list of available source channels for the compressor's input routing in the sidechain. It's represented as a dictionary with the following key:   
`available_input_routing_channels` [list]   
The list contains dictionaries as described in _input_routing_channel_.

### available_input_routing_types dict read-onlyobserve

The list of available source types for the compressor's input routing in the sidechain. It's represented as a dictionary with the following key:   
`available_input_routing_types` [list]   
The list contains dictionaries as described in _input_routing_type_.

### input_routing_channel dict observe

The currently selected source channel for the compressor's input routing in the sidechain. It's represented as a dictionary with the following keys:   
`display_name` [symbol]   
`identifier` [symbol]   
Can be set to all values found in the compressor's _available_input_routing_channels_.

### input_routing_type dict observe

The currently selected source type for the compressor's input routing in the sidechain. It's represented as a dictionary with the following keys:   
`display_name` [symbol]   
`identifier` [symbol]   
Can be set to all values found in the track's _available_input_routing_types_.
