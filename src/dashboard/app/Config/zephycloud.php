<?php


$proc_groups = file_get_contents("/proc/1/cgroup");
$inside_docker = (strpos($proc_groups, "lxc") !== false) || (strpos($proc_groups, "docker") !== false);
$conf_array = parse_ini_file(DASHBOARD_CONF_FILE, true)['dashboard'];

$use_saml_str = strtolower($conf_array['use_saml']);
$use_saml = ($use_saml_str == "true") || ($use_saml_str == "1") || ($use_saml_str == "on") || ($use_saml_str == "yes");

$config['zephycloud']['url'] = 'https://' . $conf_array['server_name'];
$config['zephycloud']['ignore_https'] = $inside_docker;
$config['zephycloud']['login'] = $conf_array['admin_user'];
$config['zephycloud']['password'] = $conf_array['admin_password'];
$config['zephycloud']['signin_url'] = $conf_array['signin_url'];
$config['zephycloud']['provider_pricing_api'] = $conf_array['provider_pricing_api'];
$allowed_users = json_decode($conf_array['allowed_users']);
if ($use_saml && is_array($allowed_users)) {
    $config['zephycloud']['allowed_users'] = $allowed_users;
}
else {
    $config['zephycloud']['allowed_users'] = array();
}
