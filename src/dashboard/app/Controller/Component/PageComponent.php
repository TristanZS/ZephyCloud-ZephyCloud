<?php

App::uses('Component', 'Controller');

class PageComponent extends Component {
	protected $_list_info = array();

	public function initialize(Controller $controller) {
        $controller->set('__PageComponent', $this->_list_info);
    }

	public function set_total_count($list_name, $count) {
		$this->_list_info[$list_name] = array(
			'total_size' => $count,
			'page_size' => 25,
			'offset' => 0
		);
	}

	function beforeRender(Controller $controller) {
		parent::beforeRender($controller);
		$controller->set('__PageComponent', $this->_list_info);
	}
}
