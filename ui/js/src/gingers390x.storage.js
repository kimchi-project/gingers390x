/*
 * Project Ginger S390x
 *
 * Copyright IBM Corp, 2015-2017
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
  gingers390x.initFCPLunsDetails = function() {
  $('#storage-window-modal').parent().width(1050);
  $('#storage-window-modal').width(1050);

  gingers390x.lunsScanStatus = null;
  gingers390x.loadFCPLunsList();

  $('#refreshLuns').on("click", function() {
    gingers390x.disableAllFCPStorageDevicesButtons();
    gingers390x.retrieveLunsList();
  });
  $('#addSANadapter').on("click", function() {
    wok.window.open("plugins/gingers390x/fcpsanadapter.html");
  });
  $("#enableLunsScan").on("click", function() {
      gingers390x.disableAllFCPStorageDevicesButtons();
      gingers390x.getLunsScanStatus(function(result) {
      gingers390x.lunsScanStatusChange(result.current, function(response) {
        var lunsStatusButtonText, messageText = "";
        gingers390x.lunsScanStatus = response.current;
        if (response.current) {
          lunsStatusButtonText = i18n['GS390XFCLN001E'];
          messageText = i18n['GS390XFCLN002E'];
          $('#luns-add-all-button').html('<i class="fa fa-search"></i>' + i18n['GS390XFCLN003E']);
          $('#luns-add-selected-button').hide();
          $("#luns-add-all-button" ).off(); //clear handlers before assigning new handler
          $('#luns-add-all-button').on("click", gingers390x.lunsDiscoveryHandler);
          gingers390x.retrieveLunsList();
          gingers390x.showLunEnabledmessage();
          gingers390x.disablerefreshLunsButton();
        } else {
          lunsStatusButtonText = i18n['GS390XFCLN004E'];
          messageText = i18n['GS390XFCLN005E'];
          $('#luns-add-all-button').html('<i class="fa fa-plus-circle"></i>' + i18n['GS390XFCLN006E']);
          $('#luns-add-selected-button').show();
          $("#luns-add-all-button" ).off(); //clear handlers before assigning new handler
          $('#luns-add-all-button').on("click", gingers390x.addAllhandler);
          gingers390x.retrieveLunsList();
          gingers390x.hideLunEnabledmessage();
        }
        wok.message.success(messageText, '#alert-modal-storage-container', true);
        $('#enableLunsScan').text(lunsStatusButtonText);
      }, function(result) {
        wok.message.error(i18n['GS390XFCLN007E'], '#alert-modal-storage-container');
      });
    }, function(result) {
      wok.message.error(i18n['GS390XFCLN008E'], '#alert-modal-storage-container');
      gingers390x.enableAllFCPStorageDevicesButtons();
    });
  });
  gingers390x.getLunsScanStatus(function(result) {
    var lunsStatusButtonText = "";
    gingers390x.lunsScanStatus = result.current;
    if (result.current) {
      lunsStatusButtonText = i18n['GS390XFCLN001E'];
      $('#luns-add-all-button').html('<i class="fa fa-search"></i>' + i18n['GS390XFCLN003E']);
      $('#luns-add-selected-button').hide();
      $("#luns-add-all-button" ).off(); //clear handlers before assigning new handler
      $('#luns-add-all-button').on("click", gingers390x.lunsDiscoveryHandler);
      gingers390x.disablerefreshLunsButton();
      gingers390x.showLunEnabledmessage();
    } else {
      lunsStatusButtonText = i18n['GS390XFCLN004E'];
      $('#luns-add-all-button').html('<i class="fa fa-plus-circle"></i>' + i18n['GS390XFCLN006E']);
      $('#luns-add-selected-button').show();
      $("#luns-add-all-button" ).off(); //clear handlers before assigning new handler
      $('#luns-add-all-button').on("click", gingers390x.addAllhandler);
      gingers390x.hideLunEnabledmessage();
    }
    $('#enableLunsScan').text(lunsStatusButtonText);

  });
}
gingers390x.loadFCPLunsList = function() {
  gingers390x.addFCPActions();
  var opts = [];
  opts['containerId'] = 'fcp-luns-list-container';
  opts['gridId'] = "fcp-luns-table-grid";
  var formattedResult = [];
  var headers = [{
    "column-id": 'hbaId',
    'title': i18n['GS390XFCLN009E'],
    "type": 'string',
    "width": "11%"
  }, {
    "column-id": 'remoteWwpn',
    'title': i18n['GS390XFCLN0018E'],
    "type": 'string',
    "width": "20%"
  }, {
    "column-id": 'lunId',
    'title': i18n['GS390XFCLN0010E'],
    "type": 'string',
    "width": "20%"
  }, {
    "column-id": 'product',
    'title': i18n['GS390XFCLN0011E'],
    "type": 'string',
    "width": '16%'
  }, {
    "column-id": 'controllerSN',
    'title': i18n['GS390XFCLN0012E'],
    "type": 'string',
    "width": '30%'
  }, {
    "column-id": 'Srno',
    "type": 'numeric',
    "identifier": true,
    "invisible": true
  }];
  opts['headers'] = JSON.stringify(headers);

  gingers390x.initHeader(opts);
  gingers390x.initBootgrid(opts);
  gingers390x.hideBootgridData(opts);
  gingers390x.retrieveLunsList();

};
gingers390x.addFCPActions = function() {
  var opts = {};
  opts['gridId'] = 'fcp-luns-table-grid';

  var actionButton = [{
    id: 'luns-add-selected-button',
    class: 'fa fa-plus-circle',
    label: i18n['GS390XFCLN0013E'],
    onClick: function(event) {
      gingers390x.disableAllFCPStorageDevicesButtons()
      var selectedRows = gingers390x.getSelectedRows(opts);
      var currentRows = gingers390x.getCurrentRows(opts);
      var identifier = 'Srno';

      var selectedRowDetails = gingers390x.getSelectedRowsData(currentRows, selectedRows, identifier);
      var rowIndex = 0;
      var failedlLuns = [];
      var successLuns = [];
      var isConfigured = null;
      var lunsDetails = '';
      var TrackNum = selectedRows.length;
      $.each(selectedRowDetails, function(i, row) {
        var lunAddDetails = {
          'hbaId': row['hbaId'],
          'remoteWwpn': row['remoteWwpn'],
          'lunId': row['lunId']
       }
        gingers390x.addLuns(lunAddDetails, function(result) {
          wok.message.success(lunAddDetails.hbaId+':'+lunAddDetails.remoteWwpn+':'+lunAddDetails.lunId+' '+i18n['GS390XFCLN0014E'], '#alert-modal-storage-container');
        TrackNum = TrackNum - 1;
        if (TrackNum == 0){
          ginger.initStorageDevicesGridData();
        }

        }, function(result) {
          wok.message.error(i18n["GS390XFCLN0015E"], '#alert-modal-storage-container');
          TrackNum = TrackNum - 1;
        if (TrackNum == 0){
          ginger.initStorageDevicesGridData();
        }
        });
      });
      gingers390x.retrieveLunsList();
    }

  }, {
    id: 'luns-add-all-button',
    class: 'fa fa-plus-circle',
    label: i18n['GS390XFCLN006E']
  }];

  var actionListSettings = {
    panelID: 'fcp-storage-actions',
    buttons: actionButton,
    type: 'action'
  };

  gingers390x.createActionList(actionListSettings);
};

gingers390x.retrieveLunsList = function() {
  var opts = [];
  opts['containerId'] = 'fcp-luns-list-container';
  opts['gridId'] = "fcp-luns-table-grid";
  gingers390x.hideBootgridData(opts);
  gingers390x.showBootgridLoading(opts);
  gingers390x.clearFilterData();
  gingers390x.clearBootgridData(opts);
  gingers390x.disableAllFCPStorageDevicesButtons();

  gingers390x.listFCPluns(function(result) {
    var formattedResult = [];

    for (var i = 0; i < result.length; i++) {
      var lunsDetails = result[i];
      lunsDetails["Srno"] = i;
      formattedResult.push(lunsDetails);
    }
    gingers390x.loadBootgridData(opts, formattedResult);

    if(formattedResult.length==0){
      gingers390x.showBootgridData(opts);
      gingers390x.hideBootgridLoading(opts);
    }
    gingers390x.enableAllFCPStorageDevicesButtons();

    if(gingers390x.lunsScanStatus){
      gingers390x.disablerefreshLunsButton();
    }
    }, function(error) {
      gingers390x.hideBootgridLoading(opts);
      gingers390x.enableAllFCPStorageDevicesButtons();
      wok.message.error(error.responseJSON.reason, '#alert-modal-storage-container', true);
    });
};

gingers390x.createActionList = function(settings) {
  var toolbarNode = null;
  var btnHTML, dropHTML = [];
  var container = settings.panelID;
  var toolbarButtons = settings.buttons;
  var buttonType = settings.type;
  toolbarNode = $('<div class="btn-group"></div>');
  toolbarNode.appendTo($("#" + container));
  dropHTML = ['<div class="dropdown menu-flat">',
    '<button id="action-dropdown-button-', container, '" class="btn btn-primary dropdown-toggle" type="button" data-toggle="dropdown">', (buttonType === 'action') ? '<span class="edit-alt"></span>' + i18n['GS390XFCLN0022E'] : '<i class="fa fa-plus-circle"></i>' + i18n['GS390XFCLN0021E'], '<span class="caret"></span>',
    '</button>',
    '<ul class="dropdown-menu"></ul>',
    '</div>'
  ].join('');
  $(dropHTML).appendTo(toolbarNode);

  $.each(toolbarButtons, function(i, button) {
    var btnHTML = [
      '<li role="presentation"', button.critical === true ? ' class="critical"' : '', '>',
      '<a role="menuitem" tabindex="-1"', (button.id ? (' id="' + button.id + '"') : ''), (button.disabled === true ? ' class="disabled"' : ''),
      '>',
      button.class ? ('<i class="' + button.class) + '"></i>' : '',
      button.label,
      '</a></li>'
    ].join('');
    var btnNode = $(btnHTML).appendTo($('.dropdown-menu', toolbarNode));
    button.onClick && btnNode.on('click', button.onClick);
  });
};
gingers390x.lunsDiscoveryHandler = function() {
  wok.message.warn(i18n["GS390XFCLN0016E"], '#alert-modal-storage-container');
  var taskAccepted = false;
  var onTaskAccepted = function() {
    if (taskAccepted) {
      return;
    }
    wok.message.warn(i18n["GS390XFCLN0020E"], '#alert-modal-storage-container',true);
    taskAccepted = true;
  };
  gingers390x.lunsDiscovery(function(result) {
    onTaskAccepted();
    var successText = i18n['GS390XFCLN0019E'];
    wok.message.success(successText, '#alert-modal-storage-container', true);
    ginger.initStorageDevicesGridData(); //refresh storage devices listing
    //  wok.topic('gingers390x/enableNetworks').publish();
  }, function(result) {
    if (result['message']) { // Error message from Async Task status TODO
      var errText = result['message'];
    } else { // Error message from standard gingers390x exception TODO
      var errText = result['responseJSON']['reason'];
    }
    result && wok.message.error(errText, '#alert-modal-storage-container');
    ginger.initStorageDevicesGridData(); //refresh storage devices listing
    taskAccepted;
  }, onTaskAccepted);
};
gingers390x.addAllhandler = function() {
  var opts = {};
  opts['gridId'] = 'fcp-luns-table-grid';
  var selectedRowDetails = gingers390x.getCurrentRows(opts);
  var rowIndex = 0;
  var failedlLuns = [];
  var successLuns = [];
  var isConfigured = null;
  var lunsDetails = '';
  var TrackNum = selectedRowDetails.length;

  $.each(selectedRowDetails, function(i, row) {
    var lunAddDetails = {
      'hbaId': row['hbaId'],
      'remoteWwpn': row['remoteWwpn'],
      'lunId': row['lunId']
    }
    gingers390x.addLuns(lunAddDetails, function(result) {
      wok.message.success(lunAddDetails.hbaId+':'+lunAddDetails.remoteWwpn+':'+lunAddDetails.lunId+' '+i18n["GS390XFCLN0014E"], '#alert-modal-storage-container');
      TrackNum = TrackNum - 1;
      if(TrackNum == 0){
        ginger.initStorageDevicesGridData();
      }
    }, function(result) {
      wok.message.error(i18n['GS390XFCLN0017E'], '#alert-modal-storage-container');
      TrackNum = TrackNum - 1;
      if(TrackNum == 0){
        ginger.initStorageDevicesGridData();
      }
    });
  });
  gingers390x.retrieveLunsList();
}

gingers390x.disablerefreshLunsButton = function(){
  $('#refreshLuns').prop("disabled", true);
}

gingers390x.enablerefreshLunsButton = function(){
  $('#refreshLuns').prop("disabled", false);
}

gingers390x.disableLunScanButton = function(){
  $('#enableLunsScan').prop("disabled", true);
}

gingers390x.enableLunScanButton = function(){
  $('#enableLunsScan').prop("disabled", false);
}

gingers390x.disablefcpStorageActionsButton = function(){
  $('#action-dropdown-button-fcp-storage-actions').prop("disabled", true);
}

gingers390x.enablefcpStorageActionsButton = function(){
  $('#action-dropdown-button-fcp-storage-actions').prop("disabled", false);
}

gingers390x.disableAddSANAdapterButton = function(){
  $('#addSANadapter').prop("disabled", true);
}

gingers390x.enableAddSANAdapterButton = function(){
  $('#addSANadapter').prop("disabled", false);
}

gingers390x.disableAllFCPStorageDevicesButtons = function(){
	gingers390x.disablerefreshLunsButton();
	gingers390x.disableLunScanButton();
	gingers390x.disablefcpStorageActionsButton();
}

gingers390x.enableAllFCPStorageDevicesButtons = function(){
	gingers390x.enablerefreshLunsButton();
	gingers390x.enableLunScanButton();
	gingers390x.enablefcpStorageActionsButton();
}

gingers390x.showLunEnabledmessage = function() {
  $('#fcp-table-container-span').css('visibility', 'hidden');
  $('#lunscan-enabled-msg-text').removeClass('hide');
}

gingers390x.hideLunEnabledmessage = function(){
  $('#lunscan-enabled-msg-text').addClass('hide');
  $('#fcp-table-container-span').css('visibility', 'visible');
}

gingers390x.loadStorageActionButtons = function() {
    var addButton = [{
      id: 'sd-add-FCP-button',
      class: 'fa fa-plus-circle',
      label: i18n['GS390XSD007M'],
      onClick: function(event) {
        $('#sd-add-FCP-button').attr('href', 'plugins/gingers390x/addFCPLuns.html');
        $('#sd-add-FCP-button').attr('data-toggle', 'modal');
        $('#sd-add-FCP-button').attr('data-target', '#storage-AddFCP-modal');
        ginger.cleanModalDialog();
      }
    }, {
      id: 'sd-add-ECKD-button',
      class: 'fa fa-plus-circle',
      label: i18n['GS390XSD008M'],
      onClick: function(event) {
        wok.window.open('plugins/gingers390x/eckd.html');
      }
    }];
    var actionButton = [{
      id: 'sd-format-button',
      class: 'fa fa-pencil-square-o',
      label: i18n['GS390XSD009M'],
      onClick: function(event) {
        var opts = [];
        opts['gridId'] = "stgDevGrid";
        opts['identifier'] = "name";
        opts['loadingMessage'] = i18n['GS390XSD001M'];

        var settings = [];
        if (gingers390x.selectionContainNonDasdDevices()) {
          settings = {
            title: i18n['GINSD00005M'],
            content: i18n['GINSD00003'],
            confirm: i18n['GGBAPI6002M'],
            cancel: i18n['GGBAPI6003M']
          };
        } else {
          settings = {
            content: i18n['GINSD00002'],
            confirm: i18n['GGBAPI6002M'],
            cancel: i18n['GGBAPI6003M']
          };
        }

        wok.confirm(settings, function() {
          var selectedRows = ginger.getSelectedRowsData(opts);
          ginger.selectedrows = selectedRows;
          var trackingNums = selectedRows.length;
          var taskAccepted = false;
          var onTaskAccepted = function() {
            if (taskAccepted) {
              return;
            }
            taskAccepted = true;
          };
          var selectedRowDetails = JSON.stringify(ginger.selectedrows);
          ginger.showBootgridLoading(opts);
          ginger.hideBootgridData(opts);
          $("#storage-device-refresh-btn").hide();
          $("#action-dropdown-button-file-systems-actions").hide();

          $.each(ginger.selectedrows, function(i, row) {
            if (row['type'] == "dasd") {
              var busId = row['bus_id'];
              var deviceId = row['id'];
              var settings = {
                'blk_size': '4096'
              };

              ginger.formatDASDDevice(busId, settings, function(result) {
                trackingNums = trackingNums - 1;
                wok.message.success(deviceId + i18n['GS390XSD002M'], '#alert-modal-nw-container');
                if (trackingNums == 0) {
                  $("#action-dropdown-button-file-systems-actions").show();
                  $("#storage-device-refresh-btn").show();
                  $("#storage-device-refresh-btn").trigger('click');
                }
              }, function(result) {
                trackingNums = trackingNums - 1;
                errorMsg = i18n['GINDASD0001E'].replace("%1", deviceId);
                if ('responseJSON' in result) {
                  errorMsg = result['responseJSON']['reason'];
                } else {
                  errorMsg = result['message'];
                }

                wok.message.error(errorMsg, '#alert-modal-nw-container', true);
                if (trackingNums == 0) {
                  $("#action-dropdown-button-file-systems-actions").show();
                  $("#storage-device-refresh-btn").show();
                  $("#storage-device-refresh-btn").trigger('click');
                }
              }, onTaskAccepted);
            } else {
              trackingNums = trackingNums - 1;
              if (trackingNums == 0) {
                $("#storage-device-refresh-btn").trigger('click');
                $('#sd-format-button').show();
              }
            }
          });
        }, function() {});
      }
    }, {
      id: 'sd-remove-button',
      class: 'fa fa-minus-circle',
      label: i18n['GS390XSD006M'],
      critical: true,
      onClick: function(event) {
        var opts = [];
        opts['gridId'] = "stgDevGrid";
        opts['identifier'] = "name";
        var settings = {
          content: i18n['GINSD00001'],
          confirm: i18n['GGBAPI6002M'],
          cancel: i18n['GGBAPI6003M']
        };

        wok.confirm(settings, function() {
          var lunsScanStatus = null;
          gingers390x.getLunsScanStatus(function(result) {
            lunsScanStatus = result.current;
            var selectedRows = ginger.getSelectedRowsData(opts);
            ginger.selectedrows = selectedRows;
            var rowNums = selectedRows.length;
            var selectedRowDetails = JSON.stringify(ginger.selectedrows);
            var fcpDeviceNo = 0;
            var removalErrorMessage = '';
            opts['loadingMessage'] = i18n['GS390XSD003M'];
            ginger.showBootgridLoading(opts);
            ginger.hideBootgridData(opts);
            $.each(ginger.selectedrows, function(i, row) {
              var diskType = row['type'];
              var deviceId = row['id'];

              if (diskType == "dasd") {
                var busId = row['bus_id'];
                var settings = {
                  'blk_size': '4096'
                };
                gingers390x.removeDASDDevice(busId, settings, function(result) {
                  wok.message.success(deviceId + i18n['GS390XSD004M'], '#alert-modal-nw-container');
                  rowNums = rowNums - 1;
                  if (rowNums == 0) {
                    $("#storage-device-refresh-btn").trigger('click');
                  }
                }, function(result) {
                  if (result['responseJSON']) {
                    var errText = result['responseJSON']['reason'];
                  }
                  result && wok.message.error(errText, '#alert-modal-nw-container', true);
                  rowNums = rowNums - 1;
                  if (rowNums == 0) {
                    $("#storage-device-refresh-btn").trigger('click');
                  }
                }, function() {});

              } else if (diskType == "fc") {
                var fcp_lun = row['fcp_lun'];
                var wwpn = row['wwpn'];
                var hba_id = row['hba_id'];
                var lun_path = hba_id + ":" + wwpn + ":" + fcp_lun
                var settings = {};
                fcpDeviceNo++;

                if (!lunsScanStatus) {
                  gingers390x.removeFCDevice(lun_path, settings, function(result) {
                    wok.message.success(deviceId + " removed successfully", '#alert-modal-nw-container');
                    rowNums = rowNums - 1;
                    if (rowNums == 0) {
                      $("#storage-device-refresh-btn").trigger('click');
                    }
                  }, function(result) {
                    var errText = result['responseJSON']['reason'];
                    wok.message.error(errText, '#alert-modal-nw-container', true);
                    rowNums = rowNums - 1;
                    if (rowNums == 0) {
                      $("#storage-device-refresh-btn").trigger('click');
                    }
                  }, function() {});
                } else {
                  if (fcpDeviceNo <= 1)
                    wok.message.error(i18n['GS390XSD005M'], '#alert-modal-nw-container', true);
                  rowNums = rowNums - 1;
                  if (rowNums == 0) {
                    $("#storage-device-refresh-btn").trigger('click');
                  }
                }
              }else{
                 removalErrorMessage = removalErrorMessage + deviceId+"<br>";
                 rowNums = rowNums - 1;

                 if (rowNums == 0) {
                   $("#storage-device-refresh-btn").trigger('click');
                 }
              }
            });

        if(removalErrorMessage!="")
         wok.message.error(i18n['GS390XSD0010M']+'<br>'+removalErrorMessage, '#alert-modal-nw-container', true);

          });
        }, function() {});
      }
    }, {
      id: 'storage-device-create-partition-btn',
      class: 'fa fa-plus-circle',
      label: i18n['GS390XSD011M'],
      onClick: function(event) {
        var opts = [];
        opts['id'] = 'stg-devs';
        opts['gridId'] = "stgDevGrid";
        opts['identifier'] = "name";
        var selectedRows = ginger.getSelectedRowsData(opts);
        ginger.partition.PartitionDeviceInfo = selectedRows[0];
        if (selectedRows && selectedRows.length === 1) {
          if(ginger.partition.PartitionDeviceInfo['status']!='n/f'){
            wok.window.open('plugins/ginger/host-storage-addpartitions.html');
          }else {
            wok.message.warn(i18n['GINPT00017M'], '#alert-modal-nw-container', true);
          }
        } else {
            wok.message.error(i18n['GINPT00014M'], '#alert-modal-nw-container', true);
        }
      }
    }];

    var addListSettings = {
      panelID: 'file-systems-add',
      buttons: addButton,
      type: 'add'
    };

    var actionListSettings = {
      panelID: 'file-systems-actions',
      buttons: actionButton,
      type: 'action'
    };

    gingers390x.createActionList(addListSettings);
    $("#storage-device-create-partition-btn").off();
    $("#file-systems-actions").empty();
    gingers390x.createActionList(actionListSettings);

};

// ******************** FCP Tape Devices ********************
gingers390x.loadFcpTapeDevices = function() {
    $("#fcp-tape-devices-panel").removeClass("hidden")
    var gridFields = [];
    var opts = [];
    opts['containerId'] = 'fcp-tape-devices';
    opts['gridId'] = "fcptapeDevicesGrid";
    gridFields = [{
      "column-id": 'Generic',
      "type": 'string',
      "width": "12.5%",
      "title": i18n['GS390XFCT001E'],
      "identifier": true
    }, {
      "title": i18n['GS390XFCT002E'],
      "column-id": 'Device',
      "width": "12.5%",
      "type": 'string'
    }, {
      "title": i18n['GS390XFCT003E'],
      "column-id": "Target",
      "width": "10%",
      "type": 'string'
    }, {
      "title": i18n['GS390XFCT004E'],
      "column-id": "Model",
      "type": 'string',
      "width": "20%",
    }, {
      "title": i18n['GS390XFCT005E'],
      "column-id": 'Type',
      "width": "20%",
      "type": 'string'
    }, {
      "title": i18n['GS390XFCT006E'],
      "column-id": "State",
      "width": "20%",
      "type": 'string'
    }];

    opts['headers'] = JSON.stringify(gridFields);
    gingers390x.initHeader(opts);
    gingers390x.initBootgrid(opts);
    gingers390x.initFcpTapeGridData();

    $('#refresh-fcp-tape-devices-btn').on('click', function(event) {
      gingers390x.hideBootgridData(opts);
      gingers390x.showBootgridLoading(opts);
      gingers390x.initFcpTapeGridData();
    });
};

gingers390x.initFcpTapeGridData = function() {
    var opts = [];
    opts['gridId'] = "fcptapeDevicesGrid";
    gingers390x.getFcpTapeDevices(function(result) {
      gingers390x.loadBootgridData(opts, result);
      gingers390x.showBootgridData(opts);
      gingers390x.hideBootgridLoading(opts);
    });
};
gingers390x.createSanAdapterAddButton = function() {
    $("#refresh-san-button").removeClass("pull-left");
    var sanAdapterAddButton = '<button class="btn btn-primary" id="add-san-button" aria-expanded="false"><i class="fa fa-plus-circle">&nbsp;</i>' + i18n['GINTITLE0020M'] + '</button>' ;
    $(".buttons","#san-adapter-content-area").append(sanAdapterAddButton);
    $("#add-san-button").addClass("pull-left");

    $('#add-san-button').off();
    $('#add-san-button').on('click', function() {
      wok.window.open('plugins/gingers390x/fcpsanadapter.html');
    });

    $('#refresh-san-button').off();
    $('#refresh-san-button').on('click', function() {
      $("#adapters-table tbody").html("");
      $('#adapters-table').DataTable().destroy();
      ginger.initSanAdaterGridData();
      setTimeout(gingers390x.createSanAdapterAddButton,500);
    });
};
gingers390x.updateSANAdapterDetails = function() {
    //reloading sanadapter datatable.
    $('#adapters-table tbody').html('');
    $('#adapters-table').DataTable().destroy();
    ginger.initSanAdaterGridData();
    setTimeout(gingers390x.createSanAdapterAddButton,500);
};
gingers390x.selectionContainNonDasdDevices = function() {
    var opts = [];
    opts['gridId'] = "stgDevGrid";
    opts['identifier'] = "id";
    var selectedRows = ginger.getSelectedRowsData(opts);
    var result = false;

    $.each(selectedRows, function(i, row) {
      if (row['type'] != "dasd") {
        result = true;
      }
    });

    return result;
};

//loading storage functionality for Gingers390x plugins
//on s390x architecture
gingers390x.loadStorageDetails = function() {
    var activeTab = $('li.active', $('#tabPanel'));
    if (activeTab.text() == i18n['Storage']) {
      gingers390x.loadStorageActionButtons();
      gingers390x.loadFcpTapeDevices();
      setTimeout(gingers390x.updateSANAdapterDetails,1000);
    }
}

ginger.getHostDetails(function(result) {
    gingers390x.hostarch = result["architecture"];
    ginger.getPlugins(function(result) {
      gingers390x.installedPlugin = result;
      if ($.inArray("gingers390x", gingers390x.installedPlugin) != -1 && gingers390x.hostarch == 's390x') {
        gingers390x.loadStorageDetails();
      }
    });
});
