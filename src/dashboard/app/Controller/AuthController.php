<?php
/**
 * Static content controller.
 *
 * This file will render views from views/pages/
 *
 * CakePHP(tm) : Rapid Development Framework (http://cakephp.org)
 * Copyright (c) Cake Software Foundation, Inc. (http://cakefoundation.org)
 *
 * Licensed under The MIT License
 * For full copyright and license information, please see the LICENSE.txt
 * Redistributions of files must retain the above copyright notice.
 *
 * @copyright     Copyright (c) Cake Software Foundation, Inc. (http://cakefoundation.org)
 * @link          http://cakephp.org CakePHP(tm) Project
 * @package       app.Controller
 * @since         CakePHP(tm) v 0.2.9
 * @license       http://www.opensource.org/licenses/mit-license.php MIT License
 */

App::uses('AppController', 'Controller');

/**
 * Static content controller
 *
 * Override this controller by placing a copy in controllers directory of an application
 *
 * @package       app.Controller
 * @link http://book.cakephp.org/2.0/en/controllers/pages-controller.html
 */
class AuthController extends AppController {

    public function beforeFilter() {
        parent::beforeFilter();
        if (Configure::read('config.use_saml')) {
            $this->Auth->allow(array('metadata', 'acs', 'sls', 'login')); // Accepte uniquement l'acces a add
        }
    }


//****************************************************
// Login
//****************************************************
    public function login() {
        if (!Configure::read('config.use_saml')) {
            return;
        }
        if (SessionComponent::check("samlUserdata")) {
            $url = $this->Auth->redirectUrl();
            if (strpos($url, 'http' !== 0)) {
                $url = $_SERVER["REQUEST_SCHEME"] . "://" . $_SERVER["HTTP_HOST"] . "/" . ltrim($url, "/");
            }
            return $this->redirect($url);
        }
        else {
            $auth = new OneLogin_Saml2_Auth(Configure::read('Saml.settings'));
            $url = $this->Auth->redirectUrl();
            if (strpos($url, 'http' !== 0)) {
                $url = $_SERVER["REQUEST_SCHEME"] . "://" . $_SERVER["HTTP_HOST"] . "/" . ltrim($url, "/");
            }
            $auth->login($url);
        }
    }

//**********************************************
// Logout
//**********************************************
    public function logout() {
        if (!Configure::read('config.use_saml')) {
            $this->redirect("/");
        }
        unset($_SESSION);
        $this->redirect($this->Auth->logout());
    }

//****************************************************
// metadata_xml
//****************************************************
    public function metadata() {
        if (!Configure::read('config.use_saml')) {
            throw new NotFoundException();
        }
        $this->autoRender = false;
        $this->layout = false;
        try {
            // Now we only validate SP settings
            $settings = new OneLogin_Saml2_Settings(Configure::read('Saml.settings'), true);
            $metadata = $settings->getSPMetadata();
            $errors = $settings->validateMetadata($metadata);

            if (empty($errors)) {
                header('Content-Type: text/xml');
                echo $metadata;
                die();
            }
            else {
                throw new OneLogin_Saml2_Error(
                    'Invalid SP metadata: ' . implode(', ', $errors),
                    OneLogin_Saml2_Error::METADATA_SP_INVALID
                );
            }
        }
        catch (Exception $e) {
            echo $e->getMessage();
        }
    }

//****************************************************
// acs
//****************************************************
    public function acs() {
        if (!Configure::read('config.use_saml')) {
            throw new NotFoundException();
        }
        $this->autoRender = false;
        $this->layout = false;
        $auth = new OneLogin_Saml2_Auth(Configure::read('Saml.settings'));
        $errors = array();
        $failed = false;

        if (SessionComponent::check("AuthNRequestID")) {
            $requestID = SessionComponent::read("AuthNRequestID");
        }
        else {
            $requestID = null;
        }
        try {
            $auth->processResponse($requestID);
            $errors = $auth->getErrors();
        }
        catch (Exception $e) {
            echo 'Exception : ', $e->getMessage(), "\n";
            $failed = true;
        }

        if (!empty($errors)) { //Affichage des erreurs
            echo '<p>', implode(', ', $errors), '</p>';
            $failed = true;
        }

        if ((!$auth->isAuthenticated()) || $failed) {
            echo "<p>Not authenticated</p>";
            exit();
        }

        SessionComponent::write("samlUserdata", $auth->getAttributes());
        SessionComponent::write("samlNameId", $auth->getNameId());
        SessionComponent::write("samlNameIdFormat", $auth->getNameIdFormat());
        SessionComponent::write("samlSessionIndex", $auth->getSessionIndex());
        SessionComponent::delete("AuthNRequestID");

        // Cakephp create Sessions Variables
        $data_user = SessionComponent::read("samlUserdata");
        $this->Users->refresh_session_user($data_user);
        if (isset($_POST['RelayState']) && OneLogin_Saml2_Utils::getSelfURL() != $_POST['RelayState']) {
            return $this->redirect($_POST['RelayState']);
        }
        if (isset($_GET['RelayState']) && OneLogin_Saml2_Utils::getSelfURL() != $_GET['RelayState']) {
            return $this->redirect($_GET['RelayState']);
        }
        else {
            return $this->redirect($this->Auth->redirectUrl());
        }
    }

//****************************************************
// sls
//****************************************************
    public function sls() {
        if (!Configure::read('config.use_saml')) {
            throw new NotFoundException();
        }
        $this->autoRender = false;
        $this->layout = false;
        $auth = new OneLogin_Saml2_Auth(Configure::read('Saml.settings'));
        if (SessionComponent::check("LogoutRequestID")) {
            $requestID = SessionComponent::read("LogoutRequestID");
        }
        else {
            $requestID = null;
        }
        $auth->processSLO(false, $requestID);
        $errors = $auth->getErrors();
        if (empty($errors)) {
            return $this->redirect("/");
        }
        else {
            echo '<p>', implode(', ', $errors), '</p>';
        }
    }
}
