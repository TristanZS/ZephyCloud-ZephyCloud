<?php

App::uses('Component', 'Controller');

class ApiComponent extends Component {
    protected static $_is_api_page = false;
    protected $_api_result = null;
    protected $_has_api_result = false;

    public function __construct(ComponentCollection $collection, $settings = array()) {
    	parent::__construct($collection, $settings);
    }

	public function set_api() {
		ApiComponent::$_is_api_page = true;
	}

	public function is_api() {
		return ApiComponent::$_is_api_page;
	}

	public function set_result($result) {
		$this->_has_api_result = true;
		$this->_api_result = $result;
	}

	public function has_result() {
		return $this->_has_api_result;
	}

	public function get_result() {
		if(!$this->has_result()) {
			throw new Exception("Unknown API error");
		}
		return $this->_api_result;
	}
}
