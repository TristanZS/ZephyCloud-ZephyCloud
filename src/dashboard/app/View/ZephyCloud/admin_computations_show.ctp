
    <div class="row">
      <div class="col-md-12">
        <!-- Titre debut -->
        <div class="panel panel-flat">
          <div class="panel-heading">
            <h3 class="panel-title" ><b>Computation <?php echo $computation["job_id"]; ?></b></h3>
            <div class="heading-elements">

            <?php if (!in_array($computation["status"], ["killed", "canceled","finished"])): ?>
              <a class="btn btn-danger btn-sm open-DeleteConfirmation" data-toggle="modal" data-target="#DeleteConfirmation" data-url="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_computations_kill', 'job_id' => $computation["job_id"])); ?>">Kill Job</a>
            <?php else: ?>
              <a class="btn btn-sm bg-grey-300" style="cursor: not-allowed;" href="#">Kill Job</a>
            <?php endif ?>

            <div class="btn-group">
              <button type="button" class="btn btn-primary dropdown-toggle" data-toggle="dropdown">Show log</button>
              <ul class="dropdown-menu dropdown-menu-right">
                <?php if ($computation["has_logs"] === true): ?>
                  <li><a class="btn btn-sm" href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_computations_show_log', 'job_id' => $computation["job_id"])); ?>">Log fragment</a></li>
                <?php endif ?>
              </ul>
            </div>
          </div>
          </div>
          <div class="panel-body">
            <h3>General information</h3>
            <p>
                <!-- Input Text : start -->
                <div class="row form-group">
                 <div class="col-md-3 text-right strong" >Job id</div>
                 <div class="col-md-9"><?php echo $computation["job_id"]; ?></div>
                </div>
                <!-- Input Text : end -->

                <!-- Input Text : start -->
                <div class="row form-group">
                 <div class="col-md-3 text-right strong" >Status</div>
                 <div class="col-md-9"><?php echo $computation["status"]; ?> (<?php echo $computation["progress"]*100; ?>%)</div>
                </div>
                <!-- Input Text : end -->

                <!-- Input Text : start -->
                <div class="row form-group">
                 <div class="col-md-3 text-right strong" >Machine</div>
                 <div class="col-md-9"><a ><?php echo $computation["machine"]; ?></a> x <?php echo $computation["nbr_machines"]; ?></div>
                </div>
                <!-- Input Text : end -->

                <!-- Input Text : start -->
                <div class="row form-group">
                 <div class="col-md-3 text-right strong" >User</div>
                 <div class="col-md-9"><a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_users_show', 'user_id' => $computation["user_id"])); ?>"><?php echo $computation["email"]." (".$computation["user_id"].")"; ?></a></div>
                </div>
                <!-- Input Text : end -->


                <!-- Input Text : start -->
                <div class="row form-group">
                 <div class="col-md-3 text-right strong" >Project uid</div>
                 <div class="col-md-9"><a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_projects_view', 'user_id' => $computation["user_id"], 'project_uid' => $computation["project_uid"])); ?>"><?php echo $computation["project_uid"]; ?></a></div>
                </div>
                <!-- Input Text : end -->

                <?php if(isset($computation["toolchain_specific"]["mesh_id"])): ?>
                  <!-- Input Text : start -->
                  <div class="row form-group">
                   <div class="col-md-3 text-right strong" >Mesh detail</div>
                   <div class="col-md-9"><a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_projects_view', 'user_id' => $computation["user_id"], 'project_uid' => $computation["project_uid"], "#" => "/meshes/".$computation["toolchain_specific"]["calc_id"])); ?>">Mesh <?php echo $computation["toolchain_specific"]["mesh_id"]; ?></a></div>
                  </div>
                  <!-- Input Text : end -->
                <?php endif ?>
                <?php if(isset($computation["toolchain_specific"]["calc_id"])): ?>
                  <!-- Input Text : start -->
                  <div class="row form-group">
                   <div class="col-md-3 text-right strong" >Calculation detail</div>
                   <div class="col-md-9"><a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_projects_view', 'user_id' => $computation["user_id"], 'project_uid' => $computation["project_uid"], "#" => "/calculations/".$computation["toolchain_specific"]["calc_id"])); ?>">Calculation <?php echo $computation["toolchain_specific"]["calc_id"]; ?></a></div>
                  </div>
                  <!-- Input Text : end -->
                <?php endif ?>

                <!-- Input Text : start -->
                <div class="row form-group">
                 <div class="col-md-3 text-right strong" >Provider</div>
                 <div class="col-md-9"><a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_providers_machines', 'providers_name' => $computation["provider"])); ?>"><?php echo $computation["provider"]; ?></a></div>
                </div>
                <!-- Input Text : end -->

                <!-- Input Text : start -->
                <div class="row form-group">
                 <div class="col-md-3 text-right strong" >Toolchain</div>
                 <div class="col-md-9"><a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_toolchains_show', 'toolchain_name' => $computation["toolchain_name"])); ?>"><?php echo $computation["toolchain_name"]; ?></a></div>
                </div>
                <!-- Input Text : end -->

                <!-- Input Text : start -->
                <div class="row form-group">
                 <div class="col-md-3 text-right strong" >Computation consumption</div>
                 <div class="col-md-9"><?php echo $computation["computation_consumption"]; ?> ZephyCoins<a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_transactions', '?' => ['job_id' => $computation["job_id"]])); ?>"> (details)</a></div>
                </div>
                <!-- Input Text : end -->

                <!-- Input Text : start -->
                <div class="row form-group">
                 <div class="col-md-3 text-right strong" >Storage consumption</div>
                 <div class="col-md-9"><?php echo $computation["storage_consumption"]; ?> ZephyCoins<a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_transactions', '?' => ['job_id' => $computation["job_id"]])); ?>"> (details)</a></div>
                </div>
                <!-- Input Text : end -->
            </p>
            <hr />
            <h3>Details</h3>
            <p>
               <!-- Input Text : start -->
                <div class="row form-group">
                 <div class="col-md-3 text-right strong" >Create date</div>
                 <div class="col-md-9"><?php echo AziugoTools::human_date($computation["create_date"]); ?></div>
                </div>
                <!-- Input Text : end -->

                <!-- Input Text : start -->
                <div class="row form-group">
                 <div class="col-md-3 text-right strong" >Start_time</div>
                 <div class="col-md-9"><?php echo AziugoTools::human_date($computation["start_time"]); ?></div>
                </div>
                <!-- Input Text : end -->

                <!-- Input Text : start -->
                <div class="row form-group">
                 <div class="col-md-3 text-right strong" >End time</div>
                 <div class="col-md-9"><?php echo AziugoTools::human_date($computation["end_time"]); ?></div>
                </div>
                <!-- Input Text : end -->


                <!-- Input Text : start -->
                <div class="row form-group">
                 <div class="col-md-3 text-right strong" >User rank</div>
                 <div class="col-md-9"><?php echo $computation["user_rank"]; ?></div>
                </div>
                <!-- Input Text : end -->


                <!-- Input Text : start -->
                <div class="row form-group">
                 <div class="col-md-3 text-right strong" >Cost Currency</div>
                 <div class="col-md-9"><?php echo $computation["cost_currency"]; ?></div>
                </div>
                <!-- Input Text : end -->


                <!-- Input Text : start -->
                <div class="row form-group">
                 <div class="col-md-3 text-right strong" >Cost min. sec. granularity</div>
                 <div class="col-md-9"><?php echo $computation["cost_min_sec_granularity"]; ?></div>
                </div>
                <!-- Input Text : end -->


                <!-- Input Text : start -->
                <div class="row form-group">
                 <div class="col-md-3 text-right strong" >Cost per sec per machine</div>
                 <div class="col-md-9"><?php echo $computation["cost_per_sec_per_machine"]; ?></div>
                </div>
                <!-- Input Text : end -->


                <!-- Input Text : start -->
                <div class="row form-group">
                 <div class="col-md-3 text-right strong" >Cost sec granularity</div>
                 <div class="col-md-9"><?php echo $computation["cost_sec_granularity"]; ?></div>
                </div>
                <!-- Input Text : end -->


                <!-- Input Text : start -->
                <div class="row form-group">
                 <div class="col-md-3 text-right strong" >Fixed price</div>
                 <div class="col-md-9"><?php echo $computation["fixed_price"]; ?></div>
                </div>
                <!-- Input Text : end -->

                <!-- Input Text : start -->
                <div class="row form-group">
                 <div class="col-md-3 text-right strong" >Price min sec granularity</div>
                 <div class="col-md-9"><?php echo $computation["price_min_sec_granularity"]; ?></div>
                </div>
                <!-- Input Text : end -->

                <!-- Input Text : start -->
                <div class="row form-group">
                 <div class="col-md-3 text-right strong" >Price per sec per machine</div>
                 <div class="col-md-9"><?php echo $computation["price_per_sec_per_machine"]; ?></div>
                </div>
                <!-- Input Text : end -->

                <!-- Input Text : start -->
                <div class="row form-group">
                 <div class="col-md-3 text-right strong" >Price sec granularity</div>
                 <div class="col-md-9"><?php echo $computation["price_sec_granularity"]; ?></div>
                </div>
                <!-- Input Text : end -->
              </p>
          </div>
        </div>
      </div>
    </div>



<?php
$this->append('script_footer');
?>

<?php
$this->end();
?>
