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
App::uses('AuthGroups', 'Lib/Aziugo');

/**
 * Static content controller
 *
 * Override this controller by placing a copy in controllers directory of an application
 *
 * @package       app.Controller
 * @link http://book.cakephp.org/2.0/en/controllers/pages-controller.html
 */
class ZephyCloudController extends AppController {
    public function beforeFilter() {
        parent::beforeFilter();
        $this->set("menu_active_element","ZephyCloud");
    }


    //**************************************
    // admin_users_index
    //**************************************
    public function admin_users_index() {
        $this->set("signin_url", Configure::read('zephycloud.signin_url'));
		$this->set_default_params(array('offset' => 0, 'limit' => 25, 'order' => 'user_id ASC'));
		$req_params = $this->get_params(array('offset','limit','order', 'rank'));
		$response = $this->ZephyCloud->request_list_or_fail("/admin/users/", $req_params);
		$this->Page->set_total_count('users', $response['total_count']);
		$this->set("users", $response["list"]);
    }


    //**************************************
    // admin_users_add
    //**************************************
    public function admin_users_add() {
        if(Configure::read('zephycloud.signin_url') != null) {
        	throw new BadRequestException("Direct user creation is disabled in this admin tool. Please use ".Configure::read('zephycloud.signin_url'));
        }
        if(!$this->request->is('post')) {
			throw new ForbiddenException("request should be POST");
		}
		$data_request = [];
		if (empty($this->request->data["login"])) {
			throw new BadRequestException("login is empty!");
		}
		$data_request["login"] = $this->request->data["login"];
		if (empty($this->request->data["email"])) {
			throw new BadRequestException("email is empty!");
		}
		$data_request["email"] = $this->request->data["email"];
		if (empty($this->request->data["pwd"])) {
			throw new BadRequestException("pwd is empty!");
		}
		$data_request["pwd"] = $this->request->data["pwd"];
		if (empty($this->request->data["rank"])) {
			throw new BadRequestException("rank is empty!");
		}
		$data_request["rank"] = $this->request->data["rank"];
		if (!empty($this->request->data["nbr_coins"])) {
			$data_request["nbr_coins"] = $this->request->data["nbr_coins"];
		}
		if (!empty($this->request->data["reason"])) {
			$data_request["reason"] = $this->request->data["reason"];
		}

		$this->ZephyCloud->request_or_fail("/admin/user/new/", $data_request);
		$this->Flash->success("User successfully created");
		return $this->redirect(array('plugin' => null, 'controller' => 'zephy_cloud', 'action' => 'admin_users_index'));
    }


    //**************************************
    // admin_users_restore
    //**************************************
    public function admin_users_restore($user_id) {
        if (empty($user_id)) {
            throw new NotFoundException("user_id is empty!");
        }
        $this->ZephyCloud->request_or_fail("/admin/user/restore/", ['user_id' => $user_id]);
		$this->Flash->success("User successfully restored");
		return $this->redirect(array('plugin' => null, 'controller' => 'zephy_cloud', 'action' => 'admin_users_show', 'user_id' => $user_id));
    }


    //**************************************
    // admin_users_delete
    //**************************************
    public function admin_users_delete($user_id) {
        if (empty($user_id)) {
            throw new NotFoundException("user_id is empty!");
        }
        $this->ZephyCloud->request_or_fail("/admin/user/remove/", ['user_id' => $user_id]);
		$this->Flash->success("User successfully deleted");
		return $this->redirect(array('plugin' => null, 'controller' => 'zephy_cloud', 'action' => 'admin_users_index'));
    }


    //**************************************
    // admin_users_add_credit
    //**************************************

