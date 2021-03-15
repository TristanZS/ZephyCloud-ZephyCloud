<?php

class ZephyCloud extends AppModel {
    public $name = 'ZephyCloud';
    public $useTable = false;
    private $api_url = null;
    private $api_login = null;
    private $api_password = null;


    //***********************************************
    // __construct
    //***********************************************
    public function __construct() {

        $this->api_url = Configure::read('zephycloud.url');
        $this->api_login = Configure::read('zephycloud.login');
        $this->api_password = Configure::read('zephycloud.password');
        $this->ssl_self_signed = Configure::read('zephycloud.ignore_https');

        if (empty($this->api_url)) {
            throw new Exception("api url is empty");
        }

        if (empty($this->api_login)) {
            throw new Exception("api login is empty");
        }

        if (empty($this->api_password)) {
            throw new Exception("api password is empty");
        }

    }

    //***********************************************
    // Basic Auth configuration
    //***********************************************

    public function setConfig($url, $login, $password) {
        $this->setUrl($url);
        $this->setLogin($login);
        $this->setPassword($password);
    }

    public function setUrl($value) {
        $this->api_url = $value;
    }

    public function setLogin($value) {
        $this->api_login = $value;
    }

    public function setPassword($value) {
        $this->api_password = $value;
    }

    public function getUrl() {
        return $this->api_url;
    }

    public function getLogin() {
        return $this->api_login;
    }

    public function getPassword() {
        return $this->api_password;
    }

    //***********************************************
    // getUsers
    //***********************************************
    public function request($route, $data = []) {
        $HttpSocket = new HttpSocket(array(
            'ssl_verify_peer' => !$this->ssl_self_signed,
            'ssl_verify_host' => !$this->ssl_self_signed,
            'ssl_allow_self_signed' => $this->ssl_self_signed,
        ));
        $reponse = $HttpSocket->post($this->getUrl() . $route, json_encode($data), array(
            'header' => array(
                'Content-Type' => 'application/json'
            ),
            'auth' => array(
                'method' => 'Basic',
                'user' => $this->getLogin(),
                'pass' => $this->getPassword()
            )
        ));
        return $reponse;
    }

    public function request_or_fail($route, $data = []) {
		$body = $this->_do_request_and_check($route, $data);
		return $body['data'];
    }

	public function request_list_or_fail($route, $data = []) {
		$body = $this->_do_request_and_check($route, $data);
		$total = null;
		if(isset($body['total']) && preg_match('/^\d+$/', $body['total'])) {
			$total = intval($body['total']);
		}
		return array('list' => $body['data'], 'total_count' => $total);
	}

	protected function _do_request_and_check($route, $data = []) {
		$raw_response = $this->request($route, $data);
		if (empty($raw_response->body)) {
			throw new Exception("admin api request failed: empty response");
		}
		try {
			$body = json_decode($raw_response->body, true);
		}
		catch(Exception $e) {
			throw new Exception("admin api request failed: bad json: ".$e->getMessage());
		}
		if(!isset($body['success'])) {
			throw new Exception("admin api request failed: invalid format: no success field");
		}
		if($body["success"] != 1) {
			if(isset($body["error_msgs"]) && !empty($body["error_msgs"])) {
				if(is_array($body["error_msgs"])){
					throw new Exception("admin api request failed: ".implode("; ", $body["error_msgs"]));
				}
				else {
					throw new Exception("admin api request failed: ".$body["error_msgs"]);
				}
			}
			else {
				throw new Exception("admin api request failed: unspecified error");
			}
		}
		if(!array_key_exists('data', $body)) {
			throw new Exception("admin api request failed: invalid format: no data field: ".var_export($body));
		}
		return $body;
	}
} //--> Fin de class


