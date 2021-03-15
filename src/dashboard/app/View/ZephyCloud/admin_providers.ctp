      <div class="panel panel-flat">
        <div class="panel-heading">
          <h3 class="panel-title" ><b>Providers</b></h3>
        </div>
        <div class="panel-body">

<?php if (!empty($providers)): ?>
                  <table class="table table-bordered table-hover">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Location</th>
                        <th>Type</th>
                        <th>Details</th>
                        <th style="width:90px;">Action</th>
                      </tr>
                    </thead>
                    <tbody>
 <?php foreach ($providers as $provider): ?>
                        <tr>
                          <td><?php echo $provider["name"]; ?></td>
                          <td><?php echo $provider["location"]; ?></td>
                          <td><?php echo $provider["type"]; ?></td>
                          <td><?php
                                  $display = array();
                                  foreach($provider["provider_specific"] as $key => $value) {
                                    array_push($display, $key.": ".$value);
                                  }
                                  echo implode('<br/>', $display) ; ?></td>
                          <td>
                            <a class="btn btn-success btn-sm" href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_providers_machines', 'providers_name' => $provider["name"])); ?>">View</a>
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