    public function admin_users_add_credit($user_id) {
        if (empty($user_id)) {
            throw new NotFoundException("user_id is empty!");
        }
        if (!$this->request->is('post')) {
			return $this->render("admin_users_add_credit");
		}
		$data_request = [];
		$data_request["user_id"] = $user_id;
		if (empty($this->request->data["nbr_coins"])) {
			throw new BadRequestException("nbr_coins is empty!");
		}
		$data_request["nbr_coins"] = $this->request->data["nbr_coins"];
		if (empty($this->request->data["reason"])) {
			throw new BadRequestException("reason is empty!");
		}
		$data_request["reason"] = $this->request->data["reason"];
		$this->ZephyCloud->request_or_fail("/admin/user/credit/add/", $data_request);
		if($data_request["nbr_coins"] > 0) {
			$this->Flash->success("Credits successfully added to user account");
		}
		else {
			$this->Flash->success("Credits successfully removed from user account");
		}
		return $this->redirect(array('plugin' => null, 'controller' => 'zephy_cloud', 'action' => 'admin_users_index'));
    }


    //**************************************
    // admin_users_reset_password
    //**************************************
    public function admin_users_reset_password($user_email) {
        if (empty($user_email)) {
            throw new NotFoundException("user_email is empty!");
        }
        $new_password = $this->ZephyCloud->request_or_fail("/admin/user/reset_pwd/", ["email" => $user_email]);
		$this->set("newpassword", $new_password);
    }


    //**************************************
    // admin_users_change_rank
    //**************************************
    public function admin_users_change_rank() {
        if (!$this->request->is('post')) {
            throw new BadRequestException("Bad method");
        }

        if (empty($this->request->data["user_id"])) {
            throw new BadRequestException("Missing 'user_id' parameter");
        }
		$data_request["user_id"] = $this->request->data["user_id"];

        if (empty($this->request->data["rank"])) {
            throw new BadRequestException("Missing 'rank' parameter");
        }
		$data_request["rank"] = $this->request->data["rank"];
        $this->ZephyCloud->request_or_fail("/admin/user/change_rank/", $data_request);
		$this->Flash->success("User rank successfully changed to ".$this->request->data["rank"]);
		return $this->redirect(array('plugin' => null, 'controller' => 'zephy_cloud', 'action' => 'admin_users_index'));
    }


    //**************************************
    // admin_users_show
    //**************************************
    public function admin_users_show($user_id) {
        if (empty($user_id)) {
            throw new NotFoundException("user_id is empty!");
        }

		$request_args = ["user_id" => $user_id, "include_deleted" => true];
        $user_data = $this->ZephyCloud->request_or_fail("/admin/user/show/", $request_args);
		$this->set("user", $user_data);

		$request_args = ["user_id" => $user_id];
        if($this->time_machine_time) {
            $request_args["date"] = $this->time_machine_time;
        }
		$projects = array();
        try {
			$projects = $this->ZephyCloud->request_or_fail("/admin/projects/list/", $request_args);
		}
        catch(Exception $e) {
			$this->log_exception($e);
			$this->Flash->error("Unable to list projects: ".$e->getMessage());
		}
		$this->set("projects", $projects);
    }


    //**************************************
    // admin_projects
    //**************************************
    public function admin_projects() {
		$this->set_default_params(array('offset' => 0, 'limit' => 25));
		$req_params = $this->get_params(array('offset','limit', 'order', 'status', 'storage', 'user_id'));
		if($this->time_machine_time) {
			$req_params["date"] = $this->time_machine_time;
		}
		if(isset($req_params['user_id'])) {
			$this->set("user", $this->ZephyCloud->request_or_fail("/admin/user/show/",
				array('user_id' => $req_params['user_id'], 'include_deleted' => true)));
		}
		$response = $this->ZephyCloud->request_list_or_fail("/admin/projects/list/", $req_params);
		$this->Page->set_total_count('projects', $response['total_count']);
		$this->set("projects", $response["list"]);
    }


