<?php
/**
 * Application level Controller
 *
 * This file is application-wide controller file. You can put all
 * application-wide controller-related methods here.
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
 * @package       app.Controller
 * @since         CakePHP(tm) v 0.2.9
 * @license       https://opensource.org/licenses/mit-license.php MIT License
 */

App::uses('Controller', 'Controller');
App::uses('CakeTime', 'Utility');
App::uses('HttpSocket', 'Network/Http');
App::uses('AuthGroups', 'Lib/Aziugo');
App::uses('AziugoTools', 'Lib/Aziugo');
App::uses('CakeNumber', 'Utility');
App::uses('Cake', 'View', 'JsonView');

/**
 * Application Controller
 *
 * Add your application-wide methods in the class below, your controllers
 * will inherit them.
 *
 * @package        app.Controller
 * @link        https://book.cakephp.org/2.0/en/controllers.html#the-app-controller
 */
class AppController extends Controller {

    public $components = array(
        'Session',
        'RequestHandler',
        'Flash',
        'Paginator',
        'Api',
		'Page'
    );

    public $helpers = array('Html', 'Form', 'Session', 'Text', 'Time', 'Page', 'Filter', 'Order');
    public $uses = array(
        "Users",
        "ZephyCloud"
    );
    public $time_machine_time = null;
	protected $_default_params = array();

    public function __construct($request = null, $response = null) {
        if (Configure::read('config.use_saml')) {
            $this->components['Auth'] = array(
                'loginAction' => array('controller' => 'auth', 'action' => 'login'),
                'authError' => 'Did you really think you were allowed to see that?',
                'authenticate' => array('Saml'),
                'loginRedirect' => $_SERVER["REQUEST_SCHEME"] . "://" . $_SERVER["HTTP_HOST"] . "/dashboard/"
            );
        }
        // if(Configure::read('debug') > 0) {
        //     array_push($this->components, 'DebugKit.Toolbar');
        // }
        parent::__construct($request, $response);
    }

	public function get_default_params() {
		return $this->_default_params;
	}

	public function set_default_params($default_params) {
		$this->_default_params = array_merge($this->_default_params, $default_params);
	}

	public function get_request_params_with_defaults() {
		return array_merge($this->_default_params, $this->request->query, $this->request->data);
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


    function beforeFilter() {
        parent::beforeFilter();

        $this->load_time_machine();
        if (Configure::read('config.use_saml')) {
        	// Authorise les erreurs non authentifiées
            $this->Auth->allow(array('error400', 'error500', 'missing_controller'));
        }

        $this->set('__default_params', $this->_default_params);

		// Doesn't work, so we still need to call $this->set_page_as_api() manually
        // if($this->RequestHandler->ext == 'json') {
		// 	$this->set_page_as_api();
		// }

    }

    public function beforeRender() {
    	parent::beforeRender();
		/*$controller->set('__PageComponent', array(
			'_total_count' => $this->_total_count,
			'_per_page' => $this->_per_page,
			'_offset' => $this->_offset
		));*/
    	if($this->Api->is_api()) { // Manage global json format
			$this->set(array(
				'data' => $this->Api->get_result(),
				'error_msgs' => array(),
				'success' => 1,
				'_serialize' => array('data', 'success', 'error_msgs')
			));
		}
    }

    function load_time_machine() {
        if(isset($_COOKIE["time_machine_time"]) && is_numeric($_COOKIE["time_machine_time"])) {
            $this->time_machine_time = (int)$_COOKIE["time_machine_time"];
        }
        else {
            $this->time_machine_time = null;
        }
        $this->set("time_machine_time", $this->time_machine_time);
        $this->set("time_machine_enabled", true);
    }

    function disable_time_machine() {
        if($this->time_machine_time) {
            setcookie("time_machine_time", null);
            $this->Flash->info('Time machine is disabled');
            $this->set("time_machine_enabled", false);
        }
    }

    function set_all($params) {
    	foreach($params as $key => $value) {
    		$this->set($key, $value);
		}
	}

    function set_page_as_api() {
    	$this->Api->set_api();
    	$this->viewClass = 'Json';
    	$this->layout = null;
    }

    function set_api_result($result) {
    	$this->set_page_as_api();
    	$this->Api->set_result($result);
    }

    function redirect_referer_or($param) {
    	if(!empty($this->referer()) &&
			(strpos($this->referer(), $_SERVER["REQUEST_SCHEME"] . "://" . $_SERVER["HTTP_HOST"]) === 0)) {
    		return $this->redirect($this->referer());
		}
    	return $this->redirect($param);
	}

	function log_exception($e) {
		CakeLog::write(LOG_ERR, static::_getMessage($e));
	}

	protected static function _getMessage($exception) {
		$message = sprintf("[%s] %s",
			get_class($exception),
			$exception->getMessage()
		);
		if (method_exists($exception, 'getAttributes')) {
			$attributes = $exception->getAttributes();
			if ($attributes) {
				$message .= "\nException Attributes: " . var_export($exception->getAttributes(), true);
			}
		}
		if (PHP_SAPI !== 'cli') {
			$request = Router::getRequest();
			if ($request) {
				$message .= "\nRequest URL: " . $request->here();
			}
		}
		$message .= "\nStack Trace:\n" . $exception->getTraceAsString();
		return $message;
	}
}
