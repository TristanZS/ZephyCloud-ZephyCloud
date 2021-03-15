      <div class="panel panel-flat">
        <div class="panel-heading">
          <h3 class="panel-title" ><b>Toolchains</b></h3>
        </div>
        <div class="panel-body">

<?php if (!empty($toolchains)): ?>
                  <table class="table table-bordered table-hover">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Fixed price</th>
                        <th>Machine limit</th>
                        <th style="width:150px;">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                       <?php foreach ($toolchains as $toolchain): ?>
                        <tr>
                          <td><?php echo $toolchain["name"]; ?></td>
                          <td><?php echo $toolchain["fixed_price"]; ?></td>
                          <td><?php echo $toolchain["machine_limit"]; ?></td>
                          <td>
                            <a class="btn btn-success btn-sm" href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_toolchains_show', 'toolchain_name' => $toolchain["name"])); ?>">View</a>
                            <a class="btn btn-info btn-sm" href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_toolchains_edit', 'toolchain_name' => $toolchain["name"])); ?>">Edit</a>
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
