<?php
              $menu = array();
              $menu[] = array(
                              "icon" =>"icon-home",
                              "id" =>"Home",
                              "name" =>"Home",
                              "url" =>$this->Html->url(array('plugin' => null,'controller' => 'home', 'action' => 'index'), true)
                            );


              $menu[] = array(
                              "authoriz" =>["admin", "manager"],
                              "icon" =>"icon-cogs",
                              "id" =>"ZephyCloud",
                              "name" =>"ZephyCloud",
                              "url" =>"#",
                              "sub" =>array(
                                                array(
                                                  "name" =>"Users",
                                                  "url" =>$this->Html->url(array('controller' => 'zephy_cloud', 'action' => 'admin_users_index'), true),
                                                ),



                                                array(
                                                  "name" =>"Projects",
                                                  "url" =>$this->Html->url(array('controller' => 'zephy_cloud', 'action' => 'admin_projects'), true),
                                                ),
                                                array(
                                                  "name" =>"Currencies",
                                                  "url" =>$this->Html->url(array('controller' => 'zephy_cloud', 'action' => 'admin_currencies'), true),
                                                ),

                                               array(
                                                  "name" =>"Providers",
                                                  "url" =>$this->Html->url(array('controller' => 'zephy_cloud', 'action' => 'admin_providers'), true),
                                                ),
         

                                               array(
                                                  "name" =>"Toolchains",
                                                  "url" =>$this->Html->url(array('controller' => 'zephy_cloud', 'action' => 'admin_toolchains'), true),
                                                ),

                                               array(
                                                  "name" =>"Transactions",
                                                  "url" =>$this->Html->url(array('controller' => 'zephy_cloud', 'action' => 'admin_transactions'), true),
                                                ),
                                               array(
                                                  "name" =>"Computations",
                                                  "url" =>$this->Html->url(array('controller' => 'zephy_cloud', 'action' => 'admin_computations'), true),
                                                ),
                                          )
                        );


      
              $menu[] = array(
                              "icon" =>"icon-switch",
                              "id" =>"Quit",
                              "name" =>"Quit",
                              "url" =>$this->Html->url(array('plugin' => null,'controller' => 'auth', 'action' => 'logout'), true)
                            );
              ?>



          <!-- Main navigation -->
          <div class="sidebar-category sidebar-category-visible">
            <div class="category-content no-padding">
              <ul class="navigation navigation-main navigation-accordion">
                 <li class="navigation-header"><span>Main</span> <i class="icon-menu" title="Main pages"></i></li>
                <?php foreach ($menu as $menu_element): ?>
				  <?php if(empty($menu_element["authoriz"]) || AuthGroups::authoriz($menu_element["authoriz"]) === true): ?>
                    <?php if (empty($menu_element["sub"])): ?>
                        <li <?php echo (!empty($menu_active_element) AND $menu_element["id"] == $menu_active_element)?'class="active"':"" ?>><a href="<?php echo $menu_element["url"]; ?>" <?php echo (!empty($menu_element["target"]) AND $menu_element["target"] =="_blank")?'target="_blank"':"" ?>><i class="<?php echo $menu_element["icon"]; ?>"></i> <span><?php echo $menu_element["name"]; ?></span>
                           <?php if (!empty($menu_element["count"]["value"])): ?>
                            <span class="label <?php echo $menu_element["count"]["color"]; ?>"><?php echo $menu_element["count"]["value"]; ?></span>
                            <?php endif ?>
                        </a></li>
                    <?php else: ?>
                      <li <?php echo (!empty($menu_active_element) AND $menu_element["id"] == $menu_active_element)?'class="active"':"" ?>>
                        <a href="#"><i class="<?php echo $menu_element["icon"]; ?>"></i> <span><?php echo $menu_element["name"]; ?></span></a>
                        <ul>
                          <?php foreach ($menu_element["sub"] as $submenu): ?>
                              <?php if (empty($menu_element["authoriz"]) OR  AuthGroups::authoriz($menu_element["authoriz"])=== true): ?>
                                <li><a href="<?php echo $submenu["url"]; ?>" <?php echo (!empty($submenu["target"]))?'target="'.$submenu["target"].'"':"" ?>><span><?php echo $submenu["name"]; ?></span>

                                <?php if (!empty($submenu["count"]["value"])): ?>
                                <span class="label <?php echo $submenu["count"]["color"]; ?>"><?php echo $submenu["count"]["value"]; ?></span>
                              <?php endif ?>
                            <?php endif ?>

                            </a></li>
                          <?php endforeach ?>
                        </ul>
                      </li>
                    <?php endif ?>
                  <?php endif ?>
                <?php endforeach ?>
              </ul>
            </div>
          </div>
          <!-- /main navigation -->
