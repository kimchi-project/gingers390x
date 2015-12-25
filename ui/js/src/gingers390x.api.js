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
var gingers390x = {

  widget: {},

  trackingTasks: [],

  /**
   * Get the i18 strings.
   */
  getI18n: function(suc, err, url, sync) {
    wok.requestJSON({
      url: url ? url : 'plugins/gingers390x/i18n.json',
      type: 'GET',
      resend: true,
      dataType: 'json',
      async: !sync,
      success: suc,
      error: err
    });
  },

  getTask: function(taskId, suc, err) {
    wok.requestJSON({
      url: 'plugins/gingers390x/tasks/' + encodeURIComponent(taskId),
      type: 'GET',
      contentType: 'application/json',
      dataType: 'json',
      success: suc,
      error: err
    });
  },

  getTasksByFilter: function(filter, suc, err, sync) {
    wok.requestJSON({
      url: 'plugins/gingers390x/tasks?' + filter,
      type: 'GET',
      contentType: 'application/json',
      dataType: 'json',
      async: !sync,
      success: suc,
      error: err
    });
  },

  trackTask: function(taskID, suc, err, progress) {
    var onTaskResponse = function(result) {
      var taskStatus = result['status'];
      switch (taskStatus) {
        case 'running':
          progress && progress(result);
          setTimeout(function() {
            gingers390x.trackTask(taskID, suc, err, progress);
          }, 2000);
          break;
        case 'finished':
          suc && suc(result);
          break;
        case 'failed':
          err && err(result);
          break;
        default:
          break;
      }
    };

    gingers390x.getTask(taskID, onTaskResponse, err);
    if (gingers390x.trackingTasks.indexOf(taskID) < 0)
      gingers390x.trackingTasks.push(taskID);
  },

  removeBlacklistDevice: function(devices, suc, err, progress) {

    var onResponse = function(data) {
      taskID = data['id'];
      gingers390x.trackTask(taskID, suc, err, progress);
    };

    function convetToList(key, value) {

      if (key === "devices" && typeof value === 'string') {
        val = value.split(",");
        finalVal = "["
        for (i = 0; i < val.length; i++) {
          if (i == 0) {
            finalVal = finalVal + JSON.stringify(val[i]);
          } else {
            finalVal = finalVal + "," + JSON.stringify(val[i]);
          }
        }
        finalVal = finalVal + "]"
        value = JSON.parse(finalVal);
      }
      return value;
    };

    wok.requestJSON({
      url: 'plugins/gingers390x/cio_ignore/remove',
      type: "POST",
      contentType: "application/json",
      data: JSON.stringify(devices, convetToList),
      dataType: "json",
      success: onResponse,
      error: err
    });
  },

  listNetworks: function(suc, err) {
    wok.requestJSON({
      url: 'plugins/gingers390x/nwdevices?_configured=false',
      type: 'GET',
      contentType: 'application/json',
      dataType: 'json',
      success: suc,
      error: function(data) {
        wok.message.error(data.responseJSON.reason);
      }
    });
  },

  configureNetwork: function(device, configure, suc, err, progress) {
    var device = encodeURIComponent(device);
    var onResponse = function(data) {
      taskID = data['id'];
      gingers390x.trackTask(taskID, suc, err, progress);
    };

    wok.requestJSON({
      url: "plugins/gingers390x/nwdevices/" + device +
        '/' + (configure === true ? 'configure' : 'unconfigure'),
      type: "POST",
      contentType: "application/json",
      dataType: "json",
      success: onResponse,
      error: err
    });
  },
listFCPluns: function(suc, err) {
    wok.requestJSON({
      url: 'plugins/gingers390x/fcluns?type="disk"&configured="false"',
      type: 'GET',
      contentType: 'application/json',
      dataType: 'json',
      success: suc,
      error: function(data) {
        wok.message.error(data.responseJSON.reason);
      }
    });
  },
  addLuns: function(settings, suc, err) {
    wok.requestJSON({
      url: "/plugins/gingers390x/fcluns",
      type: "POST",
      contentType: "application/json",
      data: JSON.stringify(settings),
      dataType: "json",
      success: suc,
      error: err
    });
  },
  getLunsScanStatus: function(suc, err) {
    wok.requestJSON({
      url: 'plugins/gingers390x/lunscan',
      type: 'GET',
      contentType: 'application/json',
      dataType: 'json',
      success: suc,
      error: function(data) {
        wok.message.error(data.responseJSON.reason);
      }
    });
  },
  lunsScanStatusChange: function(enabled, suc) {
    wok.requestJSON({
      url: "plugins/gingers390x/lunscan/" +
        (enabled === true ? 'disable' : 'enable'),
      type: "POST",
      contentType: "application/json",
      dataType: "json",
      success: suc,
      error: function(data) {
        wok.message.error(data.responseJSON.reason);
      }
    });
  },
  lunsDiscovery: function(suc, err, progress) {
    var onResponse = function(data) {
      taskID = data['id'];
      gingers390x.trackTask(taskID, suc, err, progress);
    };
    wok.requestJSON({
      url: "plugins/gingers390x/lunscan/trigger",
      type: "POST",
      contentType: "application/json",
      dataType: "json",
      success: onResponse,
      error: err
    });
  },
  configureFcpSanAdapter: function(device, enable, suc, err, progress) {
    var device = encodeURIComponent(device);

    wok.requestJSON({
      url: "plugins/gingers390x/storagedevices/" + device +
        '/' + (enable === true ? 'online' : 'offline'),
      type: "POST",
      contentType: "application/json",
      dataType: "json",
      success: suc,
      error: err
    });
  },

  configureEckd: function(device, enable, suc, err, progress) {
    var device = encodeURIComponent(device);
    var onResponse = function(data) {
      taskID = data['id'];
      gingers390x.trackTask(taskID, suc, err, progress);
    };

    wok.requestJSON({
      url: "plugins/gingers390x/storagedevices/" + device +
        '/' + (enable === true ? 'online' : 'offline'),
      type: "POST",
      contentType: "application/json",
      dataType: "json",
      success: suc,
      error: err
    });
  },
  listFcpSanAdapter: function(suc, err) {
    wok.requestJSON({
      url: 'plugins/gingers390x/storagedevices?_type=zfcp&status=offline',
      type: 'GET',
      contentType: 'application/json',
      dataType: 'json',
      success: suc,
      error: function(data) {
        gingers390x.messagecloseable.error(data.responseJSON.reason);
      }
    });
  },
  listEckd: function(suc, err) {
    wok.requestJSON({
      url: 'plugins/gingers390x/storagedevices?_type=dasd-eckd&status=offline',
      type: 'GET',
      contentType: 'application/json',
      dataType: 'json',
      success: suc,
      error: function(data) {
        gingers390x.messagecloseable.error(data.responseJSON.reason);
      }
    });
  }

};
