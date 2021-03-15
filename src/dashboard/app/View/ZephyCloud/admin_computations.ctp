<div class="panel panel-flat">
  <div class="panel-heading">
    <h3 class="panel-title" ><b>
      <?php
        if(!($this->Filter->is_filtered('user_id') || $this->Filter->is_filtered('project_uid') || $this->Filter->is_filtered('status'))) {
          echo "All Computations";
        }
        elseif($this->Filter->is_filtered('project_uid')) {
          echo "Computations of project ".$this->Filter->get_filter_value('project_uid');
        }
        else {
          if($this->Filter->is_filtered('status')) {
              echo ucfirst($this->Filter->get_filter_value('status'))." computations";
          }
          else {
            echo "Computations";
          }
          if($this->Filter->is_filtered('user_id') && !$this->Filter->is_filtered('project_uid')) {
            echo " of user ".$user['email'];
          }
        } ?>
    </b></h3>
  </div>
  <div class="panel-body">
    <?php if (!empty($computations)): ?>
      <table class="table table-bordered table-hover">
        <thead>
          <tr>
            <th>job_id <?php echo $this->Order->links("job_id"); ?></th>
            <th>user <?php echo $this->Order->links("email"); echo $this->Filter->header_link('user_id'); ?></th>
            <th>project_uid <?php echo $this->Order->links("project_uid"); echo $this->Filter->header_link('project_uid'); ?></th>
            <th>create_date</th>
            <th>start_time</th>
            <th>end_time</th>
            <th>status <?php echo $this->Order->links("status"); echo $this->Filter->header_link('status'); ?></th>
            <th>progress</th>
            <th style="width:180px;">Action</th>
          </tr>
        </thead>
        <tbody>
          <?php foreach ($computations as $computation): ?>
            <tr>
              <td><a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_computations_show', 'job_id' => $computation["job_id"])); ?>"><?php echo $computation["job_id"]; ?></a></td>
              <td>
                <?php echo $this->Filter->link('user_id', $computation["user_id"]); ?>
                <a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_users_show', 'user_id' => $computation["user_id"])); ?>"><?php echo $computation["email"]; ?></a>
              </td>
              <td>
                <?php echo $this->Filter->link('project_uid', $computation["project_uid"]); ?>
                <a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_projects_view', 'user_id' => $computation["user_id"], 'project_uid' => $computation["project_uid"])); ?>"><?php echo AziugoTools::cutTitle($computation["project_uid"],".......",32, 7 ); ?></a>
              </td>
              <td><?php echo AziugoTools::human_date($computation["create_date"]); ?></td>
              <td><?php echo AziugoTools::human_date($computation["start_time"]); ?></td>
              <td><?php echo AziugoTools::human_date($computation["end_time"]); ?></td>
              <td>
                <?php
                echo $this->Filter->link('status', $computation["status"]);
                switch ($computation["status"]) {
                  case 'running':
                   echo '<span style="color:green; font-weight:bold">'.$computation["status"].'</span>';
                    break;
                  case 'killed':
                  case 'canceled':
                    echo '<span style="color:red; font-weight:bold">'.$computation["status"].'</span>';
                    break;
                  case 'finished':
                  default:
                    echo $computation["status"];
                    break;
                }
                ?>
              </td>
              <td>
                <?php
                  if ($computation["progress"] != 0) {
                    $progress = number_format(($computation["progress"]*100), 0);
                  }
                  else{
                    $progress = 0;
                  }
                ?>
                <div class="progress">
                  <div class="progress-bar bg-teal" style="width: <?php echo $progress; ?>%">
                  <span><?php echo $progress; ?>% Complete</span>
                  </div>
                </div>
              </td>
              <td>
                <div class="btn-group">
                  <a class="btn btn-success btn-sm" href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_computations_show', 'job_id' => $computation["job_id"])); ?>">View</a>
                  <button type="button" class="btn btn-primary dropdown-toggle" data-toggle="dropdown">Show log</button>
                  <ul class="dropdown-menu dropdown-menu-right">
                    <?php if ($computation["has_logs"] === true): ?>
                      <li><a class="btn btn-sm" href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_computations_show_log', 'job_id' => $computation["job_id"])); ?>">Log fragment</a></li>
                    <?php endif ?>
                  </ul>
                </div>
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
<?php if(!empty($computations)) { echo $this->Page->paginate('computations'); } ?>
<?php
  $this->append('script_footer');
?>
<?php
  $this->end();
?>