    //**************************************
    // admin_projects_view
    //**************************************
    public function admin_projects_view($user_id, $project_uid) {
        if (empty($project_uid)) {
            throw new NotFoundException("project_uid is empty!");
        }
        if (empty($user_id)) {
            throw new NotFoundException("user_id is empty!");
        }
        $project = $this->ZephyCloud->request_or_fail("/admin/projects/show/", ["project_uid" => $project_uid, "user_id" => $user_id, 'include_deleted' => true]);
		$this->set("project", $project);
    }


    //**************************************
    // admin_projects_delete
    //**************************************
    public function admin_projects_delete($user_id, $project_uid) {
        if (empty($project_uid)) {
            throw new NotFoundException("project_uid is empty!");
        }
        if (empty($user_id)) {
            throw new NotFoundException("user_id is empty!");
        }

		$this->ZephyCloud->request_or_fail("/admin/projects/remove/", ["project_uid" => $project_uid, "user_id" => $user_id]);
		$this->Flash->success("Project successfully deleted");
		return $this->redirect(array('plugin' => null, 'controller' => 'zephy_cloud', 'action' => 'admin_projects'));
    }


    //**************************************
    // admin_projects_file_url
    //**************************************
    public function admin_projects_file_url($user_id, $project_uid, $file_id) {
    	$this->set_page_as_api();
    	if (empty($project_uid)) {
            throw new NotFoundException("project_uid is empty!");
        }
        if (empty($user_id)) {
            throw new NotFoundException("user_id is empty!");
        }
    	if (empty($file_id)) {
            throw new NotFoundException("file_id is empty!");
        }
    	$request_params = ["project_uid" => $project_uid, "user_id" => $user_id, "file_id" => $file_id];
        $reponse = $this->ZephyCloud->request_or_fail("/admin/projects/file_url/", $request_params);
        $this->set_api_result($reponse);
    }


    //**************************************
    // admin_projects_set_status
    //**************************************
    public function admin_projects_set_status($user_id, $project_uid, $status) {
    	$this->set_page_as_api();
    	if (empty($project_uid)) {
            throw new NotFoundException("project_uid is empty!");
        }
        if (empty($user_id)) {
            throw new NotFoundException("user_id is empty!");
        }
    	if (empty($status)) {
            throw new NotFoundException("status is empty!");
        }
    	$request_params = ["project_uid" => $project_uid, "user_id" => $user_id, "status" => $status];
        $reponse = $this->ZephyCloud->request_or_fail("/admin/projects/status/", $request_params);
        $this->Flash->success("Project status successfully changed to ".$status);
        $this->set_api_result($reponse);
    }


    //**************************************
    // admin_providers
    //**************************************
    public function admin_providers() {
        $providers = $this->ZephyCloud->request_or_fail("/admin/providers/list/", []);
		$this->set("providers", $providers);
    }


    //**************************************
    // admin_providers_machines
    //**************************************
    public function admin_providers_machines($providers_name) {
        if (empty($providers_name)) {
            throw new NotFoundException("providers_name is empty!");
        }
        $this->set("providers_name", $providers_name);
        $request_args = ["provider_name" => $providers_name];
        if($this->time_machine_time) {
            $request_args["date"] = $this->time_machine_time;
        }
        $machines = $this->ZephyCloud->request_or_fail("/admin/machines/list/", $request_args);
		$this->set("providers_machines", $machines);
    }


    //**************************************
    // admin_providers_machines_delete
    //**************************************
    public function admin_providers_machines_delete($providers_name, $machine_name) {
        if (empty($providers_name)) {
            throw new NotFoundException("providers_name is empty!");
        }
        if (empty($machine_name)) {
            throw new NotFoundException("machine_name is empty!");
        }

		$data_request = ["provider_name" => $providers_name, "machine_name" => $machine_name];
        $this->ZephyCloud->request_or_fail("/admin/machines/remove/", $data_request);
		$this->Flash->success("Machine successfully deleted");
		return $this->redirect(array('plugin' => null, 'controller' => 'zephy_cloud', 'action' => 'admin_providers_machines', 'providers_name' => $providers_name));
    }


