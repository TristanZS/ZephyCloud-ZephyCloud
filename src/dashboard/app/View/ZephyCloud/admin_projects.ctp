<div class="panel panel-flat">
  <div class="panel-heading">
    <h3 class="panel-title" ><b>
      <?php
        if(!($this->Filter->is_filtered('user_id') || $this->Filter->is_filtered('status') || $this->Filter->is_filtered('storage'))) {
          echo "All Projects";
        }
        else {
          if($this->Filter->is_filtered('status')) {
            echo ucfirst($this->Filter->get_filter_value('status'))." projects";
          }
          else {
            echo "Projects";
          }
          if($this->Filter->is_filtered('user_id')) {
            echo " of user ".$user['email'];
          }
          if($this->Filter->is_filtered('storage')) {
            echo " stored on ".$this->Filter->get_filter_value('storage');
          }
        }
      ?>
    </b></h3>
  </div>
  <div class="panel-body">
    <?php if (!empty($projects)): ?>
      <table class="table table-bordered table-hover">
        <thead>
          <tr>
            <th>UID <?php echo $this->Order->links("project_uid"); ?></th>
            <th>User <?php echo $this->Order->links("email"); echo $this->Filter->header_link('user_id'); ?></th>
            <th>Creation Date <?php echo $this->Order->links("creation_date"); ?></th>
            <th>Status <?php echo $this->Order->links("status"); echo $this->Filter->header_link('status'); ?></i></th>
            <th>Storage <?php echo $this->Order->links("storage"); echo $this->Filter->header_link('storage'); ?></th>
            <th style="width:180px;">Action</th>
          </tr>
        </thead>
        <tbody>
          <?php foreach ($projects as $project): ?>
            <tr>
              <td><a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_projects_view', 'user_id' => $project["user_id"], 'project_uid' => $project["project_uid"])); ?>"><?php echo AziugoTools::cutTitle($project["project_uid"],".......",32, 7 ); ?></a></td>
              <td><?php echo $this->Filter->link('user_id', $project["user_id"]); ?><a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_users_show', 'user_id' => $project["user_id"])); ?>"><?php echo $project["email"]; ?></a></td>
              <td><?php echo AziugoTools::human_date($project["create_date"]); ?></td>
              <td><?php echo $this->Filter->link('status', $project["status"]); ?><?php echo $project["status"]; ?></td>
              <td><?php echo $this->Filter->link('storage', $project["storage"]); ?><?php echo $project["storage"]; ?></td>
              <td>
                <a class="btn btn-success btn-sm" href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_projects_view', 'user_id' => $project["user_id"], 'project_uid' => $project["project_uid"])); ?>">View</a>
                <a class="btn btn-danger btn-sm open-DeleteConfirmation" data-toggle="modal" data-target="#DeleteConfirmation" data-url="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_projects_delete', 'user_id' => $project["user_id"], 'project_uid' => $project["project_uid"])); ?>">Delete</a>
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
<?php if(!empty($projects)) { echo $this->Page->paginate('projects'); } ?>
<?php
  $this->append('script_footer');
?>
<?php
  $this->end();
?>
