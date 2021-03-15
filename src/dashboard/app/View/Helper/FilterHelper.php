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
class FilterHelper extends AppHelper {
	function link($field, $value) {
		$get_params = $this->get_request_params_with_defaults();
		if (isset($get_params[$field]) && ($get_params[$field] == $value)) {
			return '';
		}
		return '<a href="' . $this->here(array($field => $value, 'offset' => 0)) . '"><i class="icon icon-filter3" rel="tooltip" title="Filter"></i></a>';
	}

	function header_link($field) {
		$get_params = $this->get_request_params_with_defaults();
		if (!isset($get_params[$field])) {
			return '';
		}
		return '<a href="' . $this->here(array('offset' => 0), array($field)) . '"><i class="icon icon-nofilter" rel="tooltip" title="Remove filter"></i></a>';
	}

	function is_filtered($field) {
		$get_params = $this->get_request_params_with_defaults();
		return isset($get_params[$field]);
	}

	function get_filter_value($field) {
		$get_params = $this->get_request_params_with_defaults();
		if (!isset($get_params[$field])) {
			return null;
		}
		return $get_params[$field];
	}
}
