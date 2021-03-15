      <div class="panel panel-flat">
        <div class="panel-heading">
          <h3 class="panel-title" ><b><?php echo $toolchain['name']; ?> toolchain</b></h3>
          <div class="heading-elements">
            <a class="btn btn-info btn-sm" href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_toolchains_edit', 'toolchain_name' => $toolchain["name"])); ?>">Edit</a>
          </div>
        </div>
        <div class="panel-body">
            <h4>General information:</h4>
            <!-- Input Text : start -->
            <div class="row form-group">
             <div class="col-md-3 text-right strong" >Name</div>
             <div class="col-md-9"><?php echo $toolchain["name"]; ?></div>
            </div>
            <!-- Input Text : end -->


            <!-- Input Text : start -->
            <div class="row form-group">
             <div class="col-md-3 text-right strong" >Fixed price</div>
             <div class="col-md-9"><?php echo $toolchain["fixed_price"]; ?> Zephycoins/week</div>
            </div>
            <!-- Input Text : end -->

            <!-- Input Text : start -->
            <div class="row form-group">
             <div class="col-md-3 text-right strong" >Machine limit</div>
             <div class="col-md-9"><?php echo $toolchain["machine_limit"]; ?> machines</div>
            </div>
            <!-- Input Text : end -->

            <h4>Allowed machines:</h4>
            <div class="panel-group panel-group-control content-group-lg" id="accordion-control" style="padding-left:20px">
              <?php foreach($machines as $provider => $machine_list): ?>
                <div class="panel panel-white">
                  <div class="panel-heading">
                    <h6 class="panel-title">
                      <a class="collapsed" data-toggle="collapse" data-parent="#accordion-control" href="#accordion-controls-group-<?php echo $provider; ?>" aria-expanded="false"><?php echo $provider; ?></a>
                    </h6>
                    <div class="heading-elements">
                      <a class="btn btn-link" href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_providers_machines', 'providers_name' => $provider)); ?>">(view provider)</a>
                    </div>
                  </div>
                  <div id="accordion-controls-group-<?php echo $provider; ?>" class="panel-collapse collapse" aria-expanded="false" style="height: 0px;">
                    <div class="panel-body">
                      <ul>
                        <?php foreach($machine_list as $machine): ?>
                          <li class="list-group-item"><a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_providers_machines_show', 'providers_name' => $provider, 'machine_name' => $machine)); ?>"><?php echo $machine; ?></a></li>
                        <?php endforeach ?>
                      </ul>
                    </div>
                  </div>
                </div>
              <?php endforeach ?>
            </div>
        </div>
      </div>



<?php
$this->append('script_footer'); 
?>

<?php
$this->end(); 
?>












