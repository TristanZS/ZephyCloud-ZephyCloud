<?php
/**
 * Routes configuration
 *
 * In this file, you set up routes to your controllers and their actions.
 * Routes are very important mechanism that allows you to freely connect
 * different URLs to chosen controllers and their actions (functions).
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
 * @package       app.Config
 * @since         CakePHP(tm) v 0.2.9
 * @license       https://opensource.org/licenses/mit-license.php MIT License
 */

/**
 * Here, we are connecting '/' (base path) to controller called 'Pages',
 * its action called 'display', and we pass a param to select the view file
 * to use (in this case, /app/View/Pages/home.ctp)...
 */


//****************************************
// Basic
//****************************************
Router::connect('/', array('controller' => 'home', 'action' => 'index'));

//****************************************
// Users
//****************************************
// ONLINE
Router::connect('/login.html', array('controller' => 'auth', 'action' => 'login'));
Router::connect('/logout.html', array('controller' => 'auth', 'action' => 'logout'));


Router::connect('/saml/metadata.xml', array('controller' => 'auth', 'action' => 'metadata'));
Router::connect('/saml/acs.html', array('controller' => 'auth', 'action' => 'acs'));
Router::connect('/saml/sls.html', array('controller' => 'auth', 'action' => 'sls'));


//****************************************
// Admin
//****************************************
Router::connect('/zephy-cloud/admin/users.html', array('controller' => 'zephy_cloud', 'action' => 'admin_users_index'));
Router::connect('/zephy-cloud/admin/users/add.html', array('controller' => 'zephy_cloud', 'action' => 'admin_users_add'));

Router::connect('/zephy-cloud/admin/users/:user_id/delete.html',
    array('controller' => 'zephy_cloud', 'action' => 'admin_users_delete'),
    array(
        'pass' => array('user_id')
    )
);

Router::connect('/zephy-cloud/admin/users/:user_id/add-credit.html',
    array('controller' => 'zephy_cloud', 'action' => 'admin_users_add_credit'),
    array(
        'pass' => array('user_id')
    )
);

Router::connect('/zephy-cloud/admin/users/:user_id/show.html',
    array('controller' => 'zephy_cloud', 'action' => 'admin_users_show'),
    array(
        'pass' => array('user_id')
    )
);

Router::connect('/zephy-cloud/admin/users/:user_email/reset-password.html',
    array('controller' => 'zephy_cloud', 'action' => 'admin_users_reset_password'),
    array(
        'pass' => array('user_email')
    )
);

Router::connect('/zephy-cloud/admin/projects.html', array('controller' => 'zephy_cloud', 'action' => 'admin_projects'));

Router::connect('/zephy-cloud/admin/users/:user_id/projects/:project_uid/view.html',
    array('controller' => 'zephy_cloud', 'action' => 'admin_projects_view'),
    array(
        'pass' => array("user_id", 'project_uid')
    )
);

Router::connect('/zephy-cloud/admin/users/:user_id/projects/:project_uid/delete.html',
    array('controller' => 'zephy_cloud', 'action' => 'admin_projects_delete'),
    array(
        'pass' => array("user_id", 'project_uid')
    )
);

Router::connect('/zephy-cloud/admin/users/:user_id/projects/:project_uid/file/:file_id.json',
    array('controller' => 'zephy_cloud', 'action' => 'admin_projects_file_url'),
    array(
        'pass' => array("user_id", 'project_uid', "file_id")
    )
);

Router::connect('/zephy-cloud/admin/users/:user_id/projects/:project_uid/status/:status.json',
    array('controller' => 'zephy_cloud', 'action' => 'admin_projects_set_status'),
    array(
        'pass' => array("user_id", 'project_uid', "status")
    )
);


Router::connect('/zephy-cloud/admin/providers.html', array('controller' => 'zephy_cloud', 'action' => 'admin_providers'));


Router::connect('/zephy-cloud/admin/providers/:providers_name/machines.html',
    array('controller' => 'zephy_cloud', 'action' => 'admin_providers_machines'),
    array(
        'pass' => array('providers_name')
    )
);

