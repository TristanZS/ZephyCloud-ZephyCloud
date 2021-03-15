<?php

class AziugoTools {
	public static $version = "1.0.0";
	//************************************
	// coupeur long titre
	//************************************

		public static function cutTitle($value,$separator = ".......",$sizemax = 58, $cut_last = 7 ){
			if (strlen($value) > $sizemax) {
				return  substr($value, 0, ($sizemax-$cut_last-strlen($separator)))  .   $separator   .   substr($value, -$cut_last);
			}else{
				return $value;
			}
		}

		public static function human_date($timestamp) {
		    if($timestamp === null) {
		        return "";
		    }
		    if (!is_numeric($timestamp)) {
		        return "";
		    }
		    if(($timestamp > PHP_INT_MAX) || ($timestamp < ~PHP_INT_MAX)){
		        return "";
		    }
		    return date('d/m/Y H:i:s', $timestamp)." UTC";
		}
}// Fin de class