    //**************************************
    // admin_providers_machines_create
    //**************************************
    public function admin_providers_machines_create($providers_name) {
        if (empty($providers_name)) {
            throw new NotFoundException("providers_name is empty!");
        }

		$aws_region = null;
		$providers_list = $this->ZephyCloud->request_or_fail("/admin/providers/list/", []);
		$provider_info = null;
		foreach($providers_list as $it) {
			if ($it["name"] === $providers_name) {
				$provider_info = $it;
				break;
			}
		}
		if($provider_info == null) {
			throw new BadRequestException("Unknown provider ".$providers_name);
		}
		$aws_region = isset($provider_info["provider_specific"]["region"]) ? $provider_info["provider_specific"]["region"] : null;

		$this->set("providers_name", $providers_name);
		$this->set("providers", $providers_list);
		$this->set("aws_region", $aws_region);
		$existing_machines = $this->ZephyCloud->request_or_fail("/admin/machines/list/", ["provider_name" => $providers_name]);
		$this->set("existing_machines", array_map(function($a) { return $a['name'];}, $existing_machines));
		$this->set("pricing", $this->ZephyCloud->request_or_fail("/admin/reports/pricing_constants/"));
		$this->set("provider_pricing_api", Configure::read('zephycloud.provider_pricing_api'));
    }


	//**************************************
	// admin_providers_machines_add
	//**************************************
	public function admin_providers_machines_add($providers_name) {
		if (empty($providers_name)) {
			throw new NotFoundException("providers_name is empty!");
		}
		if (!$this->request->is('post')) {
			throw new BadRequestException("Bad method");
		}
		$data_request = $this->get_params(["machine_name", "cores", "ram", "availability",
			"price_sec_granularity", "price_min_sec_granularity", "cost_per_hour", "cost_currency",
			"cost_sec_granularity", "cost_min_sec_granularity", "auto_update", "auto_update"]);
		$data_request["provider_name"] = $providers_name;
		$data_request["prices"] = [
			"root" => (float)$this->request->data["prices_root"],
			"gold" => (float)$this->request->data["prices_gold"],
			"silver" => (float)$this->request->data["prices_silver"],
			"bronze" => (float)$this->request->data["prices_bronze"]
		];
		$this->ZephyCloud->request_or_fail("/admin/machines/create/", $data_request);
		$this->Flash->success("Machine ".$data_request["machine_name"]." has been successfully created");
		return $this->redirect(array('plugin' => null, 'controller' => 'zephy_cloud', 'action' => 'admin_providers_machines', 'providers_name' => $providers_name));
	}


    //**************************************
    // admin_providers_machines_show
    //**************************************
    public function admin_providers_machines_show($providers_name, $machine_name) {
        if (empty($providers_name)) {
            throw new NotFoundException("project_uid is empty!");
        }
        if (empty($machine_name)) {
            throw new NotFoundException("machine_name is empty!");
        }

		$this->set("provider", $providers_name);
        $request_args = ["provider_name" => $providers_name, "machine_name" => $machine_name];
		$this->set("machine", $this->ZephyCloud->request_or_fail("/admin/machines/show/", $request_args));
		$toolchains = array();
		try {
			$toolchains = $this->ZephyCloud->request_or_fail("/admin/machines/list_toolchains/", $request_args);
		}
		catch(Exception $e) {
			$this->log_exception($e);
			$this->Flash->error("Unable to list toolchains: ".$e->getMessage());
		}
		$this->set("toolchains", $toolchains);
    }


