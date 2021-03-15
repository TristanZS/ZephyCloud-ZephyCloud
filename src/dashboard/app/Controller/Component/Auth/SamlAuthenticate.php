<?php
App::uses('BaseAuthenticate', 'Controller/Component/Auth');

class SamlAuthenticate extends BaseAuthenticate {
    public $settings;
    private $SamlAuth;

    //****************************************
    // Constructor
    //****************************************
    public function __construct(ComponentCollection $collection, array $settings, string $authSource = NULL) {
        $this->settings = array();
        if (!Configure::read('config.use_saml')) {
            return;
        }
        if (Configure::check('Saml.settings')) { // Check the config
            $this->settings = Configure::read('Saml.settings');
        }
        else {
            throw new Exception('Settings is missing from the configuration file.');
        }
        $this->SamlAuth = new OneLogin_Saml2_Auth($this->settings);
        parent::__construct($collection, $settings);
    }


    //****************************************
    // Authenticate
    //****************************************
    public function authenticate(CakeRequest $request, CakeResponse $response) {
        parent::authenticate($request, $response);
        if (!Configure::read('config.use_saml')) {
            return;
        }
        if (!SessionComponent::check("samlUserdata")) {
            SessionComponent::delete("Auth");
            unset($_SESSION);
            $this->SamlAuth->login(Configure::read('Saml.spBaseUrl'));
        }
    }


    //https://dashboard.aziugo.fr/saml/slo.html
    //****************************************
    // getUser
    //****************************************
    public function getUser(CakeRequest $request) {
        return $this->SamlAuth->getAttributes();
    }

    //****************************************
    // logout
    //****************************************
    // This function hooks into AuthComponent::logout and extends it to add a SAML logout in addition to the session logout
    public function logout($user) {
        if (!Configure::read('config.use_saml')) {
            return;
        }
        SessionComponent::delete("Auth");
        unset($_SESSION);

        $returnTo = null;
        $paramters = array();
        $nameId = null;
        $sessionIndex = null;
        $nameIdFormat = null;
        if (SessionComponent::check("samlNameId")) {
            $nameId = SessionComponent::read("samlNameId");
        }
        if (SessionComponent::check("samlSessionIndex")) {
            $sessionIndex = SessionComponent::read("samlSessionIndex");
        }
        if (SessionComponent::check("samlNameIdFormat")) {
            $nameIdFormat = SessionComponent::read("samlNameIdFormat");
        }
        $this->SamlAuth->logout($returnTo, $paramters, $nameId, $sessionIndex, false, $nameIdFormat);
        parent::logout($user);
    }

}
