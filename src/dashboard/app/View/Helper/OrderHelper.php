<?php
/**
 * Application level View Helper
 *
 * This file is application-wide helper file. You can put all
 * application-wide helper-related methods here.
 *
 * CakePHP(tm) : Rapid Development Framework (https://cakephp.org)
 * Copyright (c) Cake Software Foundation, Inc. (https://cakefoundation.org)
 *
 * Licensed under The MIT License
 * For full copyright and license information, please see the LICENSE.txt
 * Redistributions of files must retain the above copyright notice.
 *
 * @copyright     Copyright (c) Cake Software Foundation, Inc. (https://cakefoundation.org)
 * @link          https://cakephp.org CakePHP(tm) Project
 * @package       app.View.Helper
 * @since         CakePHP(tm) v 0.2.9
 * @license       https://opensource.org/licenses/mit-license.php MIT License
 */

App::uses('AppHelper', 'View');

/**
 * Application helper
 *
 * Add your application-wide methods in the class below, your helpers
 * will inherit them.
 *
 * @package       app.View.Helper
 */
class OrderHelper extends AppHelper {
	function change_order($field, $asc=true) {
		$get_params = $this->get_request_params_with_defaults();
		if(isset($get_params['order'])) {
			$old_order = explode(",", $get_params['order']);
			$new_order = array($field." ".($asc ? "ASC" : "DESC"));
			foreach($old_order as $field_and_dir) {
				$len = strlen($field)+1;
    			if(substr($field_and_dir, 0, $len) !== $field." ") {
    				array_push($new_order, $field_and_dir);
    			}
			}
			$order = implode(",", $new_order);
		}
		else {
			$order = $field." ".($asc ? "ASC" : "DESC");
		}
		return $this->here(array("order" => $order, "offset" => 0));
	}

	function get_current_order($field, $first_only=false) {
		$get_params = $this->get_request_params_with_defaults();
		if(isset($get_params['order'])) {
			$old_order = explode(",", $get_params['order']);
			foreach($old_order as $old_field_and_dir) {
				$old_field_info = explode(" ", $old_field_and_dir, 2);
				if($old_field_info[0] != $field) {
					if($first_only) {
						return null;
					}
				}
				else {
					if (count($old_field_info) == 1) {
						return "ASC";
					}
					if (strtoupper($old_field_info[1]) == "DESC") {
						return "DESC";
					}
					return "ASC";
				}
			}
		}
		return null;
	}

	function links($field) {
		$current_order = $this->get_current_order($field, true);
		if($current_order == "ASC") {
			return '<a href="'.$this->change_order($field, false).'"><i class="icon icon-arrow-up5" rel="tooltip" title="Sort ascending"></i></a>';
		}
		else if($current_order == "DESC") {
			return '<a href="'.$this->change_order($field).'"><i class="icon icon-arrow-down5" rel="tooltip" title="Sort descending"></i></a>';
		}
		else {
			return '<a href="'.$this->change_order($field).'"><i class="icon icon-menu-open" rel="tooltip" title="Sort"></i></a>';
		}
	}

}
