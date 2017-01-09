/*
 * Copyright IBM Corp, 2016-2017
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
 */
gingers390x.initOSAport = function() {
    $('.selectpicker').selectpicker();
    $('.selectpicker').selectpicker('refresh');
    $('#osaport-submit').off();
    $('#osaport-submit').prop("disabled", true);
    OSAportvalue = $('.selectpicker').val();
    $('.selectpicker').on('change', function() {
      if($(this).val() == OSAportvalue){
        $('#osaport-submit').prop("disabled", true);
      }else{
         $('#osaport-submit').prop("disabled", false);
      }
    });
    var networkConfigTable = $('#network-configuration').DataTable();
    var selectedRows = ginger.listNetworkConfig.rows_indexes;

    if (selectedRows && (selectedRows.length == 1)) {
        var selectedRowDetails = networkConfigTable.row(selectedRows[0]).data();
        var networkType = selectedRowDetails[2];
        gingers390x.listNetworksOSA(networkType, function(result) {
            var current_osaport = result['osa_portno'];
            $('#osa-port-status-textbox').text(current_osaport);
            $('#osaportType').selectpicker("val", current_osaport);
            OSAportvalue = current_osaport;
        }, function() {});
    }
    $('#osaport-submit').on('click', function() {
        var osaport = {};
        osaport.osa_portno = parseInt($('#osaportType').val());
        var settings = {
            content: i18n['GS390XOSA001M'].replace("%1", '<strong>' + networkType + '</strong>').replace("%2", '<strong>' + osaport.osa_portno + '</strong>'),
            confirm: i18n['GS390XOSA003M']
        };
        wok.confirm(settings, function() {
            $('#OSAport-update-loading').show();
            gingers390x.UpdateNetworksOSA(osaport, networkType, function(result) {
                wok.window.close();
                gingers390x.refreshNetworkPage();
                wok.message.success(i18n['GS390XOSA002M'] + networkType, '#message-network-configuration-container-area');
            }, function(err) {
                $('#OSAport-update-loading').hide();
                wok.message.error(err.responseJSON.reason, "#osaport-message");
            });
        });
    });
    $('#osa-port-button-close').on('click', function() {
        wok.window.close();
        gingers390x.refreshNetworkPage();
    });
    $('#osaport-cancel').on('click', function() {
        wok.window.close();
    });
    gingers390x.refreshNetworkPage = function() {
        ginger.listNetworkConfig.refreshNetworkConfigurationDatatable();
        ginger.listNetworkConfig.rows_indexes = new Array();
        setTimeout(function() {
            gingers390x.networkRefreshHandler();
            gingers390x.networkConfigRowSelection();
        }, 3000);
        $('#network-configuration-content-area').on('shown.bs.dropdown', '.nw-configuration-add', function() {
            if (!($('#nw-add-adapter-button', $(this)).length))
                gingers390x.addNetworkAdapterButton();
        });
        $('#network-configuration-content-area').on('shown.bs.dropdown', '.nw-configuration-action', function() {
            if (!($('#nw-osa-port-button', $(this)).length))
                gingers390x.addOSAportButton();
        });
    }
}
