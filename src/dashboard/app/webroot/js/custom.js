function setCookie(name,value,hours) {
    var expires = "";
    if (hours) {
        var date = new Date();
        date.setTime(date.getTime() + (hours*60*60*1000));
        expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "")  + expires + "; path=/";
}

function getCookie(name) {
    var nameEQ = name + "=";
    var ca = document.cookie.split(';');
    for(var i=0;i < ca.length;i++) {
        var c = ca[i];
        while (c.charAt(0)==' ') c = c.substring(1,c.length);
        if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
    }
    return null;
}

function eraseCookie(name) {
    document.cookie = name+'=; Max-Age=-99999999;';
}

function escapeHtml(html){
  var text = document.createTextNode(html);
  var p = document.createElement('p');
  p.appendChild(text);
  return p.innerHTML;
}

function display_error(msg, title=null){
    var text = '<div class="alert alert-danger bg-light text-default alert-styled-left alert-arrow-left alert-dismissible">';
    text += '<button type="button" class="close" data-dismiss="alert"><span>×</span></button>';
    if(title) {
      text += '<h6 class="alert-heading font-weight-semibold mb-1">'+escapeHtml(title)+'</h6>';
    }
    text += escapeHtml(msg);
    text += '</div>';
    $(".flash-container").append(text);
}

document.addEventListener('DOMContentLoaded', function() {
    var moment_now = moment();
    var start_date = moment_now.clone();
    var ranges = {
        'Yesterday': [moment_now.clone().subtract(1, 'days'), moment_now.clone().subtract(1, 'days')],
        'A week ago': [moment_now.clone().subtract(6, 'days'), moment_now.clone().subtract(6, 'days')],
        'A month Ago': [moment_now.clone().subtract(29, 'days'), moment_now.clone().subtract(29, 'days')],
        'Beginning of this month': [moment_now.clone().startOf('month'), moment_now.clone().startOf('month')],
    };
    var time_machine_time = Number(getCookie("time_machine_time"));
    if(!isNaN(time_machine_time) && (time_machine_time != 0)) {
        ranges['Back To The Future'] = [moment_now, moment_now];
        start_date = moment.unix(time_machine_time);
        setCookie("time_machine_time", time_machine_time, 1);  // Reset the cookie to disable expiry
    }

    $('.time-machine').daterangepicker({
            "startDate": start_date.clone(),
            "maxDate": moment_now.clone(),
            "ranges": ranges,
            "alwaysShowCalendars": false,
            "autoUpdateInput": true,
            "linkedCalendars": false,
            "opens": "left",
            "showCustomRangeLabel": true,
            "showDropdowns": true,
            "timePicker": true,
            "timePicker24Hour": true,
            "singleDatePicker": true,
            "locale": {
                "format": "DD/MM/YYYY",
                "customRangeLabel": "Custom date",
                "firstDay": 1
            }
        },
        function(start, end, label) {
           console.log('On select: '+start.toISOString());
           if((start >= moment_now) || (label == 'Back To The Future')) {
                setCookie("time_machine_time", null, 1);
           }
           else {
                setCookie("time_machine_time", start.unix(), 1);
           }
           location.reload();
        }
    );

    $('.daterangepicker .ranges ul').show();
    $('.daterangepicker .daterangepicker-inputs').hide();
});


function api_call(url, params) {
	var on_success = params.on_success || function(){};
	var on_error = params.on_error || function(){};
	var on_complete = params.on_complete || function(){};

	$.ajax({
	  url: url,
	  processData: false,
	  success: function( data, textStatus, jQxhr ){
		  var result = null;
		  if(typeof(data) === "object") {
			result = data;
		  }
		  else {
			try {
			  result = JSON.parse(data);
			}
			catch(error) {
			  on_error([error.toString()]);
			  return;
			}
		  }
		  if(!result.hasOwnProperty('success') || !result.hasOwnProperty('data')) {
		  	on_error(["Invalid response format"]);
			return;
		  }
		  if(result['success'] != 1) {
			 if(result.hasOwnProperty('error_msgs') && result['error_msgs'].isArray() && result['error_msgs'].length() > 0) {
			   on_error(result['error_msgs']);
			 }
			 else {
			   on_error(["Invalid response format"]);
			 }
			 return;
		  }
		  on_success(result["data"]);
	  },
	  error: function( jqXhr, textStatus, errorThrown ){
	      on_error([errorThrown.toString()]);
	  },
	  complete: function() {
		  on_complete();
	  }
  });
}
