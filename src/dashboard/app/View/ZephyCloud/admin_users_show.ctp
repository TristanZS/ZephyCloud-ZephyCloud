    <div class="row">
      <div class="col-md-6">
        <!-- Titre debut -->
        <div class="panel panel-flat">
          <div class="panel-heading">
            <h3 class="panel-title" ><b>User <?php echo $user["login"]; ?></b></h3>
            <div class="heading-elements">
              <div class="btn-group">
                <?php if(!$user["deleted"]): ?>
                  <button type="button" class="btn border-slate text-slate-800 text-warning-600 btn-flat btn-icon dropdown-toggle" data-toggle="dropdown" aria-expanded="false">
                     <i class="icon-cog5"></i> &nbsp;<span class="caret"></span>
                  </button>
                  <ul class="dropdown-menu dropdown-menu-right" >
                    <li><a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_users_add_credit', 'user_id' => $user["id"])); ?>">Add credit</a></li>
                    <li><a class="border-warning open-ChangeRank" data-toggle="modal" data-target="#ChangeRank" data-login="<?php echo $user["login"]; ?>" data-user_id="<?php echo $user["id"]; ?>" data-rank="<?php echo $user["rank"]; ?>">Change rank</a></li>
                    <li class="divider"></li>
                    <li><a class="border-warning open-ResetPassword" data-toggle="modal" data-target="#ResetPassword" data-url="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_users_reset_password', 'user_email' => $user["email"])); ?>">Reset Password<i class="icon-warning22 text-danger pull-right"></i></a></li>
                    <?php if(!$user["deleted"]): ?>
                      <li><a class="border-warning open-DeleteConfirmation" data-toggle="modal" data-target="#DeleteConfirmation" data-url="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_users_delete', 'user_id' => $user["id"])); ?>">Delete<i class="icon-warning22 text-danger pull-right"></i></a></li>
                    <?php endif ?>
                  </ul>
                <?php endif ?>
              </div>
            </div>
          </div>
          <div class="panel-body">
            <!-- Input Text : start -->
            <div class="row form-group">
             <div class="col-md-3 text-right strong" >Login</div>
             <div class="col-md-9"><?php echo $user["login"]; ?></div>
            </div>
            <!-- Input Text : end -->

            <!-- Input Text : start -->
            <div class="row form-group">
             <div class="col-md-3 text-right strong" >Id</div>
             <div class="col-md-9"><?php echo $user["id"]; ?></div>
            </div>

            <!-- Input Text : start -->
            <div class="row form-group">
             <div class="col-md-3 text-right strong" >Email</div>
             <div class="col-md-9"><?php echo $user["email"]; ?></div>
            </div>
            <!-- Input Text : end -->

            <!-- Input Text : start -->
            <div class="row form-group">
             <div class="col-md-3 text-right strong" >Subscription</div>
             <div class="col-md-9"><?php echo $user["rank"]; ?></div>
            </div>
            <!-- Input Text : end -->

            <!-- Input Text : start -->
            <div class="row form-group">
             <div class="col-md-3 text-right strong" >Credit balance</div>
             <div class="col-md-9"><?php echo $user["credit"]; ?> Zephycoins <a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_transactions', '?' => ['user_id' => $user["id"]])); ?>"> (details)</a></div>
            </div>
            <!-- Input Text : end -->

            <!-- Input Text : start -->
            <div class="row form-group">
             <div class="col-md-3 text-right strong" >Deleted</div>
             <div class="col-md-9"><?php echo $user["deleted"] ? "Yes" : "No"; ?></div>
            </div>
            <!-- Input Text : end -->
          </div>
        </div>
      </div>
    </div>


    <style>
    .table .text-ellipsis {
      position: relative;
    }
    .table .text-ellipsis span {
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
      position: absolute;
      left: 0;
      right: 0;
    }
    .text-ellipsis:before {
      content: '';
      display: inline-block;
    }
    </style>
      <div class="panel panel-flat">
        <div class="panel-heading">
          <h3 class="panel-title" ><b>Projects</b></h3>
        </div>
        <div class="panel-body">

<?php if (!empty($projects)): ?>
                  <table class="table table-bordered table-hover">
                    <thead>
                      <tr>
                        <th>UID</th>
                        <th>Creation Date</th>
                        <th>Status</th>
                        <th>Storage</th>
                        <th style="width:180px;">Action</th>
                      </tr>
                    </thead>
                    <tbody>

 <?php foreach ($projects as $project): ?>
                        <tr>
                          <td><a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_projects_view', 'user_id' => $project["user_id"], 'project_uid' => $project["project_uid"])); ?>"><?php echo AziugoTools::cutTitle($project["project_uid"],".......",32, 7 ); ?></a></td>
                          <td><?php echo AziugoTools::human_date($project["create_date"]); ?></td>
                          <td><?php echo $project["status"]; ?></td>
                          <td><?php echo $project["storage"]; ?></td>
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

</script>

<?php
$this->append('script_footer');
?>


<?php
$this->end();
?>
