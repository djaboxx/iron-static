> **Source**: https://docs.cycling74.com/apiref/js/  
> **Fetched**: 2026-04-27  

# Max JS API

Reference for the API available within the `[js]`, `[jsui]`, `[v8]`, `[v8.codebox]`, and `[v8ui]` objects

## Classes

Item| Description  
---|---  
[Buffer](</apiref/js/buffer/> "Buffer")| Bind to a Max `buffer~` object.  
[Dict](</apiref/js/dict/> "Dict")| Bind to a Max `dict` object.  
[File](</apiref/js/file/> "File")| The File object provides a means of reading and writing files from JavaScript.  
[Folder](</apiref/js/folder/> "Folder")| Iterate through the files in a folder.  
[Global](</apiref/js/global/> "Global")| Global object for sharing data between Max JavaScript instances.  
[Image](</apiref/js/image/> "Image")| Bitmap image object handle  
[Jitter3dUtilsInterface](</apiref/js/jitter3dutilsinterface/> "Jitter3dUtilsInterface")| Utilities for Jitter 3D manipulations  
[JitterEvent](</apiref/js/jitterevent/> "JitterEvent")| The argument passed to a [JitterListener](</apiref/js/jitterlistener/> "JitterListener") callback function.  
[JitterListener](</apiref/js/jitterlistener/> "JitterListener")| A listener for changes in a [JitterObject](</apiref/js/jitterobject/> "JitterObject").  
[JitterMatrix](</apiref/js/jittermatrix/> "JitterMatrix")| A named matrix which may be used for data storage and retrieval, resampling, and matrix type and planecount conversion operations.  
[JitterObject](</apiref/js/jitterobject/> "JitterObject")| A JavaScript representation of a Jitter object in a patcher.  
[jsthis](</apiref/js/jsthis/> "jsthis")| The "this" object in the context of JavaScript in Max  
[LiveAPI](</apiref/js/liveapi/> "LiveAPI")| A means of communicating with the Live API from JavaScript.  
[Max](</apiref/js/max/> "Max")| Singleton Max object, controlling the Max environment.  
[Maxobj](</apiref/js/maxobj/> "Maxobj")| A JavaScript representation of a Max object in a patcher.  
[MaxobjConnection](</apiref/js/maxobjconnection/> "MaxobjConnection")| A JavaScript representation of a patchcord connection.  
[MaxobjListener](</apiref/js/maxobjlistener/> "MaxobjListener")| A listener for changes in a [Maxobj](</apiref/js/maxobj/> "Maxobj") object.  
[MaxobjListenerData](</apiref/js/maxobjlistenerdata/> "MaxobjListenerData")| The argument provided to a [MaxobjListener](</apiref/js/maxobjlistener/> "MaxobjListener") callback function.  
[MaxString](</apiref/js/maxstring/> "MaxString")| Bind a Max `string` object  
[MGraphics](</apiref/js/mgraphics/> "MGraphics")| Drawing context for rendering shapes and images.  
[MGraphicsSVG](</apiref/js/mgraphicssvg/> "MGraphicsSVG")| SVG object handle  
[ParameterInfoProvider](</apiref/js/parameterinfoprovider/> "ParameterInfoProvider")| Provides a list of named parameter objects within a patcher hierarchy as well as information about specific parameter objects. It can also notify when parameter objects are added or removed from a patcher hierarchy.  
[ParameterInfoProviderData](</apiref/js/parameterinfoproviderdata/> "ParameterInfoProviderData")| The argument to the [ParameterInfoProvider](</apiref/js/parameterinfoprovider/> "ParameterInfoProvider")'s callback function  
[ParameterListener](</apiref/js/parameterlistener/> "ParameterListener")| A listener for changes in named parameters.  
[ParameterListenerData](</apiref/js/parameterlistenerdata/> "ParameterListenerData")| The argument provided to a [ParameterListener](</apiref/js/parameterlistener/> "ParameterListener") callback function.  
[Patcher](</apiref/js/patcher/> "Patcher")| A JavaScript representation of a Max patcher.  
[Pattern](</apiref/js/pattern/> "Pattern")| Pattern object for drawing gradients and patterns.  
[PolyBuffer](</apiref/js/polybuffer/> "PolyBuffer")| Bind to a Max `polybuffer~` object.  
[ProgressEvent](</apiref/js/progressevent/> "ProgressEvent")| ProgressEvent provides information about the progress of a network request.  
[Sketch](</apiref/js/sketch/> "Sketch")| Interface to an OpenGL-backed drawing context  
[SnapshotAPI](</apiref/js/snapshotapi/> "SnapshotAPI")| Provides access to patcher snapshots.  
[SQLite](</apiref/js/sqlite/> "SQLite")| Provides access to the SQLite database system.  
[SQLResult](</apiref/js/sqlresult/> "SQLResult")| A container for results obtained in an [SQLite.exec()](</apiref/js/sqlite/#exec> "SQLite.exec\(\)") call.  
[Task](</apiref/js/task/> "Task")| A function that can be scheduled or repeated.  
[Wind](</apiref/js/wind/> "Wind")| A property of the [Patcher](</apiref/js/patcher/> "Patcher") which represents its window.  
[XMLHttpRequest](</apiref/js/xmlhttprequest/> "XMLHttpRequest")| XMLHttpRequest provides HTTP client functionality for making network requests from JavaScript in Max.  
  
## Enums

Item| Description  
---|---  
[Basic2dStrokeStyleParameterNames](</apiref/js/basic2dstrokestyleparameternames/> "Basic2dStrokeStyleParameterNames")| Stroke parameters for use with [Sketch.beginstroke()](</apiref/js/sketch/#beginstroke> "Sketch.beginstroke\(\)") in the "basic2d" drawing style  
[LineStrokeStyleParameterNames](</apiref/js/linestrokestyleparameternames/> "LineStrokeStyleParameterNames")| Stroke parameters for use with [Sketch.beginstroke()](</apiref/js/sketch/#beginstroke> "Sketch.beginstroke\(\)") in the "line" drawing style  
  
## Functions

Item| Description  
---|---  
[cpost](</apiref/js/cpost/> "cpost")| Prints a message to the system console window. See [post()](</apiref/js/post/> "post\(\)") for more details about arguments and formatting.  
[error](</apiref/js/error/> "error")| Prints a message to the Max console with a red tint. See [post()](</apiref/js/post/> "post\(\)") for more details about arguments and formatting.  
[messnamed](</apiref/js/messnamed/> "messnamed")| Sends a message to the named Max object.  
[post](</apiref/js/post/> "post")| Prints a representation of the arguments in the Max window.  
  
## Interfaces

Item| Description  
---|---  
[PointerEvent](</apiref/js/pointerevent/> "PointerEvent")| Pointer event object passed to onpointer* event handlers  
  
## Namespaces

Item| Description  
---|---  
[FileTypes](</apiref/js/filetypes/> "FileTypes")| Types used with  
[Jitter3dUtilsTypes](</apiref/js/jitter3dutilstypes/> "Jitter3dUtilsTypes")| Types used with [Jitter3dUtilsInterface](</apiref/js/jitter3dutilsinterface/> "Jitter3dUtilsInterface")  
[JitterEventTypes](</apiref/js/jittereventtypes/> "JitterEventTypes")| Possible event types for a [JitterEvent](</apiref/js/jitterevent/> "JitterEvent")  
  
## Type Aliases

Item| Description  
---|---  
[DrawingPrimitiveType](</apiref/js/drawingprimitivetype/> "DrawingPrimitiveType")| Primitive type to use for drawing shapes. See [Sketch.shapeprim()](</apiref/js/sketch/#shapeprim> "Sketch.shapeprim\(\)").  
[MGraphicsMatrixHandle](</apiref/js/mgraphicsmatrixhandle/> "MGraphicsMatrixHandle")| Opaque handle for an MGraphics transformation matrix.  
[MGraphicsPathHandle](</apiref/js/mgraphicspathhandle/> "MGraphicsPathHandle")| Opaque handle for an MGraphics path.
