<div class="panel panel-flat">
  <div class="panel-heading">
    <h3 class="panel-title" ><b>
      <?php
        if(!($this->Filter->is_filtered('user_id') || $this->Filter->is_filtered('project_uid') || $this->Filter->is_filtered('description') || $this->Filter->is_filtered('job_id'))) {
          echo "All transactions";
        }
        else {
          echo "Transactions";
          if($this->Filter->is_filtered('job_id')) {
            echo " of computation ".$this->Filter->get_filter_value('job_id');
          }
          elseif($this->Filter->is_filtered('project_uid')) {
            echo " of project ".$this->Filter->get_filter_value('project_uid');
          }
          elseif($this->Filter->is_filtered('user_id') && !$this->Filter->is_filtered('project_uid')) {
            echo " of user ".$user['email'];
          }
          if($this->Filter->is_filtered('description')) {
            echo " with specific description";
          }
        }
      ?>
    </b></h3>
  </div>
  <div class="panel-body">
    <?php if (!empty($transactions)): ?>
      <table class="table table-bordered table-hover">
        <thead>
          <tr>
            <th># <?php echo $this->Order->links("id"); ?></th>
            <th>User <?php echo $this->Order->links("email"); echo $this->Filter->header_link('user_id'); ?></th>
            <th>Amount <?php echo $this->Order->links("amount"); ?></th>
            <th>Description <?php echo $this->Order->links("description"); echo $this->Filter->header_link('description');?></th>
            <th>Date <?php echo $this->Order->links("date"); ?></th>
            <th>Project <?php echo $this->Order->links("project_uid"); echo $this->Filter->header_link('project_uid');?></th>
            <th>Computation <?php echo $this->Order->links("job_id"); echo $this->Filter->header_link('job_id');?></th>
            <th style="width:90px;">Action</th>
          </tr>
        </thead>
        <tbody>
          <?php foreach ($transactions as $transaction): ?>
            <tr>
              <td><?php echo $transaction["id"]; ?></td>
              <td>
                <?php echo $this->Filter->link('user_id', $transaction["user_id"]); ?>
                <a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_users_show', 'user_id' => $transaction["user_id"])); ?>"><?php echo $transaction["email"]; ?></a>
              </td>
              <td>
                <?php if($transaction["amount"] > 0): ?>
                  <span style="color:green; font-weight:bold"><?php echo $transaction["amount"]; ?> Zephycoins</span>
                <?php else: ?>
                  <span style="color:red; font-weight:bold"><?php echo $transaction["amount"]; ?> Zephycoins</span>
                <?php endif ?>
              </td>
              <td>
                <?php echo $this->Filter->link('description', $transaction["description"]); ?>
                <?php echo $transaction["description"]; ?>
              </td>
              <td><?php echo AziugoTools::human_date($transaction["date"]); ?></td>
              <td>
                <?php if($transaction["project_uid"] != null): ?>
                  <?php echo $this->Filter->link('project_uid', $transaction["project_uid"]); ?>
                  <a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_projects_view', 'user_id' => $transaction["user_id"], 'project_uid' => $transaction["project_uid"])); ?>">
                    <?php echo AziugoTools::cutTitle($transaction["project_uid"],".......",32, 7 ); ?>
                  </a>
                <?php endif ?>
              </td>
              <td>
                <?php if($transaction["job_id"] != null): ?>
                  <?php echo $this->Filter->link('job_id', $transaction["job_id"]); ?>
                  <a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_computations_show', 'job_id' => $transaction["job_id"])); ?>">
                    <?php echo $transaction["job_id"]; ?>
                  </a>
                <?php endif ?>
              </td>
              <td>
                <a class="btn btn-danger btn-sm" href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_transactions_cancel', 'transaction_ids' => $transaction["id"])); ?>">Cancel</a>
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
<?php if(!empty($transactions)) { echo $this->Page->paginate('transactions'); } ?>
<?php $this->append('script_footer'); ?>
<?php $this->end(); ?>