Router::connect('/zephy-cloud/admin/providers/:providers_name/machines/:machine_name/show.html',
    array('controller' => 'zephy_cloud', 'action' => 'admin_providers_machines_show'),
    array(
        'pass' => array('providers_name', "machine_name")
    )
);

Router::connect('/zephy-cloud/admin/providers/:providers_name/machines/:machine_name/delete.html',
    array('controller' => 'zephy_cloud', 'action' => 'admin_providers_machines_delete'),
    array(
        'pass' => array('providers_name', "machine_name")
    )
);

Router::connect('/zephy-cloud/admin/providers/:providers_name/machines/:machine_name/edit.html',
	array('controller' => 'zephy_cloud', 'action' => 'admin_providers_machines_edit'),
	array(
		'pass' => array('providers_name', "machine_name")
	)
);

Router::connect('/zephy-cloud/admin/providers/:providers_name/machines/:machine_name/update.html',
    array('controller' => 'zephy_cloud', 'action' => 'admin_providers_machines_update'),
    array(
        'pass' => array('providers_name', "machine_name")
    )
);


Router::connect('/zephy-cloud/admin/providers/:providers_name/machines/create.html',
    array('controller' => 'zephy_cloud', 'action' => 'admin_providers_machines_create'),
    array(
        'pass' => array('providers_name')
    )
);


Router::connect('/zephy-cloud/admin/providers/:providers_name/machines/add.html',
	array('controller' => 'zephy_cloud', 'action' => 'admin_providers_machines_add'),
	array(
		'pass' => array('providers_name')
	)
);



Router::connect('/zephy-cloud/admin/toolchains.html', array('controller' => 'zephy_cloud', 'action' => 'admin_toolchains'));


Router::connect('/zephy-cloud/admin/toolchains/:toolchain_name/edit.html',
    array('controller' => 'zephy_cloud', 'action' => 'admin_toolchains_edit'),
    array(
        'pass' => array('toolchain_name')
    )
);

Router::connect('/zephy-cloud/admin/toolchains/:toolchain_name/update.html',
	array('controller' => 'zephy_cloud', 'action' => 'admin_toolchains_update'),
	array(
		'pass' => array('toolchain_name')
	)
);

Router::connect('/zephy-cloud/admin/toolchains/:toolchain_name/show.html',
    array('controller' => 'zephy_cloud', 'action' => 'admin_toolchains_show'),
    array(
        'pass' => array('toolchain_name')
    )
);



Router::connect('/zephy-cloud/admin/computations.html', array('controller' => 'zephy_cloud', 'action' => 'admin_computations'));

Router::connect('/zephy-cloud/admin/computations/:job_id/show.html',
    array('controller' => 'zephy_cloud', 'action' => 'admin_computations_show'),
    array(
        'pass' => array('job_id')
    )
);

Router::connect('/zephy-cloud/admin/computations/:job_id/show/log.html',
    array('controller' => 'zephy_cloud', 'action' => 'admin_computations_show_log'),
    array(
        'pass' => array('job_id')
    )
);

Router::connect('/zephy-cloud/admin/computations/:job_id/kill.html',
    array('controller' => 'zephy_cloud', 'action' => 'admin_computations_kill'),
    array(
        'pass' => array('job_id')
    )
);

Router::connect('/zephy-cloud/admin/users/:user_id/projects/:project_uid/meshes/:mesh_id/status/:status.json',
    array('controller' => 'zephy_cloud', 'action' => 'admin_meshes_set_status'),
    array(
        'pass' => array("user_id", 'project_uid', "mesh_id", "status")
    )
);

Router::connect('/zephy-cloud/admin/transactions.html', array('controller' => 'zephy_cloud', 'action' => 'admin_transactions'));

Router::connect('/zephy-cloud/admin/search.json', array('controller' => 'zephy_cloud', 'action' => 'admin_search'));

/**
 * ...and connect the rest of 'Pages' controller's URLs.
 */
//Router::connect('/pages/*', array('controller' => 'pages', 'action' => 'display'));

/**
 * Load all plugin routes. See the CakePlugin documentation on
 * how to customize the loading of plugin routes.
 */
CakePlugin::routes();

/**
 * Load the CakePHP default routes. Only remove this if you do not want to use
 * the built-in default routes.
 */
require CAKE . 'Config' . DS . 'routes.php';






