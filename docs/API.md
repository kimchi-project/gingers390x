## Project Ginger S390x REST API Specification

The Ginger S390x API provides all functionality to the application and may be used
directly by external tools.  In the following sections you will find the
specification of all Collections and Resource types that are supported and the
URIs where they can be accessed.  In order to use the API effectively, please
the following general conventions:

* The **Content Type** of the API is JSON.  When making HTTP requests to this
  API you should specify the following headers:
    * Accept: application/json
    * Content-type: application/json
* A **Collection** is a group of Resources of a given type.
    * A **GET** request retrieves a list of summarized Resource representations
      This summary *may* include all or some of the Resource properties but
      *must* include a link to the full Resource representation.
    * A **POST** request will create a new Resource in the Collection. The set
      of Resource properties *must* be specified as a JSON object in the request
      body.
    * No other HTTP methods are supported for Collections
* A **Resource** is a representation of a singular object in the API (eg.
  Virtual Machine).
    * A **GET** request retrieves the full Resource representation.
    * A **DELETE** request will delete the Resource. This request *may* contain
      a JSON object which specifies optional parameters.
    * A **PUT** request is used to modify the properties of a Resource (eg.
      Change the name of a Virtual Machine). This kind of request *must not*
      alter the live state of the Resource. Only *actions* may alter live state.
    * A **POST** request commits an *action* upon a Resource (eg. Start a
      Virtual Machine). This request is made to a URI relative to the Resource
      URI. Available *actions* are described within the *actions* property of a
      Resource representation.  The request body *must* contain a JSON object
      which specifies parameters.
* URIs begin with '/plugins/gingers390x' to indicate the root of gingers390x plugin.
    * Variable segments in the URI begin with a ':' and should replaced with the
      appropriate resource identifier.


### Collection: Tasks

**URI:** /plugins/gingers390x/tasks

**Methods:**

* **GET**: Retrieve a summarized list of current Ginger s390x specific Tasks (stored
in Gingers390x's object store)

### Resource: Task

**URI:** /plugins/gingers390x/tasks/*:id*

A task represents an asynchronous operation that is being performed by the
server.

**Methods:**

* **GET**: Retrieve the full description of the Task
    * id: The Task ID is used to identify this Task in the API.
    * status: The current status of the Task
        * running: The task is running
        * finished: The task has finished successfully
        * failed: The task failed
    * message: Human-readable details about the Task status
    * target_uri: Resource URI related to the Task
* **POST**: *See Task Actions*

**Actions (POST):**

*No actions defined*

### Resource: CIO Ignore List(Blacklist)

**URI:** /plugins/gingers390x/cio_ignore

Contains information about black listed i/o devices.

**Methods:**

* **GET**: Retrieve cio ignore list
    * ignored_devices: List of device ids in ignore list

* **POST**: *See CIO Ignore list Actions*

**Actions (POST):**

* remove: Remove devices from ignore list in background and return
          a task resource * See Resource: Task *
    * devices: list of device ids(can be combination of individual device id or
               range of device ids) to be removed from ignore list

### Collection: Storage I/O devices

**URI:** /plugins/gingers390x/storagedevices

**Methods:**

* **GET**: Retrieve summarized list of defined IO storage devices of type dasd-eckd and zfcp
    * Parameters:
        * _type: Filter device list with given type, currently support
                        'dasd-eckd' and 'zfcp'.

### Resource: Storage I/O device

**URI:** /plugins/gingers390x/storagedevices/*:device*

**Methods:**

* **GET**: Retrieve information of the specified IO storage device.
    * device: Device ID of the device
    * status: status of the device
             * online:  The device is online.
             * offline: The device is offline.
    * cu_type: Control unit type and model of the device.
    * sub_channel: Sub channel bus id of the device.
    * device_type:  Device type and model of the device.
    * installed_chipids: installed CHIPIDs for the device
    * enabled_chipids: currently available CHIPIDs for the device

* **POST**: *See Storage I/O device Actions*

**Actions (POST):**

* online: Bring device online
* offline: Bring device offline

### Collection: Network I/O devices

**URI:** /plugins/gingers390x/nwdevices

**Methods:**

* **GET**: Retrieve summarized list of defined Network I/O devices of type OSA
    * Parameters:
        * _configured: Filter device list with configured or un-configured devices,
                       currently support 'True' and 'False'.

### Resource: Network I/O device

**URI:** /plugins/gingers390x/nwdevices/*:name*

**Methods:**

* **GET**: Retrieve information of the specified network i/o device.
    * name: Interface name of the device
    * state: Specifies current state of the interface
    * driver: Specifies device driver for the interface
    * device_ids: List of sub channels(network triplets) of the interface
    * type:  Device type and model of the interface.
    * card_tpe: Specifies type of the network adapter
    * chpid: CHPID of the interface

* **POST**: *See Network I/O device Actions*

**Actions (POST):**

* configure: Configure network device in background and return
             a task resource * See Resource: Task *
* unconfigure: Un-configure network device in background and return
               a task resource * See Resource: Task *


### Collection: Fiber Channel LUNs

URI: /plugins/gingers390x/fcluns

**Methods:**

* **GET**: Retrieve a summarized list of all FC LUNs

* **POST**: Add a LUN
       * hbaId : ID of the HBA
       * remoteWwpn : Remote port WWPN
       * lunId : ID of the LUN

### Resource: Fiber Channel LUN

URI: /plugins/gingers390x/fcluns/*:lun_path*

*Methods:**

* **GET**: Retrieve the full description of the FC LUN

       * status%: Online or offline
       * product: Product type
       * vendor:  Vendor of the storage controller
       * configured: True if added to system, otherwise False
       * hbaId : ID of the HBA
       * sgDev : If LUN is configured, corresponding sg_device
       * remoteWwpn : Remote ports WWPN
       * controllerSN : Serial Number of the Storage Controller
       * lunId : ID of the LUN
       * type : Could be 'disk', 'tape' etc.

* **DELETE**: Remove a LUN


### Resource: FC LUN Scanning Status

**URI:** /plugins/gingers390x/lunscan

**Methods:**

* **GET**: Retrieve a dictionary with the FC LUN scanning status:
    * boot: Status of the LUN Scanning in zipl.conf. Can be 'true' or 'false'.
    * current: Status of the LUN Scanning in running system. Can be 'true' or 'false'.

*Actions (POST):**

* enable: Enable FC LUN Scanning.
* disable: Disable FC LUN Scanning.
* trigger: Trigger a FC LUN Scan.


### SimpleCollection: List of Tape devices
 
**URI:** /plugins/ginger/lstapes
 
**Methods:**
 
* **GET**: Retrieve a summarized list of Tape devices

