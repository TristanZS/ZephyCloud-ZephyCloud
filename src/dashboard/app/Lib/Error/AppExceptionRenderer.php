<?php

App::uses('ExceptionRenderer', 'Error');
App::uses('JsonView', 'View');

/*

This class manage special error rendering for API calls and ensure unauthorized errors work well setting minimal layout

*/
class AppExceptionRenderer extends ExceptionRenderer {

    public function render() {
    	if(Configure::read('config.use_saml')) {
			if(!$this->controller->Auth->loggedIn()) {
				 $this->controller->layout = 'error';
			}
		}
		try {
			if($this->controller->Api->is_api()) {
				$view = new JsonView($this->controller);
				$view->set(array(
					'data' => null,
					'error_msgs' => array($this->error->getMessage()),
					'success' => 0,
					'_serialize' => array('data', 'error_msgs', 'success')
				));
				$code = 500;
				if($this->error instanceof CakeError) {
					$code = ($this->error->getCode() >= 400 && $this->error->getCode() < 506) ? $this->error->getCode() : 500;
				}
				$this->controller->response->statusCode($code);
				$this->controller->response->body($view->render(null, null));
				$this->controller->response->type('js');
				$this->controller->response->send();
				return;
			}
		}
		catch(Exception $e) {
			CakeLog::write(LOG_ERR, static::_getMessage($e));
		}
		return parent::render();
    }
}
