<div class="panel panel-flat">
  <div class="panel-heading">
    <h3 class="panel-title" >
      <?php if(!$this->Filter->is_filtered('rank')): ?>
        <b>All Users</b>
      <?php else: ?>
        <b><?php echo ucfirst($this->Filter->get_filter_value('rank')); ?> users</b>
      <?php endif ?>
    </h3>
    <div class="heading-elements">
      <?php if($signin_url == null): ?>
        <a class="btn btn-success" href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_users_add')); ?>">Add user</a>
      <?php else: ?>
        <a class="btn btn-success" href="<?php echo $signin_url; ?>">Add user</a>
      <?php endif ?>
    </div>
  </div>
  <div class="panel-body">
    <?php if (!empty($users)): ?>
      <table class="table table-bordered table-hover">
        <thead>
          <tr>
            <th style="width:50px;"><?php echo $this->Order->links("user_id"); ?></th>
            <th>Login <?php echo $this->Order->links("login");?></th>
            <th>Email <?php echo $this->Order->links("email");?></th>
            <th>Subscription <?php echo $this->Order->links("rank"); echo $this->Filter->header_link('rank'); ?></th>
            <th>Credit<?php echo $this->Order->links("credit");?></th>
            <th style="width:450px;">Action</th>
          </tr>
        </thead>
        <tbody>
          <?php foreach ($users as $user): ?>
            <tr>
              <td><?php echo $user["id"]; ?></td>
              <td><a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_users_show', 'user_id' => $user["id"])); ?>"><?php echo $user["login"]; ?></a></td>
              <td><a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_users_show', 'user_id' => $user["id"])); ?>"><?php echo $user["email"]; ?></a></td>
              <td>
                <?php echo $this->Filter->link('rank', $user["rank"]); ?>
                <?php echo $user["rank"]; ?>
              </td>
              <td><?php echo $user["credit"]; ?> ZephyCoins<a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_transactions', '?' => ['user_id' => $user["id"]])); ?>"> (details)</a></td>
              <td>
                  <a class="btn btn-success btn-sm" href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_users_show', 'user_id' => $user["id"])); ?>">View</a>
                  <div class="btn-group">
                    <button type="button" class="btn border-slate text-slate-800 text-warning-600 btn-flat btn-icon dropdown-toggle" data-toggle="dropdown" aria-expanded="false">
                       <i class="icon-cog5"></i> &nbsp;<span class="caret"></span>
                    </button>
                    <ul class="dropdown-menu dropdown-menu-right" >
                      <li><a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_users_add_credit', 'user_id' => $user["id"])); ?>">Add credit</a></li>
                      <li><a class="border-warning open-ChangeRank" data-toggle="modal" data-target="#ChangeRank" data-login="<?php echo $user["login"]; ?>" data-user_id="<?php echo $user["id"]; ?>" data-rank="<?php echo $user["rank"]; ?>">Change rank</a></li>
                      <li class="divider"></li>
                      <li><a class="border-warning open-ResetPassword" data-toggle="modal" data-target="#ResetPassword" data-url="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_users_reset_password', 'user_email' => $user["email"])); ?>">Reset Password<i class="icon-warning22 text-danger pull-right"></i></a></li>
                      <li><a class="border-warning open-DeleteConfirmation" data-toggle="modal" data-target="#DeleteConfirmation" data-url="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_users_delete', 'user_id' => $user["id"])); ?>">Delete<i class="icon-warning22 text-danger pull-right"></i></a></li>
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
<?php if(!empty($users)) { echo $this->Page->paginate('users'); } ?>

<?php
  $this->append('script_footer');
?>

<div id="ResetPassword" tabindex="-1" role="dialog" class="modal fade">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal">
          <span aria-hidden="true">×</span>
          <span class="sr-only">Close</span>
        </button>
      </div>
      <div class="modal-body">
        <div class="text-center">
          <span class="text-danger icon icon-times-circle icon-5x"></span>
          <h3 class="text-danger">Danger</h3>
          <p>Are you sure you want to reset password this?</p>
          <div class="m-t-lg">
            <a class="btn btn-danger" href="#" id="UrlConfirm">Yes, reset it!</a>
            <button class="btn btn-default" data-dismiss="modal" type="button">Cancel</button>
          </div>
        </div>
      </div>
      <div class="modal-footer"></div>
    </div>
  </div>
</div>

<div id="ChangeRank" tabindex="-1" role="dialog" class="modal fade">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal">
          <span aria-hidden="true">×</span>
          <span class="sr-only">Close</span>
        </button>
      </div>
      <div class="modal-body">
        <div class="text-center">
          <span class="text-danger icon icon-times-circle icon-5x"></span>
          <h3 class="text-danger">Danger</h3>
          <p>Select the new subscription:</p>
          <form method="POST" action="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_users_change_rank')); ?>" style="max-width: 200px; margin: auto; padding: 10px;" >
            <input type="hidden" name="user_id" id="user_id" value=""/>
            <div class="form-group">
              <?php echo $this->Form->input('rank',
                                              array(
                                                'label'=>false,
                                                'options' => ["bronze"=>"bronze","silver"=>"silver", "gold"=>"gold", "root"=>"root"],
                                                'data-placeholder' => 'Choice',
                                                'empty' => '(Choice)',
                                                'class' => 'form-control',
                                                'required' => 'required'
                                              )); ?>
            </div>
          </form>
          <div class="m-t-lg">
            <a class="btn btn-danger validate" href="#">Save new rank!</a>
            <button class="btn btn-default" data-dismiss="modal" type="button">Cancel</button>
          </div>
        </div>
      </div>
      <div class="modal-footer"></div>
    </div>
  </div>
</div>

<script>
  <!--
  $(document).on("click", ".open-ResetPassword", function () {
       var myUrl = $(this).data('url');
       $(".modal-body #UrlConfirm").attr("href", myUrl);
  });

  $('#ChangeRank').on('show.bs.modal', function (event) {
    var button = $(event.relatedTarget);
    var rank = button.data('rank');
    var login = button.data('login');
    var user_id = button.data('user_id');

    var modal = $(this)
    modal.find("h3").text("Change the subscription for user "+login);
    modal.find('#rank').val(rank);
    modal.find('#user_id').val(user_id);
    modal.find('.validate').on("click", function () {
      modal.find("form").submit();
    });
  })
  -->
</script>

<?php
  $this->end();
?>
