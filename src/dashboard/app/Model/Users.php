<?php

class Users extends AppModel {
    public $name = 'Users';
    public $useTable = false;

	//**********************************************
	// beforeSave (Password auto encrypt)
	//**********************************************
    public function beforeSave($options = array()) {
    }

    public function password_hash($password) {
        $passwordHasher = new SimplePasswordHasher();
        return $passwordHasher->hash($password);
    }

    public function password_generator($sizebytes = 6) {
        return bin2hex(openssl_random_pseudo_bytes($sizebytes));
    }

	//***********************************************
	// refresh_session
	//***********************************************
    // Refresh the session
    public function refresh_session_user($data_user) {
        //  get user info
        $email = $data_user['mail'][0];
        SessionComponent::write("Auth.User.id", $data_user["user_id"][0]);
        SessionComponent::write("Auth.User.firstname", $data_user["firstname"][0]);
        SessionComponent::write("Auth.User.lastname", $data_user["lastname"][0]);
        SessionComponent::write("Auth.User.alias", $data_user["username"][0]);
        SessionComponent::write("Auth.User.email", $email);

        $allowed_users = Configure::read('zephycloud.allowed_users');
        $login = explode('@', $email, 2)[0];
        $groups = array();
        if (in_array($login, $allowed_users)) {
            array_push($groups, "manager");
        }
        else {
            array_push($groups, "guest");
        }
        SessionComponent::write("Auth.User.groups_list", $groups);
    }
}
