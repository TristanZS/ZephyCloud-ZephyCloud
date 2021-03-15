<?php
$config['Saml']['spBaseUrl'] = $_SERVER["REQUEST_SCHEME"] . "://" . $_SERVER["HTTP_HOST"] . '/dashboard/';
$config['Saml']['serverAuth'] = "https://auth.aziugo.com";
$config['Saml']["settings"] = array(
    // If 'strict' is True, then the PHP Toolkit will reject unsigned
    // or unencrypted messages if it expects them signed or encrypted
    // Also will reject the messages if not strictly follow the SAML
    // standard: Destination, NameId, Conditions ... are validated too.
    'strict' => false,

    // Enable debug mode (to print errors)
    'debug' => true,

    // Set a BaseURL to be used instead of try to guess
    // the BaseURL of the view that process the SAML Message.
    // Ex. http://sp.example.com/
    //     http://example.com/sp/
    'baseurl' => $config['Saml']['serverAuth'],

    // Service Provider Data that we are deploying
    'sp' => array(
        // Identifier of the SP entity  (must be a URI)
        'entityId' => $config['Saml']['spBaseUrl'] . 'saml/metadata.xml', /// local
        // Specifies info about where and how the <AuthnResponse> message MUST be
        // returned to the requester, in this case our SP.
        'assertionConsumerService' => array(
            // URL Location where the <Response> from the IdP will be returned
            'url' => $config['Saml']['spBaseUrl'] . 'saml/acs.html', /// local
            // SAML protocol binding to be used when returning the <Response>
            // message.  Onelogin Toolkit supports for this endpoint the
            // HTTP-Redirect binding only
            //'binding' => 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST',
            //'binding' => 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect',
        ),
        // If you need to specify requested attributes, set a
        // attributeConsumingService. nameFormat, attributeValue and
        // friendlyName can be omitted. Otherwise remove this section.
        /* "attributeConsumingService"=> array(
                 "ServiceName" => "Zephycloud Dashboard",
                 "serviceDescription" => "Zephycloud Dashboard",
                 "requestedAttributes" => array(
                     array(
                         "name" => "groups",
                         "isRequired" => true,
                         "nameFormat" => "",
                         "friendlyName" => "groups",
                         "attributeValue" => "groups"
                     )
                 )
        ), */
        // Specifies info about where and how the <Logout Response> message MUST be
        // returned to the requester, in this case our SP.
        'singleLogoutService' => array(
            // URL Location where the <Response> from the IdP will be returned
            'url' => $config['Saml']['spBaseUrl'] . 'saml/sls.html', /// local
            // SAML protocol binding to be used when returning the <Response>
            // message.  Onelogin Toolkit supports for this endpoint the
            // HTTP-Redirect binding only
            //'binding' => 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect',
        ),
        // Specifies constraints on the name identifier to be used to
        // represent the requested subject.
        // Take a look on lib/Saml2/Constants.php to see the NameIdFormat supported
        'NameIDFormat' => 'urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified',

        // Usually x509cert and privateKey of the SP are provided by files placed at
        // the certs folder. But we can also provide them with the following parameters
        //'x509cert' => '',
        //'privateKey' => '',

        /*
         * Key rollover
         * If you plan to update the SP x509cert and privateKey
         * you can define here the new x509cert and it will be
         * published on the SP metadata so Identity Providers can
         * read them and get ready for rollover.
         */
        // 'x509certNew' => '',
    ),

    // Identity Provider Data that we want connect with our SP
    'idp' => array(
        // Identifier of the IdP entity  (must be a URI)
        'entityId' => $config['Saml']['serverAuth'] . '/_saml/metadata/dashboard',
        // SSO endpoint info of the IdP. (Authentication Request protocol)
        'singleSignOnService' => array(
            // URL Target of the IdP where the SP will send the Authentication Request Message
            'url' => $config['Saml']['serverAuth'] . '/saml2/idp/SSOService.php',
            // SAML protocol binding to be used when returning the <Response>
            // message.  Onelogin Toolkit supports for this endpoint the
            // HTTP-POST binding only
            //'binding' => 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect',
        ),
        // SLO endpoint info of the IdP.
        'singleLogoutService' => array(
            // URL Location of the IdP where the SP will send the SLO Request
            'url' => $config['Saml']['serverAuth'] . '/saml2/idp/SingleLogoutService.php',
            // SAML protocol binding to be used when returning the <Response>
            // message.  Onelogin Toolkit supports for this endpoint the
            // HTTP-Redirect binding only
            //'binding' => 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect',
        ),
        // Public x509 certificate of the IdP
        'x509cert' => 'MIIDyzCCArOgAwIBAgIJAIXSX6Y10gUpMA0GCSqGSIb3DQEBCwUAMHwxCzAJBgNVBAYTAkZSMQ8wDQYDVQQIDAZGcmFuY2UxEjAQBgNVBAcMCU1hcnNlaWxsZTEPMA0GA1UECgwGQXppdWdvMRMwEQYDVQQDDApheml1Z28uY29tMSIwIAYJKoZIhvcNAQkBFhNzeXNhZG1pbkBheml1Z28uY29tMB4XDTE3MTAxOTA5NDAxMloXDTI3MTAxOTA5NDAxMlowfDELMAkGA1UEBhMCRlIxDzANBgNVBAgMBkZyYW5jZTESMBAGA1UEBwwJTWFyc2VpbGxlMQ8wDQYDVQQKDAZBeml1Z28xEzARBgNVBAMMCmF6aXVnby5jb20xIjAgBgkqhkiG9w0BCQEWE3N5c2FkbWluQGF6aXVnby5jb20wggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQC4iaCJ2GFV5DnN4g+m26iFXVvlS+AZh3Cv08ypbH+lQfW43KxiTgZipwQZ1nOXCThltY4dL3B3Jh7zJouZAe/uoTQDAhydLTPu1cY/A5scyeLPGjfOqRrw4/28ofJhWFRSdWmVB6B5ICfU6yF/Wv5Km0TDsY2v0QuECRxXbgb0G6hBD3MqwDzx0Se7AaYsx4QGTcAF0LCa9wgy8fzU+QiUYnWmNWzi3GWR3cuQVWuZFafaO0puWRjDLZlfDxHI9aJiup8S3AoVoVveqVK+ZLSax+4S2vdEw6Wl/GP2mxAwFC3P2OumvYXiUnNLCKQmSwFaBLoKxQLmC+7AxKrbKi+7AgMBAAGjUDBOMB0GA1UdDgQWBBTl5YWejXb2dxc/MqsAM00tu9HJPTAfBgNVHSMEGDAWgBTl5YWejXb2dxc/MqsAM00tu9HJPTAMBgNVHRMEBTADAQH/MA0GCSqGSIb3DQEBCwUAA4IBAQAzkFLfMGQrs37Bf4HPziVvulbNSmpkGhAgaXvOuJGHhFWhpG/u4iRJ4R1Vvmvyh3/GQB7FdRHONJej/psiF9+9m2jP1Wy8cg20RHr6snOMOiTek0qG9uZkvZYf6zuPRUT3hPa8Gj7hfokr7712fFfSaIHtTqa7gccq9dVNL2G9bnSaK+37quggxAdjqJVAI4DGshbROMVBCYtzbYDA4kDv/hFf4s88ojkoG6c2WPmtqCTjHsStWwV1Ywi8LiKCMbWZ/LQlYOPgdusQOOWqZ2OsEYCYWmsZzdwNcwJyFJNQ7y0n2hD3igz9E0WLn6Au97SbldzERXi+Yx6t/eX+mtv9',
        /*
         *  Instead of use the whole x509cert you can use a fingerprint
         *  (openssl x509 -noout -fingerprint -in "idp.crt" to generate it,
         *   or add for example the -sha256 , -sha384 or -sha512 parameter)
         *
         *  If a fingerprint is provided, then the certFingerprintAlgorithm is required in order to
         *  let the toolkit know which Algorithm was used. Possible values: sha1, sha256, sha384 or sha512
         *  'sha1' is the default value.
         */
        // 'certFingerprint' => '',
        // 'certFingerprintAlgorithm' => 'sha1',

        /* In some scenarios the IdP uses different certificates for
         * signing/encryption, or is under key rollover phase and more
         * than one certificate is published on IdP metadata.
         * In order to handle that the toolkit offers that parameter.
         * (when used, 'x509cert' and 'certFingerprint' values are
         * ignored).
         */
        // 'x509certMulti' => array(
        //      'signing' => array(
        //          0 => '<cert1-string>',
        //      ),
        //      'encryption' => array(
        //          0 => '<cert2-string>',
        //      )
        // ),
    ),
);
