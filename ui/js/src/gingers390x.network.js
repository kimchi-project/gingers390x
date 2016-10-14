/*
 * Project Ginger S390x
 *
 * Copyright IBM Corp, 2015-2016
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
gingers390x.network = {};
gingers390x.selectedNWInterface = [];
gingers390x.selectedNWrows = [];
gingers390x.selectedNWtype = 0;
gingers390x.initNetwork = function() {
  gingers390x.initBlacklist(gingers390x.RefreshNetworkBootGridData);
  gingers390x.initNetworkBootgrid(i18n['GS390XNW001E']);

};

gingers390x.initNetworkBootgrid = function(actionButtonText) {

  var opts = [];
  opts['containerId'] = 'network-content-container';
  opts['gridId'] = "network-table-grid";

  var headers = [{
    "column-id": 'name',
    'title': i18n['GS390XNW002E'],
    "type": 'string',
    "identifier": true,
    "width": "20%"
  }, {
    "column-id": 'chpid',
    'title': i18n['GS390XNW003E'],
    "type": 'string',
    "width": "15%"
  }, {
    "column-id": 'card_type',
    'title': i18n['GS390XNW004E'],
    "type": 'string',
    "width": "25%"
  }, {
    "column-id": 'device_ids',
    'title': i18n['GS390XNW005E'],
    "type": 'string',
    "width": "35%"
  }];

  opts['headers'] = JSON.stringify(headers);

  gingers390x.initHeader(opts);
  gingers390x.initBootgrid(opts);
  gingers390x.hideBootgridData(opts); //This will hide  No reaord found till data is not appended.

  //Add on click event
  $('#osaport-add-submit').on('click', function(event) {
    gingers390x.disableActionButton();
    gingers390x.enableNetworks(opts);
    event.preventDefault();
  });

  gingers390x.initNetworkBootGridData(opts);
  gingers390x.finishAction(opts);

  $('#network-refresh-btn').on('click', function(event) {
    gingers390x.disableActionButton();
    gingers390x.initNetworkBootGridData(opts);
    event.preventDefault();
  });
  $('#network-enable-btn').on('click', function(event) {
    var selectedRowIds = gingers390x.getSelectedRows(opts);
    if (selectedRowIds.length > 0) {
        $('#network-enable-btn').attr('href', 'plugins/gingers390x/host-network-add-osaport.html');
        $('#network-enable-btn').attr('data-toggle', 'modal');
        $('#network-enable-btn').attr('data-target', '#network-Addosa-modal');
        gingers390x.cleanModalDialog();
    } else {
        wok.message.error(i18n['GS390XNW008E'], '#alert-modal-nw-container', true);
        gingers390x.enableActionButton();
        gingers390x.hideBootgridLoading(opts);
        gingers390x.showBootgridData(opts);
    }
  });
};

gingers390x.initNetworkBootGridData = function(opts) {

  var result = [];
  gingers390x.disableActionButton();
  gingers390x.clearBootgridData(opts);
  gingers390x.clearFilterData();
  gingers390x.hideBootgridData(opts); //This will hide  No record found till data is not appended.
  opts['loadingMessage'] = i18n['GS390XNW006E'];
  gingers390x.showBootgridLoading(opts);

  gingers390x.listNetworks(function(result) {

    function stringifyNestedObject(key, value) {
      if (key === "device_ids" && typeof value === "object") {
        value = value.join(',');
      }
      return value;
    }

    stringify_result = JSON.stringify(result, stringifyNestedObject);
    stringify_result = JSON.parse(stringify_result);

    gingers390x.loadBootgridData(opts, stringify_result);

    if (stringify_result && stringify_result.length > 0) {
      gingers390x.enableActionButton();
    } else {
      // This need to be in else block to avoid showing no-record-found
      // for a second if data is present.
      gingers390x.hideBootgridLoading(opts);
      gingers390x.showBootgridData(opts);
    }
  }, function(error){
    gingers390x.hideBootgridLoading(opts);
    gingers390x.showBootgridData(opts);
    wok.message.error(error.responseJSON.reason, '#alert-modal-nw-container', true);
  });
};

gingers390x.enableNetworks = function(opts,osaval) {
  var osaport = {};
  osaport.osa_portno = parseInt(osaval);
  var selectedRowIds = gingers390x.getSelectedRows(opts);
  if (selectedRowIds.length > 0) {
    opts['loadingMessage'] = i18n['GS390XNW007E'];
    gingers390x.showBootgridLoading(opts);

    var taskAccepted = false;
    var onTaskAccepted = function() {
      if (taskAccepted) {
        return;
      }
      taskAccepted = true;
      wok.topic('gingers390x/enableNetworks').publish();
    };

    var totalRowsSelected = selectedRowIds.length;
    for (var i = 0; i < selectedRowIds.length; i++) {
      gingers390x.configureNetwork(osaport,selectedRowIds[i], true, function(result) {
        onTaskAccepted();
        var successText = result['message'];
        wok.message.success(successText, '#alert-modal-nw-container');
        totalRowsSelected = totalRowsSelected - 1;
        if (totalRowsSelected == 0)
		gingers390x.enableNetworksCompleted(opts);
      }, function(result) {
        if (result['message']) {
          var errText = result['message'];
        } else {
          var errText = result['responseJSON']['reason'];
        }
        result && wok.message.error(errText, '#alert-modal-nw-container', true);
        taskAccepted;
        totalRowsSelected = totalRowsSelected - 1;
        if (totalRowsSelected == 0)
          gingers390x.enableNetworksCompleted(opts);
      }, onTaskAccepted);
    }
  } else {
    wok.message.error(i18n['GS390XNW008E'], '#alert-modal-nw-container', true);
    gingers390x.enableActionButton();
    gingers390x.hideBootgridLoading(opts);
    gingers390x.showBootgridData(opts);
  }

};

//Function triggers when all devices enable is completed and refresh the parent page
gingers390x.enableNetworksCompleted = function(opts) {
	gingers390x.initNetworkBootGridData(opts);
    ginger.listNetworkConfig.refreshNetworkConfigurationDatatable();
    ginger.listNetworkConfig.rows_indexes = new Array();
    setTimeout(function(){
      gingers390x.networkRefreshHandler();
      gingers390x.networkConfigRowSelection();
    },3000);
    $('#network-configuration-content-area').on('shown.bs.dropdown','.nw-configuration-add',function(){
      if(!($('#nw-add-adapter-button',$(this)).length))
        gingers390x.addNetworkAdapterButton();
    });
    $('#network-configuration-content-area').on('shown.bs.dropdown', '.nw-configuration-action', function() {
      if (!($('#nw-osa-port-button', $(this)).length))
        gingers390x.addOSAportButton();
    });
}

gingers390x.finishAction = function(opts) {
  $("#s390x-network-finish").on('click', function(event) {
    var selectedRowIds = gingers390x.getSelectedRows(opts);

    var settings = {
      content: i18n['GS390XFN001E'],
      confirm: i18n['GS390XFN002E'],
      cancel: i18n['GS390XFN003E']
    };

    if (selectedRowIds.length > 0) {
      wok.confirm(settings, function() {
        $('#network-enable-btn').trigger("click");
      }, function() {
        gingers390x.deselectAll(opts);
        $('#s390x-network-finish').trigger("click");
      });
    } else {
      $(this).attr('data-dismiss', 'modal');
      return true;
    }
  });
};

gingers390x.enableActionButton = function() {
  $('#network-enable-btn').prop("disabled", false);
  $('#network-refresh-btn').prop("disabled", false);
};

gingers390x.disableActionButton = function() {
  $('#network-enable-btn').prop("disabled", true);
  $('#network-refresh-btn').prop("disabled", true);
};

// function to refresh network boot gird data which can be called from blacklist.js
gingers390x.RefreshNetworkBootGridData = function(){
  var opts = {
    gridId: 'network-table-grid',
    loadingMessage: i18n['GS390XBG003E']
  };
  gingers390x.initNetworkBootGridData(opts);
};

gingers390x.addNetworkAdapterButton = function() {
    var btnHTML = [
      '<li role="presentation" class="" >',
      '<a role="menuitem" tabindex="-1" data-backdrop="static"  data-keyboard="false" data-dismiss="modal" id="nw-add-adapter-button"',
      '>',
      '<i class="fa fa-plus-circle"></i>',
      i18n['GINNET0008M'],
      '</a></li>'
    ].join('');
    var btnNode = $(btnHTML).appendTo($('.dropdown-menu', $('.nw-configuration-add')));
    $('button', $('.nw-configuration-add')).css('width','152px');

    $('#nw-add-adapter-button').on('click', function() {
      wok.window.open('plugins/gingers390x/network.html');
    });
    $('.nw-configuration-add').show();
}
gingers390x.addOSAportButton = function() {
    var btnHTML = [
        '<li role="presentation" class="" >',
        '<a role="menuitem" tabindex="-1" data-backdrop="static"  data-keyboard="false" data-dismiss="modal" id="nw-osa-port-button"',
        '>',
        '<i class="fa fa-pencil"></i>',
        i18n['GS390XOSA004M'],
        '</a></li>'
    ].join('');
    var btnNode = $(btnHTML).appendTo($('.dropdown-menu', $('.nw-configuration-action')));
    $('button', $('.nw-configuration-add')).css('width', '152px');

    $('#nw-osa-port-button').on('click', function() {
        var networkConfigTable = $('#network-configuration').DataTable();
        var selectedRows = ginger.listNetworkConfig.rows_indexes;
        if (selectedRows && (selectedRows.length == 1)) {
            wok.window.open('plugins/gingers390x/network-osa-port.html');
        } else {
            var settings = {
                content: i18n["GS390XOSA005M"],
                confirm: i18n["GS390XOSA003M"]
            };
            wok.confirm(settings, function() {}, function() {});
        }
    });
    $('.nw-configuration-add').show();
}

gingers390x.removeEthernetInterface = function() {
    // check architecture and gingers390x plugin for ethernet deletion
    if (gingers390x.hostarch == 's390x') {
      ginger.getPlugins(function(result) {
        if ($.inArray("gingers390x", result) != -1) {
          var settings = {
            content: i18n['GINNET0032M'].replace("%1", gingers390x.selectedNWrows),
            confirm: i18n["GINNET0015M"]
          };
          // get confirmation from user
          wok.confirm(settings, function() {
            var trackDeletedDevices = gingers390x.selectedNWrows;
            // remove ethernet device if user confirms
            $.each(gingers390x.selectedNWInterface, function(key, value) {
            if ((value[3]).toLowerCase() == 'nic') {
            var taskAccepted = false;
            var onTaskAccepted = function() {
              if (taskAccepted) {
                return;
              }
              taskAccepted = true;
            };
            var index = gingers390x.selectedNWrows.indexOf(value[2]);
            trackDeletedDevices.splice(index,1);

            gingers390x.deleteEthernetInterface(value[2], function(result) {
              onTaskAccepted();
              var message = i18n['GINNET0019M'] + " " + value[2].toString() + " " + i18n['GINNET0020M'];
              wok.message.success(message, '#message-network-configuration-container-area');

              if (key == (gingers390x.selectedNWInterface.length-1) && trackDeletedDevices.length == 0){
                  ginger.listNetworkConfig.refreshNetworkConfigurationDatatable();
                  ginger.listNetworkConfig.rows_indexes = new Array();
                  setTimeout(function(){
                    gingers390x.networkRefreshHandler();
                    gingers390x.networkConfigRowSelection();
                  },3000);
                  $('#network-configuration-content-area').on('shown.bs.dropdown','.nw-configuration-add',function(){
                    if(!($('#nw-add-adapter-button',$(this)).length))
                      gingers390x.addNetworkAdapterButton();
                  });
                  $('#network-configuration-content-area').on('shown.bs.dropdown','.nw-configuration-action',function(){
                    if(!($('#nw-osa-port-button',$(this)).length))
                      gingers390x.addOSAportButton();
                  });
                }
            }, function(error) {
              var message = i18n['GINNET0019M'] + " " + value[2].toString() + " " + i18n['GINNET0021M'];
              wok.message.error(message + " " + error.responseJSON.reason, '#message-network-configuration-container-area', true);
          }, onTaskAccepted);
        } else if ((value[3]).toLowerCase() != 'nic') {
          var taskAccepted = false;
          var onTaskAccepted = function() {
              if (taskAccepted) {
                  return;
              }
              taskAccepted = true;
          };
          var index = gingers390x.selectedNWrows.indexOf(value[2]);
          trackDeletedDevices.splice(index,1);
          ginger.deleteInterface(value[2], function(result) {
              onTaskAccepted();
              var message = i18n['GINNET0019M'] + " " + value[2].toString() + " " + i18n['GINNET0020M'];
              wok.message.success(message, '#message-network-configuration-container-area');

              if (key == (gingers390x.selectedNWInterface.length-1) && trackDeletedDevices.length == 0){
                  ginger.listNetworkConfig.refreshNetworkConfigurationDatatable();
                  ginger.listNetworkConfig.rows_indexes = new Array();
                  setTimeout(function(){
                    gingers390x.networkRefreshHandler();
                    gingers390x.networkConfigRowSelection();
                  },3000);
                  $('#network-configuration-content-area').on('shown.bs.dropdown','.nw-configuration-add',function(){
                    if(!($('#nw-add-adapter-button',$(this)).length))
                      gingers390x.addNetworkAdapterButton();
                  });
                  $('#network-configuration-content-area').on('shown.bs.dropdown','.nw-configuration-action',function(){
                    if(!($('#nw-osa-port-button',$(this)).length))
                      gingers390x.addOSAportButton();
                  });
                }
              }, function(error) {
                   var message = i18n['GINNET0019M'] + " " + value[2].toString() + " " + i18n['GINNET0021M'];
                   wok.message.error(message + " " + error.responseJSON.reason, '#message-network-configuration-container-area', true);
                }, onTaskAccepted);
             }
           });
          }, function() {
            //ginger.hideBootgridLoading(ginger.opts_nw_if);
          });

        } else {
          // display message asking user to install gingers390x plugin to avail delete Ethernet interfaces functionality
          var settings = {
            content: i18n["GS390XNW0010E"],
            confirm: i18n["GINNET0015M"]
          };
          wok.confirm(settings, function() {});
        }
      }, function(error) {
        // display error message asking user to try delete again since it
        // failed check gingers390x plugin
        wok.message.error(i18n['GS390XNW0011E'], '#message-network-configuration-container-area', true);
      });
    } else {
      // if not s390x architecture, display error message that deletion of ethernet
      // devices is not supported
      var settings = {
        content: i18n["GS390XNW009E"],
        confirm: i18n["GINNET0015M"]
      };
      wok.confirm(settings, function() {});
    };
};
gingers390x.changeActionButtonsState = function() {
    var opts = [];
    opts['gridId'] = "nwConfigGrid";
    opts['identifier'] = "device";
    // Showing delete button when s390x is selected
    var selectedIf = ginger.getSelectedRowsData(opts);
    if (selectedIf && selectedIf.length == 1) {
      if ((selectedIf[0]["type"]).toLowerCase() == 'nic') {
        ginger.changeButtonStatus(["nw-delete-button"], true);
      }
    } else if(selectedIf && selectedIf.length > 1){
         $.each(selectedIf, function(key, value){
           if((value.type).toLowerCase() == 'nic') {
             ginger.changeButtonStatus(["nw-delete-button"], true);
           }
         });
     } else {
      ginger.networkConfiguration.disableActions();
    }
};

gingers390x.ethernetDeleteHandler = function() {
    $('#network-configuration-content-area').off('click','.nw-delete');
    $('#network-configuration-content-area').on('click','.nw-delete',function(e) {
      e.preventDefault();
      e.stopPropagation();
      $('#network-configuration-content-area > .wok-mask').removeClass('hidden');
      gingers390x.selectedNWrows = [];
      gingers390x.selectedNWtype = 0;
      gingers390x.selectedNWInterface = [];
      var selectedRows = ginger.listNetworkConfig.rows_indexes;
      var networkConfigTable =  $('#network-configuration').DataTable();
      var selectedRows = ginger.listNetworkConfig.rows_indexes;

      if (selectedRows && (selectedRows.length == 1)) {
        var selectedRowDetails  = networkConfigTable.row(selectedRows[0]).data();
        var networkType = selectedRowDetails[3];
        if (networkType.toLowerCase() == 'nic') {
          gingers390x.selectedNWInterface.push(selectedRowDetails);
          gingers390x.selectedNWrows.push(selectedRowDetails[2]);
        }
      } else if (selectedRows && (selectedRows.length > 1)) {
          for (var i = 0; i < selectedRows.length; i++) {
              var selectedRowDetails  = networkConfigTable.row(selectedRows[i]).data();
              gingers390x.selectedNWInterface.push(selectedRowDetails);
              gingers390x.selectedNWrows.push(selectedRowDetails[2]);
          }
      }
      gingers390x.removeEthernetInterface();
    });
};
gingers390x.networkRefreshHandler =  function(){
  $('#nw-config-refresh-btn').off();
  $('#nw-config-refresh-btn').on('click',function(e) {
      e.preventDefault();
      e.stopPropagation();
      ginger.listNetworkConfig.refreshNetworkConfigurationDatatable();
      ginger.listNetworkConfig.rows_indexes = new Array();
      setTimeout(function(){
        gingers390x.networkRefreshHandler();
        gingers390x.networkConfigRowSelection();
      },2000);

      $('#network-configuration-content-area').on('shown.bs.dropdown','.nw-configuration-add',function(){
          if(!($('#nw-add-adapter-button',$(this)).length))
           gingers390x.addNetworkAdapterButton();
      });
      $('#network-configuration-content-area').on('shown.bs.dropdown','.nw-configuration-action',function(){
        if(!($('#nw-osa-port-button',$(this)).length))
          gingers390x.addOSAportButton();
      });
  });
};
//loading network functionality for Gingers390x plugins
//on s390x architecture
gingers390x.loadNetworkDetails = function() {
    var activeTab = $('li.active', $('#tabPanel'));
    if (activeTab.text() == i18n['Network']) {
      if ($.inArray("gingers390x", gingers390x.installedPlugin) != -1 && gingers390x.hostarch == 's390x') {
        //Adding SAN Adapter add button
        $('.nw-configuration-add').on('shown.bs.dropdown',function(){
            if(!($('#nw-add-adapter-button',$(this)).length))
             gingers390x.addNetworkAdapterButton();
        });
        $('#network-configuration-content-area').on('shown.bs.dropdown','.nw-configuration-action',function(){
          if(!($('#nw-osa-port-button',$(this)).length))
            gingers390x.addOSAportButton();
        });
        // Refresh Button handler
        gingers390x.networkRefreshHandler();

        //Network Config datatable selection handler
        gingers390x.networkConfigRowSelection();

        //ethernet deletion handler
        gingers390x.ethernetDeleteHandler();

      }
    }
};
gingers390x.networkConfigRowSelection = function(){
  $('#network-configuration tbody').on('click', 'input[type="checkbox"]', function(e) {
    ginger.nwConfiguration.enableDelete();
    var rows_indexes = ginger.listNetworkConfig.rows_indexes;

    var $row = $(this).closest('tr');

    // Get row ID
    var rowId = $('#network-configuration').DataTable().row($row).index();

    // Determine whether row ID is in the list of selected row IDs
    var index = $.inArray(rowId, rows_indexes);

    // If checkbox is checked and row ID is not in list of selected row IDs
    if (this.checked && index === -1) {
        rows_indexes.push(rowId);

        // Otherwise, if checkbox is not checked and row ID is in list of selected row IDs
    } else if (!this.checked && index !== -1) {
        rows_indexes.splice(index, 1);
    }

    if (this.checked) {
        $row.addClass('active');
    } else {
        $row.removeClass('active');
    }
    ginger.listNetworkConfig.rows_indexes = rows_indexes;
    e.stopPropagation();
  });
};

ginger.getHostDetails(function(result) {
    gingers390x.hostarch = result["architecture"];
    ginger.getPlugins(function(result) {
      gingers390x.installedPlugin = result;
      setTimeout(gingers390x.loadNetworkDetails,2000);
    });
});
gingers390x.initNetworkAddOsaPort = function() {
    $('.selectpicker').selectpicker();
    $('.selectpicker').selectpicker('refresh');
    var opts = [];
    opts['containerId'] = 'network-content-container';
    opts['gridId'] = "network-table-grid";
    $('#osaport-add-submit').on('click', function(event) {
        $(this).attr('data-dismiss', 'modal');
        var osaval = $('#add-osaportType').val();
        gingers390x.disableActionButton();
        gingers390x.enableNetworks(opts, osaval);
        event.preventDefault();
    });
}
gingers390x.cleanModalDialog = function() {
    $(document).ready(function() {
        $('body').on('hidden.bs.modal', '.modal', function() {
            $(this).removeData('bs.modal');
            $("#" + $(this).attr("id") + " .modal-content").empty();
            $("#" + $(this).attr("id") + " .modal-content").append("Loading...");
        });
    });
};
