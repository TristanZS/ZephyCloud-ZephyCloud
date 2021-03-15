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
class PageHelper extends AppHelper {
	protected $_list_info = array();

	public function __construct(View $View, $settings = array()) {
		parent::__construct($View, $settings);
		$this->_list_info = $View->viewVars['__PageComponent'];
	}

	public function set_total_count($list_name, $count) {
		$this->_list_info[$list_name] = array(
			'total_size' => $count,
			'page_size' => 25,
			'offset' => 0
		);
	}

	public function paginate($list_name) {
		if(isset($this->_list_info[$list_name])) {
			$offset = $this->_list_info[$list_name]['offset'];
			$page_size = $this->_list_info[$list_name]['page_size'];
			$total_size = $this->_list_info[$list_name]['total_size'];
		}
		else {
			$offset = 0;
			$page_size = 25;
			$total_size = null;
		}

		$params = $this->get_request_params_with_defaults();
		if(isset($params['offset']) && preg_match('/^\d+$/', $params['offset'])) {
			$offset = intval($params['offset']);
		}
		if(isset($params['limit']) && preg_match('/^\d+$/', $params['limit'])) {
			$page_size= intval($params['limit']);
		}
		$result = '<div class="pagination_block" align="center">';
		if($total_size === null) {
			if($offset != 0) {
				$result .= '<a class="btn btn-info" href="'.$this->here(array('offset' => max(0, $offset - $page_size))).'">Previous</a>';
			}
			else {
				$result .= '<a class="btn bg-grey-300" href="#">Previous</a>';
			}
			$result .= '<a class="btn btn-info" href="'.$this->here(array('offset' => max(0, $offset + $page_size))).'">Next</a>';
		}
		else {
			$page_window_size = 2;
			$max_page = floor($total_size / $page_size); // 0-index
			if($max_page == 0) {
				return '';
			}
			$current_page = floor($offset / $page_size); // 0-index

			if($current_page > 0) {
				$result .= '<a class="btn btn-info" href="'.$this->here(array('offset' => ($current_page-1)*$page_size)).'">Previous</a>';
				if($current_page > $page_window_size) {
					$result .= '<a class="btn btn-info" href="'.$this->here(array('offset' => 0)).'">1</a>';
				}
				if($current_page > $page_window_size + 1) {
					$result .= '<span class="btn_ellipsis">...</span>';
				}
				for($i = max(0, $current_page - $page_window_size); $i < $current_page; $i++) {
					$result .= '<a class="btn btn-info" href="'.$this->here(array('offset' => $i*$page_size)).'">'.($i+1).'</a>';
				}
			}
			else {
				$result .= '<a class="btn bg-grey-300 disabled" href="#" role="button" aria-disabled="true">Previous</a>';
			}
			$result .= '<a class="btn bg-success" href="" role="button" aria-disabled="true" style="pointer-events: none;" onclick="return false;">'.($current_page+1).'</a>';
			if($current_page < $max_page) {
				for($i = $current_page +1; $i <= min($max_page, $current_page + $page_window_size); $i++) {
					$result .= '<a class="btn btn-info" href="'.$this->here(array('offset' => $i*$page_size)).'">'.($i+1).'</a>';
				}
				if($current_page < $max_page - $page_window_size-1) {
					$result .= '<span class="btn_ellipsis">...</span>';
				}
				if($current_page < $max_page - $page_window_size) {
					$result .= '<a class="btn btn-info" href="'.$this->here(array('offset' => $max_page*$page_size)).'">'.($max_page+1).'</a>';
				}
				$result .= '<a class="btn btn-info" href="'.$this->here(array('offset' => ($current_page+1)*$page_size)).'">Next</a>';
			}
			else {
				$result .= '<a class="btn bg-grey-300 disabled" href="#" role="button" aria-disabled="true">Next</a>';
			}
		}
		$result .= '</div>';
		return $result;
	}
}
