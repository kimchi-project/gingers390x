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
gingers390x.initHeader = function(opts) {

  var containerId = opts['containerId'];
  var gridId = opts['gridId'];
  var gridMessage = ('loadingMessage' in opts && opts['loadingMessage'].trim() && opts['loadingMessage'].length > 0) ? opts['loadingMessage'] : i18n['GS390XBG003E'];
  var fields = JSON.parse(opts['headers']);

  var gridloadingHtml = ['<div id="' + gridId + '-loading" class="wok-list-loader-container wok-list-loading" style="display: none;">',
    '<div class="wok-list-loading-icon"></div>',
    '<div class="wok-list-loading-text">' + gridMessage + '</div>',
    '</div>'
  ].join('');

  $(gridloadingHtml).appendTo('#' + containerId);

  var gridHtml = [
    '<table id="', gridId, '" class="table table-condensed table-hover table-striped" >',
    '<thead>',
    '<tr>',
    '</tr>',
    '</thead>'
  ].join('');

  $(gridHtml).appendTo('#' + containerId);

  var gridHeader = $('tr', gridHtml);
  for (var i = 0; i < fields.length; i++) {
    var columnHtml = [
      '<th data-type="', fields[i]["type"], '" data-column-id="', fields[i]["column-id"], '"', (fields[i].identifier) ? 'data-identifier="true"' : '',
      ' data-align="left" hederAlign="center"', ("formatter" in fields[i]) ? 'data-formatter=' + fields[i]["formatter"] : '', (fields[i]["width"]) ? (' data-width="' + fields[i]["width"] + '"') : '', (fields[i].invisible) ? 'data-visible="false"' : '',
      'data-header-css-class="gridHeader">', ("title" in fields[i]) ? fields[i]["title"] : fields[i]["column-id"],
      '</th>'
    ].join('');

    $(columnHtml).appendTo($('tr', '#' + gridId));
  }

};

gingers390x.initBootgrid = function(opts) {

  var gridId = opts['gridId'];

  var grid = $('#' + gridId).bootgrid({
    selection: true,
    multiSelect: true,
    rowCount: -1,
    sorting: true,
    columnSelection: false,
    rowSelect: true,
    labels: {
      search: i18n['GS390XBG001E'],
      noResults: i18n['GS390XBG002E']
    },
    css: {
      iconDown: "fa fa-sort-desc",
      iconUp: "fa fa-sort-asc"
    }
  }).on("loaded.rs.jquery.bootgrid", function(e) {
    $('.input-group .glyphicon-search').removeClass('.glyphicon-search').addClass('fa fa-search');
    if ($('#' + gridId).bootgrid('getTotalRowCount') > 0) {
      // This need to be in if block to avoid showing no-record-found
      // for a second if data is present.
      gingers390x.hideBootgridLoading(opts);
      gingers390x.showBootgridData(opts);
    }
  }).on("appended.rs.jquery.bootgrid", function(e, appendedRows) {
    if ($('#' + gridId).bootgrid('getTotalRowCount') === 0 && appendedRows == 0) {
      gingers390x.deselectAll(opts);
    }
  });
};

gingers390x.loadBootgridData = function(opts, data) {
  gingers390x.clearBootgridData(opts);
  gingers390x.appendBootgridData(opts, data);
};

gingers390x.clearBootgridData = function(opts) {
  $('#' + opts['gridId']).bootgrid("clear");
};

gingers390x.appendBootgridData = function(opts, data) {
  $('#' + opts['gridId']).bootgrid("append", data);
};

gingers390x.getSelectedRows = function(opts) {
  return $('#' + opts['gridId']).bootgrid("getSelectedRows");
};

gingers390x.deselectAll = function(opts) {
  $('#' + opts['gridId']).bootgrid("deselect");
  $('#' + opts['gridId'] + ' input.select-box').attr('checked', false);
};

gingers390x.addBootgridActionButton = function(opts, actionButtonHtml) {
  $(actionButtonHtml).appendTo('#' + opts['gridId'] + '-header .row .actionBar');
};

gingers390x.showBootgridData = function(opts) {
  $("#" + opts['gridId'] + " tbody").show();
};

gingers390x.hideBootgridData = function(opts) {
  $("#" + opts['gridId'] + " tbody").hide();
};

gingers390x.hideBootgridLoading = function(opts) {
  $("#" + opts['gridId'] + "-loading").hide();
};

gingers390x.showBootgridLoading = function(opts) {
  var gridMessage = ('loadingMessage' in opts && opts['loadingMessage'].trim() && opts['loadingMessage'].length > 0) ? opts['loadingMessage'] : i18n['GS390XBG003E'];
  $("#" + opts['gridId'] + "-loading .wok-list-loading-text").text(gridMessage);
  $("#" + opts['gridId'] + "-loading").show();
  $("#" + opts['gridId'] + "-loading").css("zIndex", 1);
};

gingers390x.getSelectedRowsData = function(currentRows, selectedRowIds, identifier) {
  var selectedRowDetails = [];
  $.each(currentRows, function(i, row) {
    var rowDetails = row;
    if (selectedRowIds.indexOf(rowDetails[identifier]) != -1) {
      selectedRowDetails.push(rowDetails);
    }
  });
  return selectedRowDetails;
};

gingers390x.getCurrentRows = function(opts) {
  return $('#' + opts['gridId']).bootgrid("getCurrentRows");
}
