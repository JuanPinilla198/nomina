console.log("timehseet js loaded")
odoo.define('bi_website_mobile_timesheet.timesheet', function (require) {
'use strict';
	require('web.dom_ready');
	if ($('.new_timesheet').length) {
        var task_options = $("select[name='task']:enabled option:not(:first)");
        $('.new_timesheet').on('change', "select[name='project']", function () {
            var select = $("select[name='task']");
            task_options.detach();
            var displayed_task = task_options.filter("[data-project='"+($(this).val() || 0)+"']");
            var nb = displayed_task.appendTo(select).show();
            select.parent().toggle(nb.length>=1);
        });
        $('.new_timesheet').find("select[name='project']").change();
    }

    var core = require('web.core');
    var ajax = require('web.ajax');
    var rpc = require('web.rpc');
    var request
    var _t = core._t;
    
    $(document).ready(function(){
        $(".khush").click(function(ev){
            var delete_timesheet = confirm("Are you sure, you want to delete a timesheet?");
            if (delete_timesheet == true) {
                let ts_id = $(this).attr("data-field")
                ajax.jsonRpc('/my/delete_timesheet/', 'call', {
                    'ts_id':  ts_id,

                }).then(function (ts) {
                    location.reload();
                });
            } else {
                }
            })
        });
    
});