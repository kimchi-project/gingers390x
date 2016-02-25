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
  gingers390x.initFCPLunsDetails = function() {
  $('#storage-window-modal').parent().width(1050);
  $('#storage-window-modal').width(1050);

  gingers390x.loadFCPLunsList();

  $('#refreshLuns').on("click", function() {
    gingers390x.retrieveLunsList();
  });
  $('#addSANadapter').on("click", function() {
    wok.window.open("plugins/gingers390x/fcpsanadapter.html");
  });
  $("#enableLunsScan").on("click", function() {
    gingers390x.getLunsScanStatus(function(result) {
      gingers390x.lunsScanStatusChange(result.current, function(response) {
        var lunsStatusButtonText, messageText = "";
        if (response.current) {
          lunsStatusButtonText = i18n['GS390XFCLN001E'];
          messageText = i18n['GS390XFCLN002E'];
          $('#luns-add-all-button').html('<i class="fa fa-search"></i>' + i18n['GS390XFCLN003E']);
          $('#luns-add-selected-button').hide();
          $("#luns-add-all-button" ).off(); //clear handlers before assigning new handler
          $('#luns-add-all-button').on("click", gingers390x.lunsDiscoveryHandler);
          gingers390x.disablerefreshLunsButton();
          gingers390x.retrieveLunsList();
          gingers390x.showLunEnabledmessage();
        } else {
          lunsStatusButtonText = i18n['GS390XFCLN004E'];
          messageText = i18n['GS390XFCLN005E'];
          $('#luns-add-all-button').html('<i class="fa fa-plus-circle"></i>' + i18n['GS390XFCLN006E']);
          $('#luns-add-selected-button').show();
          $("#luns-add-all-button" ).off(); //clear handlers before assigning new handler
          $('#luns-add-all-button').on("click", gingers390x.addAllhandler);
          gingers390x.enablerefreshLunsButton();
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
    });
  });
  gingers390x.getLunsScanStatus(function(result) {
    var lunsStatusButtonText = "";
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
      gingers390x.enablerefreshLunsButton();
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

  gingers390x.listFCPluns(function(result) {
    var formattedResult = [];

    for (var i = 0; i < result.length; i++) {
      var lunsDetails = result[i];
      lunsDetails["Srno"] = i;
      formattedResult.push(lunsDetails);
    }
    gingers390x.loadBootgridData(opts, formattedResult);
    gingers390x.showBootgridData(opts);
    gingers390x.hideBootgridLoading(opts);
    }, function(error) {
      gingers390x.hideBootgridLoading(opts);
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
    '<button id="action-dropdown-button-', container, '" class="btn btn-primary dropdown-toggle" type="button" data-toggle="dropdown">', (buttonType === 'action') ? '<span class="edit-alt"></span>Actions' : '<i class="fa fa-plus-circle"></i>Add ', '<span class="caret"></span>',
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

gingers390x.showLunEnabledmessage = function() {
  $('#fcp-table-container-span').css('visibility', 'hidden');
  $('#lunscan-enabled-msg-text').removeClass('hide');
}

gingers390x.hideLunEnabledmessage = function(){
  $('#lunscan-enabled-msg-text').addClass('hide');
  $('#fcp-table-container-span').css('visibility', 'visible');
}