	//**************************************
	// admin_providers_machines_edit
	//**************************************
	public function admin_providers_machines_edit($providers_name, $machine_name) {
		if (empty($providers_name)) {
			throw new NotFoundException("project_uid is empty!");
		}
		if (empty($machine_name)) {
			throw new NotFoundException("machine_name is empty!");
		}
		$this->set("provider", $providers_name);
		$request_data = ["provider_name" => $providers_name, "machine_name" => $machine_name];
		$machine_info = $this->ZephyCloud->request_or_fail("/admin/machines/show/", $request_data);
		$this->set("machine", $machine_info);
		$this->set("pricing", $this->ZephyCloud->request_or_fail("/admin/reports/pricing_constants/"));

		//This is to autofill input fields
		$field_list = ["machine_name", "cores", "ram", "availability",
			"price_sec_granularity", "price_min_sec_granularity", "cost_per_hour", "cost_currency",
			"cost_sec_granularity", "cost_min_sec_granularity", "auto_update", "auto_update"];
		foreach($field_list as $field) {
			$this->request->data[$field] = $machine_info[$field];
		}
		$ranks = ['root', 'gold', 'silver', 'bronze'];
		foreach($ranks as $rank) {
			$this->request->data['prices_'.$rank] = 	$machine_info['prices'][$rank];
		}
	}


    //**************************************
    // admin_providers_machines_update
    //**************************************
    public function admin_providers_machines_update($providers_name, $machine_name) {
        if (empty($providers_name)) {
            throw new NotFoundException("project_uid is empty!");
        }
        if (empty($machine_name)) {
            throw new NotFoundException("machine_name is empty!");
        }
		if (!$this->request->is('post')) {
			throw new ForbiddenException("POST method is required");
		}
		$data_request = $this->get_params(["cores", "ram", "availability",
			"price_sec_granularity", "price_min_sec_granularity", "cost_per_hour", "cost_currency",
			"cost_sec_granularity", "cost_min_sec_granularity", "auto_update", "auto_update"]);
		$data_request["provider_name"] = $providers_name;
		$data_request["machine_name"] = $machine_name;
		$data_request["prices"] = [
			"root" => (float)$this->request->data["prices_root"],
			"gold" => (float)$this->request->data["prices_gold"],
			"silver" => (float)$this->request->data["prices_silver"],
			"bronze" => (float)$this->request->data["prices_bronze"]
		];
		$this->ZephyCloud->request_or_fail("/admin/machines/update/", $data_request);
		$this->Flash->success("Machine ".$data_request["machine_name"]." has been successfully updated");
		return $this->redirect(array('plugin' => null, 'controller' => 'zephy_cloud', 'action' => 'admin_providers_machines', 'providers_name' => $providers_name));
    }


    //**************************************
    // admin_toolchains
    //**************************************
    public function admin_toolchains() {
        $request_args = [];
        if($this->time_machine_time) {
            $request_args["date"] = $this->time_machine_time;
        }
		$toolchains = $this->ZephyCloud->request_or_fail("/admin/toolchains/list/", $request_args);
		$this->set("toolchains", $toolchains);
    }


    //**************************************
    // admin_toolchains_show
    //**************************************
    public function admin_toolchains_show($toolchain_name) {
    	$request_args = ["toolchain_name" => $toolchain_name];
        $toolchain = $this->ZephyCloud->request_or_fail("/admin/toolchains/show/", $request_args);
		$this->set("toolchain", $toolchain);

		$machines = [];
		try {
			$machines = $this->ZephyCloud->request_or_fail("/admin/toolchains/list_machines/", $request_args);
		}
		catch(Exception $e) {
			$this->log_exception($e);
			$this->Flash->error("Unable to list machines: ".$e->getMessage());
		}
		$this->set("machines", $machines);
    }


    //**************************************
    // admin_toolchains_edit
    //**************************************
    public function admin_toolchains_edit($toolchain_name) {
        if (empty($toolchain_name)) {
            throw new NotFoundException("toolchain_name is empty!");
        }

        $toolchain = $this->ZephyCloud->request_or_fail("/admin/toolchains/show/", ["toolchain_name" => $toolchain_name]);
		$this->set("toolchains", $toolchain);
		$this->set("all_machines", $this->ZephyCloud->request_or_fail("/admin/providers/list_all_machines/"));
		$toolchain_machines = $this->ZephyCloud->request_or_fail("/admin/toolchains/list_machines/", ["toolchain_name" => $toolchain_name]);
		$this->set("toolchain_machines", $toolchain_machines);

		// To setup the form
		$this->request->data['fixed_price'] = $toolchain['fixed_price'];
		$this->request->data['machine_limit'] = $toolchain['machine_limit'];
		$this->request->data["machines"] = $toolchain_machines;
    }


