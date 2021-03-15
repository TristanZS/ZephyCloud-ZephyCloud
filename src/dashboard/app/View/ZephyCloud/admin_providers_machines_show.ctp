      <div class="panel panel-flat">
        <div class="panel-heading">
          <h3 class="panel-title" ><b><?php echo $machine['name']." machines on ".$provider; ?></b></h3>
          <div class="heading-elements">
            <a class="btn btn-info btn-sm" href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_providers_machines_edit', 'providers_name' => $provider, 'machine_name' => $machine['name'])); ?>">Edit</a>
            <a class="btn btn-danger btn-sm open-DeleteConfirmation" data-toggle="modal" data-target="#DeleteConfirmation" data-url="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_providers_machines_delete', 'providers_name' => $provider, 'machine_name' => $machine['name'])); ?>">Delete</a>
          </div>
        </div>
        <div class="panel-body">
            <h4>General information:</h4>

            <!-- Input Text : start -->
            <div class="row form-group">
             <div class="col-md-3 text-right strong" >Name</div>
             <div class="col-md-9"><?php echo $machine["name"]; ?></div>
            </div>
            <!-- Input Text : end -->

            <!-- Input Text : start -->
            <div class="row form-group">
             <div class="col-md-3 text-right strong" >Provider</div>
                <div class="col-md-9"><a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_providers_machines', 'providers_name' => $provider)); ?>"><?php echo $provider; ?></a></div>
            </div>
            <!-- Input Text : end -->

                        <!-- Input Text : start -->
            <div class="row form-group">
             <div class="col-md-3 text-right strong" >Availability</div>
             <div class="col-md-9"><?php echo $machine["availability"]; ?> machines</div>
            </div>
            <!-- Input Text : end -->

            <!-- Input Text : start -->
            <div class="row form-group">
             <div class="col-md-3 text-right strong" >CPU</div>
                <div class="col-md-9"><?php echo $machine["cores"]; ?> cores</div>
            </div>
            <!-- Input Text : end -->

            <!-- Input Text : start -->
            <div class="row form-group">
             <div class="col-md-3 text-right strong" >RAM</div>
                <div class="col-md-9"><?php echo CakeNumber::toReadableSize($machine["ram"]); ?></div>
            </div>
            <!-- Input Text : end -->

            <hr />
            <h4>Pricing:</h4>

            <!-- Input Text : start -->
            <div class="row form-group">
              <div class="col-md-3 text-right strong" >Auto-update prices</div>
              <div class="col-md-9"><?php echo $machine["auto_update"] ? "true" : "false"; ?></div>
            </div>
            <!-- Input Text : end -->

            <?php foreach(array('root', 'gold', 'silver', 'bronze') as $rank): ?>
                <!-- Input Text : start -->
                <div class="row form-group">
                 <div class="col-md-3 text-right strong" >Price for <?php echo $rank; ?> users</div>
                    <div class="col-md-9"><?php echo $machine['prices'][$rank]; ?> zephycoins/hour</div>
                </div>
                <!-- Input Text : end -->
            <?php endforeach ?>

            <!-- Input Text : start -->
            <div class="row form-group">
             <div class="col-md-3 text-right strong" >Time granularity</div>
                <div class="col-md-9"><?php echo $machine["price_sec_granularity"]; ?> seconds (min: <?php echo $machine["price_min_sec_granularity"]; ?>s)</div>
            </div>
            <!-- Input Text : end -->


            <hr />
            <h4>Provider Cost:</h4>

            <!-- Input Text : start -->
            <div class="row form-group">
             <div class="col-md-3 text-right strong" >Cost:</div>
                <div class="col-md-9"><?php echo $machine["cost_per_hour"]." ".$machine["cost_currency"]; ?>/hour</div>
            </div>
            <!-- Input Text : end -->

            <!-- Input Text : start -->
            <div class="row form-group">
             <div class="col-md-3 text-right strong" >Time granularity</div>
                <div class="col-md-9"><?php echo $machine["cost_sec_granularity"]; ?> seconds (min: <?php echo $machine["cost_min_sec_granularity"]; ?>s)</div>
            </div>
            <!-- Input Text : end -->

            <hr />
            <h4>Allowed toolchains:</h4>
            <ul class="list-group">
              <?php foreach($toolchains as $toolchain): ?>
                <li class="list-group-item"><a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_toolchains_show', 'toolchain_name' => $toolchain)); ?>"><?php echo $toolchain; ?></a></li>
              <?php endforeach ?>
            </ul>
        </div>
      </div>


<?php
$this->append('script_footer');
?>

<?php
$this->end();
?>

