      <div class="panel panel-flat">
        <div class="panel-heading">
          <h3 class="panel-title" ><b>Providers machines</b></h3>
          <div class="heading-elements">
                  <a class="btn btn-success" href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_providers_machines_create', 'providers_name' => $providers_name)); ?>">Create machine</a>
          </div>
        </div>
        <div class="panel-body">

<?php if (!empty($providers_machines)): ?>
                  <table class="table table-bordered table-hover">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>cores</th>
                        <th style="min-width:120px;">ram</th>
                        <th>availability</th>
                        <th>root</th>
                        <th>gold</th>
                        <th>silver</th>
                        <th>bronze</th>
                        <th>psec_granularity</th>
                        <th>pminsec granularity</th>
                        <th>cost/h</th>
                        <th>costsec granularity</th>
                        <th>costminsec granularity</th>
                        <th style="width:360px;">Action</th>
                      </tr>
                    </thead>
                    <tbody>

 <?php foreach ($providers_machines as $providers_machine): ?>
                        <tr>
                          <td><?php echo $providers_machine["name"]; ?></td>
                          <td><?php echo $providers_machine["cores"]; ?></td>
                          <td><?php echo CakeNumber::toReadableSize($providers_machine["ram"]); ?></td>
                          <td><?php echo $providers_machine["availability"]; ?></td>
                          <td><?php echo $providers_machine["prices"]["root"]; ?></td>
                          <td><?php echo $providers_machine["prices"]["gold"]; ?></td>
                          <td><?php echo $providers_machine["prices"]["silver"]; ?></td>
                          <td><?php echo $providers_machine["prices"]["bronze"]; ?></td>
                          <td><?php echo $providers_machine["price_sec_granularity"]; ?></td>
                          <td><?php echo $providers_machine["price_min_sec_granularity"]; ?></td>
                          <td><?php echo $providers_machine["cost_per_hour"]; ?> <?php echo $providers_machine["cost_currency"]; ?></td>
                          <td><?php echo $providers_machine["cost_sec_granularity"]; ?></td>
                          <td><?php echo $providers_machine["cost_min_sec_granularity"]; ?></td>
                          <td>
                            <a class="btn btn-success btn-sm" href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_providers_machines_show', 'providers_name' => $providers_name, 'machine_name' => $providers_machine["name"])); ?>">View</a>
                            <a class="btn btn-info btn-sm" href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_providers_machines_edit', 'providers_name' => $providers_name, 'machine_name' => $providers_machine["name"])); ?>">Edit</a>
                            <a class="btn btn-danger btn-sm open-DeleteConfirmation" data-toggle="modal" data-target="#DeleteConfirmation" data-url="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_providers_machines_delete', 'providers_name' => $providers_name, 'machine_name' => $providers_machine["name"])); ?>">Delete</a>
                          </td>
                        </tr>
                      <?php endforeach ?>
                    </tbody>
                  </table>
<?php else: ?>
<span style="font-weight: bold;font-weight: 26px">No Data</span>
<?php endif ?>
        <!-- table fin -->
        </div>
      </div>
      <!-- /custom handle -->

<?php
$this->append('script_footer');
?>

<?php
$this->end();
?>

