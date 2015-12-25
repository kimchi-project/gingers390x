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
gingers390x.eckd = {};

gingers390x.initEckd = function() {

  var opts = {
    actionButtonText: i18n['GS390XED001E'],
    containerId: 'eckd-content-container',
    gridId: 'eckd-table-grid',
    bootGridHeaderC1: i18n['GS390XED002E'],
    bootGridHeaderC2: i18n['GS390XED003E'],
    bootGridHeaderC3: i18n['GS390XED004E'],
    bootGridListMsg: i18n['GS390XED005E'],
    bootGridEnableMsg: i18n['GS390XED006E'],
    deviceEnableSuccessMsg: i18n['GS390XED007E'],
    deviceEnableFailedMsg: i18n['GS390XED008E'],
    deviceSelectMsg: i18n['GS390XED009E'],
    finishMsg: i18n['GS390XED010E'],
    finishConfirm: i18n['GS390XED011E'],
    finishCancel: i18n['GS390XED012E']
  };

  gingers390x.initBlacklist();
  gingers390x.initEckdBootgrid(opts);
};

gingers390x.initEckdBootgrid = function(opts) {

  actionButtonText = opts.actionButtonText;

  var headers = [{
    "column-id": 'device',
    'title': opts.bootGridHeaderC1,
    "type": 'string',
    "identifier": true,
    "width": "20%"
  }, {
    "column-id": 'installed_chipids',
    'title': opts.bootGridHeaderC2,
    "type": 'string',
    "width": "30%"
  }, {
    "column-id": 'enabled_chipids',
    'title': opts.bootGridHeaderC3,
    "type": 'string',
    "width": "45%"
  }];

  opts['headers'] = JSON.stringify(headers);
  opts['loadingMessage'] = opts.bootGridListMsg;
  gingers390x.initHeader(opts);
  gingers390x.initBootgrid(opts);
  gingers390x.hideBootgridData(opts); //This will hide  No reaord found till data is not appended.

  var actionButtonHtml = '<div class="col-sm-1 grid-control">' + '<button class="row btn btn-primary" type="submit" id="eckd-enable-btn" aria-expanded="false" disabled="true">' + actionButtonText + '</button>' + '</div>';

  gingers390x.addBootgridActionButton(opts, actionButtonHtml);

  $('#eckd-enable-btn').on('click', function(event) {
    gingers390x.eckd.disableActionButton();
    gingers390x.enableEckd(opts);
    event.preventDefault();
  });

  gingers390x.initEckdBootGridData(opts);
  gingers390x.initEckdFinish(opts);

};

gingers390x.initEckdBootGridData = function(opts) {

  var result = [];
  gingers390x.eckd.disableActionButton();
  gingers390x.clearBootgridData(opts);
  opts['loadingMessage'] = opts.bootGridListMsg;
  gingers390x.showBootgridLoading(opts);

  gingers390x.hideBootgridData(opts);

  gingers390x.listEckd(function(result) {
    function stringifyNestedObject(key, value) {
      if (key === "installed_chipids" && typeof value === "object") {
        value = value.join(',');
      }
      if (key === "enabled_chipids" && typeof value === "object") {
        value = value.join(',');
      }
      return value;
    }

    stringify_result = JSON.stringify(result, stringifyNestedObject);
    stringify_result = JSON.parse(stringify_result);

    gingers390x.loadBootgridData(opts, stringify_result);

    if (stringify_result && stringify_result.length > 0) {
      gingers390x.eckd.enableActionButton();
    } else {
      // This need to be in else block to avoid showing no-record-found
      // for a second if data is present.
      gingers390x.hideBootgridLoading(opts);
      gingers390x.showBootgridData(opts);
    }

  });

};

gingers390x.eckd.validateRowSelection = function(selectedRowIds) {
  return (selectedRowIds && selectedRowIds.length > 0) ? true : false;
}

gingers390x.enableEckd = function(opts) {
  var selectedRowIds = gingers390x.getSelectedRows(opts);
  if (gingers390x.eckd.validateRowSelection(selectedRowIds)) {

    opts['loadingMessage'] = opts.bootGridEnableMsg;
    gingers390x.showBootgridLoading(opts);

    var trackEnablingDevices = selectedRowIds;

    for (var i = 0; i < selectedRowIds.length; i++) {
      gingers390x.configureEckd(selectedRowIds[i], true,
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
            gingers390x.initEckdBootGridData(opts); //Reload The list
        },
        function(result) {
          if (result['message']) { // Error message from Async Task status TODO
            var errText = result['message'];
          } else { // Error message from standard gingers390x exception TODO
            var errText = result['responseJSON']['reason'];
          }
          result
            && wok.message.error(errText,
              '#alert-modal-nw-container', true);

          trackEnablingDevices = gingers390x.trackdevices(
            trackEnablingDevices, result.device);

          if (i == selectedRowIds.length && trackEnablingDevices.length == 0)
            gingers390x.initEckdBootGridData(opts); //Reload The list

        });
    }
  } else {
    wok.message.error(opts.deviceSelectMsg, '#alert-modal-nw-container',
      true);
    gingers390x.eckd.enableActionButton();
    gingers390x.showBootgridData(opts);
    gingers390x.hideBootgridLoading(opts);
  }
};

gingers390x.eckd.enableActionButton = function() {
  $('#eckd-enable-btn').prop("disabled", false);
};

gingers390x.eckd.disableActionButton = function() {
  $('#eckd-enable-btn').prop("disabled", true);
};

gingers390x.initEckdFinish = function(opts) {
  $("#s390x-eckd-finish").on('click', function(event) {

    var selectedRowIds = gingers390x.getSelectedRows(opts);

    var settings = {
      content: opts.finishMsg,
      confirm: opts.finishConfirm,
      cancel: opts.finishCancel
    };

    if (gingers390x.eckd.validateRowSelection(selectedRowIds)) {
      wok.confirm(settings, function() {
        $('#eckd-enable-btn').trigger("click");
      }, function() {
        gingers390x.deselectAll(opts);
        $('#s390x-eckd-finish').trigger("click");
      });
    } else {
      $(this).attr('data-dismiss', 'modal');
      return true;
    }
  });
};
