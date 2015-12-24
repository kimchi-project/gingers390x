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
gingers390x.network = {};

gingers390x.initNetwork = function() {
  gingers390x.initBlacklist();
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

  var actionButtonHtml = '<div class="col-sm-1 grid-control">' +
    '<button class="row btn btn-primary" type="submit" id="network-enable-btn" aria-expanded="false" disabled="true">' + actionButtonText + '</button>' +
    '</div>';
  gingers390x.addBootgridActionButton(opts, actionButtonHtml);

  //Add on click event
  $('#network-enable-btn').on('click', function(event) {
    gingers390x.disableActionButton();
    gingers390x.enableNetworks(opts);
    event.preventDefault();
  });

  gingers390x.initNetworkBootGridData(opts);
  gingers390x.finishAction(opts);


};

gingers390x.initNetworkBootGridData = function(opts) {

  var result = [];
  gingers390x.disableActionButton();
  gingers390x.clearBootgridData(opts);
  gingers390x.hideBootgridData(opts); //This will hide  No reaord found till data is not appended.
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

  });

};

gingers390x.enableNetworks = function(opts) {
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
      gingers390x.configureNetwork(selectedRowIds[i], true, function(result) {
        onTaskAccepted();
        var successText = result['message'];
        wok.message.success(successText, '#alert-modal-nw-container');
        totalRowsSelected = totalRowsSelected - 1;
        if (totalRowsSelected == 0) {
          gingers390x.initNetworkBootGridData(opts);
        }
      }, function(result) {
        if (result['message']) {
          var errText = result['message'];
        } else {
          var errText = result['responseJSON']['reason'];
        }
        result && wok.message.error(errText, '#alert-modal-nw-container', true);
        taskAccepted;
        totalRowsSelected = totalRowsSelected - 1;
        if (totalRowsSelected == 0) {
          gingers390x.initNetworkBootGridData(opts);
        }
      }, onTaskAccepted);
    }
  } else {
    wok.message.error(i18n['GS390XNW008E'], '#alert-modal-nw-container', true);
    gingers390x.enableActionButton();
    gingers390x.hideBootgridLoading(opts);
    gingers390x.showBootgridData(opts);
  }

};

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
};

gingers390x.disableActionButton = function() {
  $('#network-enable-btn').prop("disabled", true);
};
