<?php

/**
 * Configures default file logging options
 */
App::uses('CakeLog', 'Log');

$conf_array = parse_ini_file(DASHBOARD_CONF_FILE, true)['dashboard'];
$log_level = trim(strtoupper($conf_array['log_level']));
$log_output = $conf_array['log_output'];

$log_types = array();
if ($log_level == "DEBUG") {
    array_push($log_types, 'debug');
    array_push($log_types, 'info');
    array_push($log_types, 'notice');
    array_push($log_types, 'warning');

}
if (($log_level == "INFO") || ($log_level == "NOTICE")) {
    array_push($log_types, 'info');
    array_push($log_types, 'notice');
    array_push($log_types, 'warning');
}
if (($log_level == "WARN") || ($log_level == "WARNING")) {
    array_push($log_types, 'warning');
}
array_push($log_types, 'error');
array_push($log_types, 'critical');
array_push($log_types, 'alert');
array_push($log_types, 'emergency');

if ($log_output == "syslog") {
    CakeLog::config('error', array(
        'engine' => 'Syslog',
        'types' => $log_types
    ));
}
else {
    if ($log_output == "stdout") {
        CakeLog::config('error', array(
            'engine' => 'Console',
            'types' => $log_types,
            'stream' => 'php://stdout'
        ));
    }
    else {
        if ($log_output == "stderr") {
            CakeLog::config('error', array(
                'engine' => 'Console',
                'types' => $log_types,
                'stream' => 'php://stderr'
            ));
        }
        else {
            CakeLog::config('error', array(
                'engine' => 'File',
                'types' => $log_types,
                'path' => rtrim(dirname($log_output), '/') . '/',
                'file' => preg_replace('/\\.log$/', '', basename($log_output))
            ));
        }
    }
}
