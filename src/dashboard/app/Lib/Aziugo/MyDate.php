<?php

class MyDate {
    public static $version = "1.0.0";
    //***************************************************
    // Get version
    //***************************************************
    public static function getVersion() {
        return self::$version;
    }

    //************************************
    // getDiffDays
    //************************************
    public static function getDiffDays($value) {
        $now = new DateTime('now');
        $date = new DateTime($value);
        $interval = $now->diff($date);
        return $interval->days;
    }
}// Fin de class
