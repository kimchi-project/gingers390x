/*
 * Project Ginger S390x
 *
 * Copyright IBM, Corp. 2015
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
gingers390x.fcpsanadapter = {};

gingers390x.initFcpSanAdapter = function() {

  var opts = {
    actionButtonText: i18n['GS390XFS001E'],
    containerId: 'fcpsan-content-container',
    gridId: 'fcpsan-table-grid',
    device_title: i18n['GS390XFS002E'],
    chipids_title: i18n['GS390XFS003E'],
    bootGridListMsg: i18n['GS390XFS004E'],
    bootGridEnableMsg: i18n['GS390XFS005E'],
    deviceEnableSuccessMsg: i18n['GS390XFS006E'],
    deviceEnableFailedMsg: i18n['GS390XFS007E'],
    deviceSelectMsg: i18n['GS390XFS008E'],
    finishMsg: i18n['GS390XFS009E'],
    finishConfirm: i18n['GS390XFS010E'],
    finishCancel: i18n['GS390XFS011E']
  };

  gingers390x.initBlacklist();
  gingers390x.initFcpSanAdapterBootgrid(opts);
};

gingers390x.initFcpSanAdapterBootgrid = function(opts) {
  actionButtonText = opts.actionButtonText;

  var headers = [{
    "column-id": 'device',
    'title': opts.device_title,
    "type": 'string',
    "identifier": true,
    "width": "25%"
  }, {
    "column-id": 'installed_chipids',
    'title': opts.chipids_title,
    "type": 'string',
    "width": "70%"
  }];

  opts['headers'] = JSON.stringify(headers);
  opts['loadingMessage'] = opts.bootGridListMsg;
  gingers390x.initHeader(opts);
  gingers390x.initBootgrid(opts);
  gingers390x.hideBootgridData(opts);

  var actionButtonHtml = '<div class="col-sm-1 grid-control">' + '<button class="row btn btn-primary" type="submit" id="fcpsan-enable-btn" aria-expanded="false" disabled="true">' + actionButtonText + '</button>' + '</div>';

  gingers390x.addBootgridActionButton(opts, actionButtonHtml);

  $('#fcpsan-enable-btn').on('click', function(event) {
    gingers390x.fcpsanadapter.disableActionButton();
    gingers390x.enableFcpSanAdapter(opts);
    event.preventDefault();
  });

  gingers390x.initFcpSanAdapterBootGridData(opts);
  gingers390x.initFcpSanAdapterFinish(opts);

};

gingers390x.initFcpSanAdapterBootGridData = function(opts) {

  var result = [];
  gingers390x.fcpsanadapter.disableActionButton();
  gingers390x.clearBootgridData(opts);
  opts['loadingMessage'] = opts.bootGridListMsg;
  gingers390x.showBootgridLoading(opts);

  gingers390x.hideBootgridData(opts);

  gingers390x.listFcpSanAdapter(function(result) {
    function stringifyNestedObject(key, value) {
      if (key === "installed_chipids" && typeof value === "object") {
        value = value.join(',');
      }
      return value;
    }

    stringify_result = JSON.stringify(result, stringifyNestedObject);
    stringify_result = JSON.parse(stringify_result);

    gingers390x.loadBootgridData(opts, stringify_result);

    if (stringify_result && stringify_result.length > 0) {
      gingers390x.fcpsanadapter.enableActionButton();
    } else {
      // This need to be in else block to avoid showing no-record-found
      // for a second if data is present.
      gingers390x.hideBootgridLoading(opts);
      gingers390x.showBootgridData(opts);
    }

  });

};

gingers390x.fcpsanadapter.validateRowSelection = function(selectedRowIds) {
  return (selectedRowIds && selectedRowIds.length > 0) ? true : false;
}

gingers390x.enableFcpSanAdapter = function(opts) {
  var selectedRowIds = gingers390x.getSelectedRows(opts);
  if (gingers390x.fcpsanadapter.validateRowSelection(selectedRowIds)) {

    opts['loadingMessage'] = opts.bootGridEnableMsg;
    gingers390x.showBootgridLoading(opts);


    var trackEnablingDevices = selectedRowIds;

    for (var i = 0; i < selectedRowIds.length; i++) {
      gingers390x.configureFcpSanAdapter(selectedRowIds[i], true,
        function(result) {

          if (result.status == 'online') {
            var successText = result.device + " " + opts.deviceEnableSuccessMsg;
            wok.message.success(successText,
              '#alert-modal-nw-container');
          } else {
            var successText = result.device + " " + opts.deviceEnableFailedMsg;
            wok.message.error(successText,
              '#alert-modal-nw-container', true);
          }

          trackEnablingDevices = gingers390x.trackdevices(
            trackEnablingDevices, result.device);

          if (i == selectedRowIds.length && trackEnablingDevices.length == 0)
            gingers390x.initFcpSanAdapterBootGridData(opts);

        },
        function(result) {
          if (result['message']) { // Error message from Async
            // Task status
            var errText = result['message'];
          } else { // Error message from standard gingers390x
            // exception
            var errText = result['responseJSON']['reason'];
          }
          result
            && wok.message.error(errText,
              '#alert-modal-nw-container', true);

          trackEnablingDevices = gingers390x.trackdevices(
            trackEnablingDevices, result.device);

          if (i == selectedRowIds.length && trackEnablingDevices.length == 0)
            gingers390x.initFcpSanAdapterBootGridData(opts);

        });
    }
  } else {
    wok.message.error(opts.deviceSelectMsg, '#alert-modal-nw-container',
      true);
    gingers390x.fcpsanadapter.enableActionButton();
    gingers390x.showBootgridData(opts);
    gingers390x.hideBootgridLoading(opts);

  }
};

gingers390x.fcpsanadapter.enableActionButton = function() {
  $('#fcpsan-enable-btn').prop("disabled", false);
};

gingers390x.fcpsanadapter.disableActionButton = function() {
  $('#fcpsan-enable-btn').prop("disabled", true);
};

gingers390x.initFcpSanAdapterFinish = function(opts) {
  $("#s390x-fcpsan-finish").on('click', function(event) {
    var selectedRowIds = gingers390x.getSelectedRows(opts);

    var settings = {
      content: opts.finishMsg,
      confirm: opts.finishConfirm,
      cancel: opts.finishCancel
    };

    if (gingers390x.fcpsanadapter.validateRowSelection(selectedRowIds)) {
      wok.confirm(settings, function() {
        $('#fcpsan-enable-btn').trigger("click");
      }, function() {
        gingers390x.deselectAll(opts);
        $('#s390x-fcpsan-finish').trigger("click");
      });
    } else {
      $(this).attr('data-dismiss', 'modal');
      return true;
    }
  });
};