	//**************************************
	// admin_toolchains_update
	//**************************************
	public function admin_toolchains_update($toolchain_name) {
		if (empty($toolchain_name)) {
			throw new NotFoundException("toolchain_name is empty!");
		}
		if (!$this->request->is('post')) {
			throw new ForbiddenException("POST method is required");
		}

		$data_request = $this->request->data;
		$data_request["toolchain_name"] = $toolchain_name;
		$this->ZephyCloud->request_or_fail("/admin/toolchains/update/", $data_request);
		$this->Flash->success("Toolchain ".$toolchain_name." has been successfully updated");
		return $this->redirect(array('plugin' => null, 'controller' => 'zephy_cloud', 'action' => 'admin_toolchains_show', "toolchain_name" => $toolchain_name));
	}


    //**************************************
    // admin_transactions
    //**************************************
    public function admin_transactions() {
		$this->set_default_params(array('offset' => 0, 'limit' => 25, 'order' => 'id DESC'));
		$req_params = $this->get_params(array('offset','limit','order', "user_id", "project_uid", "description", 'job_id'));
		if(isset($req_params['user_id'])) {
			$this->set("user", $this->ZephyCloud->request_or_fail("/admin/user/show/",
				array('user_id' => $req_params['user_id'], 'include_deleted' => true)));
		}
		$response = $this->ZephyCloud->request_list_or_fail("/admin/transactions/list/", $req_params);
		$this->Page->set_total_count('transactions', $response['total_count']);
		$this->set("transactions", $response["list"]);
    }


    //**************************************
    // admin_transactions_cancel
    //**************************************
    public function admin_transactions_cancel($transaction_ids) {
        if (!$this->request->is('post')) {
			throw new ForbiddenException("Post request is required");
		}
		if (empty($this->request->data["reason"])) {
			throw new BadRequestException("reason is empty!");
		}
		if (empty($transaction_ids)) {
			throw new BadRequestException("transaction_ids is empty!");
		}

		$data_request = [
			"transaction_ids" => array($transaction_ids),
			"reason" => $this->request->data["reason"]
		];
		$this->ZephyCloud->request_or_fail("/admin/transactions/cancel/", $data_request);
		$this->Flash->success("Transaction has been successfully canceled");
		return $this->redirect(array('plugin' => null, 'controller' => 'zephy_cloud', 'action' => 'admin_transactions'));
    }


    //**************************************
    // admin_computations
    //**************************************
    public function admin_computations() {
    	$this->set_default_params(array('offset' => 0, 'limit' => 25, 'order' => 'job_id DESC'));
		$req_params = $this->get_params(array('offset','limit','order','user_id','project_uid','status'));
		if(isset($req_params['user_id'])) {
			$this->set("user", $this->ZephyCloud->request_or_fail("/admin/user/show/",
				array('user_id' => $req_params['user_id'], 'include_deleted' => true)));
		}
		$response = $this->ZephyCloud->request_list_or_fail("/admin/computations/list/", $req_params);
		$this->Page->set_total_count('computations', $response['total_count']);
		$this->set("computations", $response["list"]);
    }


    //**************************************
    // admin_computations_show
    //**************************************
    public function admin_computations_show($job_id) {
        $job_data = $this->ZephyCloud->request_or_fail("/admin/computations/show/", ["job_id" => $job_id]);
		$this->set("computation", $job_data);
    }


