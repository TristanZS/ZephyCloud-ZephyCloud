<?php

App::uses('ErrorHandler', 'Error');
App::uses('AppExceptionRenderer', 'Error');

// in app/Lib/AppExceptionHandler.php
class AppErrorHandler extends ErrorHandler {
    public static function handleException($exception) {
        $config = Configure::read('Exception');
        static::_log($exception, $config);

		$renderer_class = isset($config['renderer']) ? $config['renderer'] : 'AppExceptionRenderer';
		if (($renderer_class !== 'AppExceptionRenderer') && ($renderer_class !== 'ExceptionRenderer')) {
			list($plugin, $renderer_class) = pluginSplit($renderer_class, true);
			App::uses($renderer_class, $plugin . 'Error');
		}
		try {
			$error_renderer = new $renderer_class($exception);
			if(Configure::read('config.use_saml')) {
				$base_saml_url = rtrim(Configure::read('Saml.settings')['baseurl'], "/");
			    if(!$error_renderer->controller->Auth->loggedIn() &&
				   (strpos($error_renderer->controller->referer(), $base_saml_url) !== 0)) { // prevent infinite redirect loop
					// Redirect to authentication page
					$auth = new OneLogin_Saml2_Auth(Configure::read('Saml.settings'));
					$url = $error_renderer->controller->Auth->redirectUrl();
					if (strpos($url, 'http' !== 0)) {
						$url = $_SERVER["REQUEST_SCHEME"] . "://" . $_SERVER["HTTP_HOST"] . "/" . ltrim($url, "/");
					}
					$auth->login($url);
					return;
			    }
            }
			$error_renderer->render();
		}
		catch (Exception $e) {
			set_error_handler(Configure::read('Error.handler')); // Should be using configured ErrorHandler
			Configure::write('Error.trace', false); // trace is useless here since it's internal
			$message = sprintf("[%s] %s\n%s", // Keeping same message format
				get_class($e),
				$e->getMessage(),
				$e->getTraceAsString()
			);
			static::$_bailExceptionRendering = true;
			trigger_error($message, E_USER_ERROR);
		}
    }

    protected static function _log($exception, $config) {
        if (empty($config['log'])) {
			return false;
		}

		if (!empty($config['skipLog'])) {
			foreach ((array)$config['skipLog'] as $class) {
				if ($exception instanceof $class) {
					try {
						$current_url = (isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on' ? "https" : "http") . "://$_SERVER[HTTP_HOST]$_SERVER[REQUEST_URI]";
					}
					catch(Exception $e) {
						$current_url = "unknown url";
					}
					return CakeLog::write(LOG_WARNING, $exception->getMessage()." for ".$current_url);
				}
			}
		}
		return CakeLog::write(LOG_ERR, static::_getMessage($exception));
    }
}
