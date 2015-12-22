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
gingers390x.initBlacklist = function() {
  var opts = {
    inputLabel: i18n['GS390XBL001E'],
    inputPlaceholder: i18n['GS390XBL002E'],
    actionName: i18n['GS390XBL003E'],
    helpText: i18n['GS390XBL004E'],
    noteText: i18n['GS390XBL005E'],
    loadingText: i18n['GS390XBL006E']
  };
  gingers390x.createBlPanel(opts, gingers390x.removeFromBlackList);
}

gingers390x.createBlPanel = function(opts, actionCallBack) {

  var inputLabel = opts.inputLabel;
  var inputPlaceholder = opts.inputPlaceholder;
  var actionName = opts.actionName;
  var helpText = opts.helpText;
  var noteText = opts.noteText;
  var loadingText = opts.loadingText;

  var alertHtml = ["<span id='alert-bl-modal-container' style='display: none;'></span>"].join('');
  $(alertHtml).appendTo("#blacklist-content-container");

  var formHtml = ["<form class='form-inline' role='form' id='form-blacklist-remove'>",
    "<div class='form-group'>",
    "<label class='sr-only' for='devices'> " + inputLabel + " </label>",
    "<input type='text' id='devices' name='devices' placeholder='" + inputPlaceholder + "' class='form-control'>",
    "<button aria-expanded='false' type='submit' class='btn btn-primary' id='button-blacklist-remove' >",
    "<i class='fa fa-minus-circle'></i> " + actionName + " </button>",
    "</div>",
    "</form>"
  ].join(' ');
  $(formHtml).appendTo("#blacklist-content-container");

  var loadingDiv = ['<div id="form-blacklist-remove-loading" class="wok-list-loader-container wok-list-loading" style="display: none;">',
    '<div class="wok-list-loading-icon"></div>',
    '<div class="wok-list-loading-text">' + loadingText + '</div>',
    '</div>'
  ].join('');
  $(loadingDiv).appendTo("#blacklist-content-container");

  var removeForm = $('#form-blacklist-remove');
  var submitButton = $('#button-blacklist-remove');
  removeForm.on('submit', actionCallBack);
  submitButton.on('click', actionCallBack);

  var helpHtml = ["<p class='help-block'>",
    "<i class='fa fa-info-circle'></i>",
    helpText,
    "</p>"
  ].join(' ');

  var noteHtml = ["<p>",
    noteText,
    "</p>"
  ].join('');

  $(helpHtml).appendTo("#blacklist-content-container");
  $(noteHtml).appendTo("#blacklist-content-container");
};

gingers390x.validateFormData = function(formData) {
  devices = formData['devices'];
  return (devices && devices.length > 0) ? true : false;
}

gingers390x.removeFromBlackList = function(event) {

  var formData = $('#form-blacklist-remove').serializeObject();
  if (gingers390x.validateFormData(formData)) {

    gingers390x.showLoading();
    gingers390x.disableBlActionButton();
    var taskAccepted = false;
    var onTaskAccepted = function() {
      if (taskAccepted) {
        return;
      }
      taskAccepted = true;
      wok.topic('gingers390x/removeBlacklistDevice').publish();
    };

    gingers390x.removeBlacklistDevice(formData, function(result) {
      onTaskAccepted();
      var successText = result['message'];
      wok.message.success(successText, '#alert-bl-modal-container');
      gingers390x.enableBlActionButton();
      $('#devices').val('');
      gingers390x.hideLoading();
      wok.topic('gingers390x/removeBlacklistDevice').publish();
    }, function(result) {
      // Error message from Async Task status
      if (result['message']) {
        var errText = result['message'];
      }
      // Error message from standard gingers390x exception
      else {
        var errText = result['responseJSON']['reason'];
      }
      result && wok.message.error(errText, '#alert-bl-modal-container', true);
      gingers390x.enableBlActionButton();
      taskAccepted;
      gingers390x.hideLoading();

    }, onTaskAccepted);

  } else {
    wok.message.error(i18n['GS390XBL007E'], '#alert-bl-modal-container');
  }
  event.preventDefault();
};

gingers390x.enableBlActionButton = function() {
  $('#button-blacklist-remove').prop("disabled", false);
};

gingers390x.disableBlActionButton = function() {
  $('#button-blacklist-remove').prop("disabled", true);
};

gingers390x.showLoading = function() {
  $("#form-blacklist-remove-loading").show();
};

gingers390x.hideLoading = function() {
  $("#form-blacklist-remove-loading").hide();
};
