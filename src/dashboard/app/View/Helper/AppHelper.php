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

App::uses('Helper', 'View');

/**
 * Application helper
 *
 * Add your application-wide methods in the class below, your helpers
 * will inherit them.
 *
 * @package       app.View.Helper
 */
class AppHelper extends Helper {
	public $helpers = array('Html');
	public $_default_params = array();

	public function __construct(View $View, $settings = array()) {
		parent::__construct($View, $settings);
		$this->_default_params = $View->viewVars['__default_params'];
	}

	public function get_default_params() {
		return $this->_default_params;
	}

	public function set_default_params($default_params) {
		$this->_default_params = array_merge($this->_default_params, $default_params);
	}

	public function get_request_params_with_defaults() {
		return array_merge($this->_default_params, $this->request->query);
	}

	public function get_params($param_list) {
		$result = array();
		$all_params = $this->get_request_params_with_defaults();
		foreach($all_params as $key => $value) {
			if(in_array($key, $param_list)) {
				$result[$key] = $value;
			}
		}
		return $result;
	}

	public function here($new_args = array(), $args_to_remove = array()) {
		if(!is_array($args_to_remove)) {
			$args_to_remove = array($args_to_remove);
		}
		$params = $this->request->params;
		unset($params["pass"]);
		unset($params["isAjax"]);
		unset($params["models"]);
		$get_params = $this->request->query;
		foreach($params['named'] as $key => $value) {
			if(!isset($get_params[$key]) && !in_array($key, $args_to_remove)) {
				$params[$key] = $value;
			}
		}
		unset($params['named']);
		foreach($get_params as $key => $value) {
			if(in_array($key, $args_to_remove)) {
				unset($get_params[$key]);
			}
		}
		foreach($new_args as $key => $value) {
			if(array_key_exists($key, $params)) {
				$params[$key] = $value;
			}
			else {
				$get_params[$key] = $value;
			}
		}
		if(count($get_params) > 0) {
			$params['?'] = $get_params;
		}
		return $this->Html->url($params);
	}
}