    //**************************************
    // admin_computations_show_log
    //**************************************
    public function admin_computations_show_log($job_id) {
        $reponse = $this->ZephyCloud->request_or_fail("/admin/computations/show_logs/", ["job_id" => $job_id]);
		$this->set("logs", $reponse);
    }


    //**************************************
    // admin_computations_kill
    //**************************************
    public function admin_computations_kill($job_id) {
		$this->ZephyCloud->request_or_fail("/admin/computations/kill/", ["job_id" => $job_id]);
		$this->Flash->success("Computation ".$job_id." has been successfully killed");
		return $this->redirect_referer_or(array('controller' => 'zephy_cloud', 'action' => 'admin_computations'));
    }


    //**************************************
    // admin_meshes_set_status
    //**************************************
    public function admin_meshes_set_status($user_id, $project_uid, $mesh_id, $status) {
    	$this->set_page_as_api();
    	if (empty($project_uid)) {
            throw new NotFoundException("project_uid is empty!");
        }
        if (empty($user_id)) {
            throw new NotFoundException("user_id is empty!");
        }
        if (empty($mesh_id)) {
            throw new NotFoundException("mesh_id is empty!");
        }
    	if (empty($status)) {
            throw new NotFoundException("status is empty!");
        }
    	$request_params = ["project_uid" => $project_uid, "user_id" => $user_id, "mesh_id" => $mesh_id, "status" => $status];
        $reponse = $this->ZephyCloud->request_or_fail("/admin/meshes/status/", $request_params);
        $this->Flash->success("Mesh status successfully changed to ".$status);
        $this->set_api_result($reponse);
    }


	//**************************************
    // admin_calc_set_status
    //**************************************
    public function admin_calc_set_status($user_id, $project_uid, $calc_id, $status) {
    	$this->set_page_as_api();
    	if (empty($project_uid)) {
            throw new NotFoundException("project_uid is empty!");
        }
        if (empty($user_id)) {
            throw new NotFoundException("user_id is empty!");
        }
        if (empty($calc_id)) {
            throw new NotFoundException("calc_id is empty!");
        }
    	if (empty($status)) {
            throw new NotFoundException("status is empty!");
        }
    	$request_params = ["project_uid" => $project_uid, "user_id" => $user_id, "calc_id" => $calc_id, "status" => $status];
        $reponse = $this->ZephyCloud->request_or_fail("/admin/calculations/status/", $request_params);
        $this->Flash->success("Calculaton status successfully changed to ".$status);
        $this->set_api_result($reponse);
    }


	//**************************************
    // admin_search
    //**************************************
    public function admin_search() {
    	$this->set_page_as_api();
    	if (!$this->request->is('get')) {
			throw new BadRequestException("Get method required");
    	}
    	if (empty($this->request->query['term'])) {
    		throw new BadRequestException("Missing term parameter");
        }

		$response = $this->ZephyCloud->request_or_fail("/admin/search/", ["term" => $this->request->query["term"]]);
		$result = array();
		foreach($response['users'] as $user) {
			$url = Router::url(['controller' => 'zephy_cloud', 'action' => 'admin_users_show', 'user_id' => $user['id']], true);
			$label = $user["email"].(empty($user["login"]) ? "" : " (".$user["login"].")");
			array_push($result, array("label" => $label, "category" => "Users", "url" => $url));
		}
		foreach($response['projects'] as $project) {
			$url = Router::url(['controller' => 'zephy_cloud', 'action' => 'admin_projects_view',
								'user_id' => $project['user_id'], 'project_uid' => $project["uid"]], true);
			array_push($result, array("label" => $project["uid"], "category" => "Projects", "url" => $url));
		}
        $this->set_api_result($result);
    }

    //**************************************
    // admin_currencies
    //**************************************
    public function admin_currencies() {
    	$currencies = $this->ZephyCloud->request_or_fail("/admin/currencies/", []);
		$this->set("currencies", $this->ZephyCloud->request_or_fail("/admin/currencies/", []));
    }
}
