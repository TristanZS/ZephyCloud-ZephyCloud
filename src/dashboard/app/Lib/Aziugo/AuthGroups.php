<?php

class AuthGroups {
    public static $version = "1.0.0";
    //***************************************************
    // Get version
    //***************************************************
    public static function getVersion() {
        return self::$version;
    }

    //***************************************************
    // authoriz
    //***************************************************
    public static function authoriz($array_group_authoriz) {
        if (!Configure::read('config.use_saml')) {
            return true;
        }
        $array_user_groups = SessionComponent::read("Auth.User.groups_list");

        if (empty($array_user_groups)) {
            throw new InternalErrorException("Error authz");
        }

        if (in_array("admin", $array_user_groups)) { // Admin access all access
            return true;
        }

        if (in_array("dashboardDev", $array_user_groups)) { // dashboardDev access all access
            return true;
        }

        foreach ($array_user_groups as $user_group) {
            if (in_array($user_group, $array_group_authoriz)) {
                return true;
            }
        }
        return false;
    }

    //***************************************************
    // authoriz
    //***************************************************
    public static function authorizAndVerify($array_group_authoriz,
                                             $message = "You do not have access to this Page or functionality") {
        if (self::authoriz($array_group_authoriz) !== true) {
            throw new InternalErrorException($message);
        }
    }
}// Fin de class
