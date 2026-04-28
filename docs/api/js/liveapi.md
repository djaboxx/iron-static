> **Source**: https://docs.cycling74.com/apiref/js/liveapi/  
> **Fetched**: 2026-04-27  

# class LiveAPI

A means of communicating with the Live API from JavaScript.

For background information on this functionality, please see the Live API Overview and Live Object Model documents, as well as the Reference pages for live.path, live.object and live.observer objects, which provide the same basic functionality as the LiveAPI object, but from the Max patcher.

Technical note: you cannot use the LiveAPI object in JavaScript global code. Use the live.thisdevice object to determine when your Max Device has completely loaded (the object sends a bang from its left outlet when the Device is fully initialized, including the Live API).

Legacy note: previous versions of the LiveAPI object required the `jsthis` object's `this.patcher` property as the first argument. For backward-compatibility, this first argument is still supported, but is no longer necessary.

Beginning with release 6.0 of Max, it is no longer possible to configure JavaScript functions to run in the high-priority thread of Max's scheduler. The LiveAPI object cannot be created or used in the high-priority thread, so users should be sure to use the defer or deferlow objects to re-queue messages to the js object.

#### Example
[code] 
    var api = new LiveAPI(sample_callback, "live_set tracks 0");
    if (!api) {
        post("no api object\n");
        return;
    }
    post("api.mode", api.mode ? "follows path" : "follows object", "\n");
    post("api.id is", api.id, "\n");
    post("api.path is", api.path, "\n");
    post("api.children are", api.children, "\n");
    post('api.getcount("devices")', api.getcount("devices"), "\n");
    
    api.property = "mute";
    post("api.property is", api.property, "\n");
    post("type of", api.property, "is", api.proptype, "\n");
    
    function sample_callback(args) {
        post("callback called with arguments:", args, "\n");
    }
    
[/code]

## Constructors
[code] 
    new LiveAPI(callback?: Function, path?: string);
    
[/code]

Constructs a new instance of the `LiveAPI` class

Parameter| Type| Description  
---|---|---  
 _optional_ callback| Function| a function to be called when the LiveAPI object refers to a new object in Live (if the LiveAPI object's path changes, for instance) or when an observed property changes  
 _optional_ path| string| the object in Live pointed to by the LiveAPI object (e.g. `"live_set tracks 0 devices 0"`) or a valid LiveAPI object id  
  
## Properties

### children string[]

An array of children of the object at the current path

### id number

The id of the Live object referred to by the LiveAPI object. These ids are dynamic and awarded in realtime from the Live application, so should not be stored and used over multiple runs of Max for Live.

### info string read-only

A description of the object at the current path, including id, type, children, properties and functions

### mode number

The follow mode of the LiveAPI object. 0 (default) means that LiveAPI follows the object referred to by the path, even if it is moved in the Live user interface.

For instance, consider a Live Set with two tracks, "Track 1" and "Track 2", left and right respectively. If your LiveAPI object's path is live_set tracks 0, the left-most track, it will refer to "Track 1". Should the position of "Track 1" change, such that it is now to the right of "Track 2", the LiveAPI object continues to refer to "Track 1". A mode of 1 means that LiveAPI updates the followed object based on its location in the Live user interface. In the above example, the LiveAPI object would always refer to the left-most track, updating its id when the object at that position in the user interface changes.

### patcher [Patcher](</apiref/js/patcher/> "Patcher") read-only

The patcher of the LiveAPI object, as passed into the constructor

### path string

The path to the Live object referred to by the LiveAPI object.

These paths are dependent on the currently open Set in Live, but are otherwise stable: `live_set tracks 0 devices 0` will always refer to the first device of the first track of the open Live Set.

### property string

The observed property, child or child-list of the object at the current path, if desired

For instance, if the LiveAPI object refers to "live_set tracks 1", setting the property to "mute" would cause changes to the "mute" property of the 2nd track to be reported to the callback function defined in the LiveAPI Constructor.

### proptype string read-only

The type of the currently observed property or child

The types of the properties and children are given in the Live Object Model.

### type string read-only

The type of the object at the current path

Please see the Live API Overview and Live Object Model documents for more information.

### unquotedpath string

The path to the Live object referred to by the LiveAPI object, without any quoting (the path property contains a quoted path)

These paths are dependent on the currently open Set in Live, but are otherwise stable: live_set tracks 0 devices 0 will always refer to the first device of the first track of the open Live Set.

### valid number read-only

Whether the LiveAPI object refers to a valid Live object

## Methods

### call

Calls the given function of the current object, optionally with a list of arguments.
[code] 
    call(fn: string, ...arguments: any[]): any;
    
[/code]

Name| Type| Description  
---|---|---  
fn| string| the name of the Live API function to call  
arguments| any[]| any arguments to the function  
Return Value| any|   
  
### get

Returns the value or list of values of the specified property of the current object.
[code] 
    get(property: string): number | number[];
    
[/code]

Name| Type| Description  
---|---|---  
property| string| the object's property  
Return Value| number | number[]|   
  
### getcount

The count of children of the object at the current path
[code] 
    getcount(child: string): number;
    
[/code]

Name| Type| Description  
---|---|---  
child| string| the child to count children of  
Return Value| number|   
  
### getstring

Returns the value or list of values of the specified property of the current object as a String object.
[code] 
    getstring(property: string): string | string[];
    
[/code]

Name| Type| Description  
---|---|---  
property| string| the object's property  
Return Value| string | string[]|   
  
### goto

Navigates to the path and causes the id of the object at that path out be sent to the callback function defined in the Constructor. If there is no object at the path, id 0 is sent.
[code] 
    goto(path: string): void;
    
[/code]

Name| Type| Description  
---|---|---  
path| string|   
  
### set

Sets the value or list of values of the specified property of the current object.
[code] 
    set(property: string, value: any): void;
    
[/code]

Name| Type| Description  
---|---|---  
property| string| the object's property to set  
value| any| the new value or values of the property
