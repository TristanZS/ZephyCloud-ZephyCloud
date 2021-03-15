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

<div class="row">
  <div class="col-md-6">
    <!-- Titre debut -->
    <div class="panel panel-flat">
      <div class="panel-heading">
        <h3 class="panel-title" ><b>Project Information</b></h3>
        <div class="heading-elements">
          <?php if (!in_array($project["status"], ["raw"])): ?>
            <a class="btn btn-danger btn-sm" href="#" onclick="set_project_raw(); return false">Set Raw</a>
          <?php endif ?>
        </div>
      </div>
      <div class="panel-body">



        <!-- Input Text : start -->
        <div class="row form-group">
         <div class="col-md-3 text-right strong" >User</div>
         <div class="col-md-9"><a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_users_show', 'user_id' => $project["user_id"])); ?>"><?php echo $project["login"]; ?></a></div>
        </div>
        <!-- Input Text : end -->



        <!-- Input Text : start -->
        <div class="row form-group">
         <div class="col-md-3 text-right strong" >Project uid</div>
         <div class="col-md-9"><?php echo $project["project_uid"]; ?></div>
        </div>
        <!-- Input Text : end -->

        <!-- Input Text : start -->
        <div class="row form-group">
         <div class="col-md-3 text-right strong" >Creation date</div>
         <div class="col-md-9"><?php echo AziugoTools::human_date($project["create_date"]); ?></div>
        </div>
        <!-- Input Text : end -->

        <!-- Input Text : start -->
        <div class="row form-group">
         <div class="col-md-3 text-right strong" >Status</div>
         <div class="col-md-9"><?php echo $project["status"]; ?></div>
        </div>
        <!-- Input Text : end -->

        <!-- Input Text : start -->
        <div class="row form-group">
         <div class="col-md-3 text-right strong" >Storage</div>
         <div class="col-md-9"><?php echo $project["storage"]; ?></div>
        </div>
        <!-- Input Text : end -->



        <!-- Input Text : start -->
        <div class="row form-group">
         <div class="col-md-3 text-right strong" >Total size</div>
         <div class="col-md-9"><?php echo CakeNumber::toReadableSize($project["total_size"]); ?></div>
        </div>
        <!-- Input Text : end -->

        <!-- Input Text : start -->
        <div class="row form-group">
          <div class="col-md-3 text-right strong" >Credits spent</div>
          <div class="col-md-9"><?php echo $project["amount"]; ?> ZephyCoins<a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_transactions', '?' => ['project_uid' => $project["project_uid"]])); ?>"> (details)</a></div>
        </div>
        <!-- Input Text : end -->

        <!-- Input Text : start -->
        <div class="row form-group">
         <div class="col-md-3 text-right strong" >Raw file url</div>
         <div class="col-md-9"><a href="<?php echo htmlspecialchars($project["raw_file_url"]); ?>"><?php echo htmlspecialchars($project["raw_file_url"]); ?></a></div>
        </div>
        <!-- Input Text : end -->


        <!-- Input Text : start -->
        <div class="row form-group">
         <div class="col-md-3 text-right strong" >Analyzed file url</div>
         <div class="col-md-9"><a href="<?php echo htmlspecialchars($project["analyzed_file_url"]); ?>"><?php echo htmlspecialchars($project["analyzed_file_url"]); ?></a></div>
        </div>
        <!-- Input Text : end -->
      </div>
    </div>
  </div>
</div>

<div class="panel panel-flat">
  <div class="panel-heading">
    <h3 class="panel-title" ><b>Meshes</b></h3>
  </div>
  <div class="panel-body">
    <table class="table table-bordered table-hover clickable">
      <thead>
        <tr>
          <th>Id</th>
          <th>Name</th>
          <th>Status</th>
          <th>Creation date</th>
          <th>Calculation count</th>
        </tr>
      </thead>
      <tbody>
        <?php foreach ($project["meshes"] as $mesh): ?>
          <?php if($mesh["delete_date"] != null): ?>
           <tr class="clickable-row deleted" data-metaurl="/meshes/<?php echo $mesh["mesh_id"]; ?>">
          <?php else: ?>
           <tr class="clickable-row" data-metaurl="/meshes/<?php echo $mesh["mesh_id"]; ?>">
          <?php endif ?>
            <td><?php echo $mesh["mesh_id"]; ?></td>
            <td><?php echo $mesh["name"]; ?></td>
            <td><?php echo $mesh["status"]; ?></td>
            <td><?php echo AziugoTools::human_date($mesh["create_date"]); ?></td>
            <?php
              $count = 0;
              foreach ($project["calculations"] as $calc) {
                if($calc["mesh_id"] == $mesh["mesh_id"]) {
                  $count += 1;
                }
              }
            ?>
            <td><?php echo $count; ?> calculations</td>
          </tr>
          <tr class="dynamic_details">
            <td colspan="5">
              <div class="panel panel-flat">
                <div class="panel-heading">
                  <h3 class="panel-title"><b>Details of mesh <?php echo htmlspecialchars($mesh['name']) ?></b></h3>
                  <?php if (!in_array($mesh["status"], ["canceled"])): ?>
                    <a class="btn btn-danger btn-sm" href="#" onclick="set_mesh_failed('<?php echo $mesh['mesh_id']; ?>'); return false">Set Canceled</a>
                  <?php endif ?>
                </div>
                <div class="panel-body">
                  <div class="row form-group">
                    <div class="col-md-3 text-right strong">Name</div>
                    <div class="col-md-9"><?php echo htmlspecialchars($mesh['name']) ?></div>
                  </div>
                  <div class="row form-group">
                    <div class="col-md-3 text-right strong">Id</div>
                    <div class="col-md-9"><?php echo htmlspecialchars($mesh['mesh_id']) ?></div>
                  </div>
                  <div class="row form-group">
                    <div class="col-md-3 text-right strong">Status</div>
                    <div class="col-md-9"><?php echo htmlspecialchars($mesh['status']) ?></div>
                  </div>
                  <div class="row form-group">
                    <div class="col-md-3 text-right strong">Creation date</div>
                    <div class="col-md-9"><?php echo AziugoTools::human_date($mesh["create_date"]); ?></div>
                  </div>
                  <div class="row form-group">
                    <div class="col-md-3 text-right strong">Deletion date</div>
                    <div class="col-md-9"><?php echo AziugoTools::human_date($mesh["delete_date"]); ?></div>
                  </div>
                  <div class="row form-group">
                    <div class="col-md-3 text-right strong">Preview file</div>
                    <div class="col-md-9 file_link"><?php echo htmlspecialchars($mesh['preview_file_id']) ?> <i class="icon-spinner6 spinner position-left nojs-hide"></i></div>
                  </div>
                  <div class="row form-group">
                    <div class="col-md-3 text-right strong">Result file</div>
                    <div class="col-md-9 file_link"><?php echo htmlspecialchars($mesh['result_file_id']) ?> <i class="icon-spinner6 spinner position-left nojs-hide"></i></div>
                  </div>
                </div>
              </div>
            </td>
          </tr>
        <?php endforeach ?>
      </tbody>
    </table>
  <!-- table fin -->
  </div>
</div>

<div class="panel panel-flat">
  <div class="panel-heading">
    <h3 class="panel-title" ><b>Calculations</b></h3>
  </div>
  <div class="panel-body">
    <table class="table table-bordered table-hover clickable calculations">
      <thead>
        <tr>
          <th>name</th>
          <th>status</th>
          <th>mesh_id</th>
          <th>create_date</th>
          <th>delete_date</th>
        </tr>
      </thead>
      <tbody>
        <?php foreach ($project["calculations"] as $calc): ?>
          <?php if($calc["delete_date"] != null): ?>
            <tr class="clickable-row deleted" data-metaurl="/calculations/<?php echo $calc["calc_id"]; ?>">
          <?php else: ?>
            <tr class="clickable-row" data-metaurl="/calculations/<?php echo $calc["calc_id"]; ?>">
          <?php endif ?>
            <td class="text-ellipsis"><span style="padding-right: 10px;padding-left: 10px;"><?php echo $calc["name"]; ?></span></td>
            <td><?php echo $calc["status"]; ?></td>
            <td><?php echo $calc["mesh_id"]; ?></td>
            <td><?php echo AziugoTools::human_date($calc["create_date"]); ?></td>
            <td><?php echo AziugoTools::human_date($calc["delete_date"]); ?></td>
          </tr>
          <tr class="dynamic_details">
            <td colspan="5">
              <div class="panel panel-flat">
                <div class="panel-heading">
                  <h3 class="panel-title"><b>Details of calculation <?php echo $calc["name"]; ?></b></h3>
                  <?php if (!in_array($calc["status"], ["canceled"])): ?>
                    <a class="btn btn-danger btn-sm" href="#" onclick="set_calc_failed('<?php echo $calc["calc_id"]; ?>'); return false">Set Canceled</a>
                  <?php endif ?>
                </div>
                <div class="panel-body">
                  <div class="row form-group">
                    <div class="col-md-3 text-right strong">Name</div>
                    <div class="col-md-9"><?php echo $calc["name"]; ?></div>
                  </div>
                  <div class="row form-group">
                    <div class="col-md-3 text-right strong">Status</div>
                    <div class="col-md-9"><?php echo $calc["status"]; ?></div>
                  </div>
                  <div class="row form-group">
                    <div class="col-md-3 text-right strong">Computation</div>
                    <div class="col-md-9"><a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_computations_show', 'job_id' => $calc["job_id"])); ?>"><?php echo $calc["job_id"]; ?></a></div>
                  </div>
                  <div class="row form-group">
                    <div class="col-md-3 text-right strong">Mesh</div>
                    <div class="col-md-9"><a href="#/meshes/<?php echo $mesh["mesh_id"]; ?>"><?php echo $calc["mesh_id"]; ?></a></div>
                  </div>
                  <div class="row form-group">
                    <div class="col-md-3 text-right strong">Creation date</div>
                    <div class="col-md-9"><?php echo AziugoTools::human_date($calc["create_date"]); ?></div>
                  </div>
                  <div class="row form-group">
                    <div class="col-md-3 text-right strong">Deletion date</div>
                    <div class="col-md-9"><?php echo AziugoTools::human_date($calc["delete_date"]); ?></div>
                  </div>
                  <div class="row form-group">
                    <div class="col-md-3 text-right strong">Logs</div>
                    <div class="col-md-9">
                      <?php if ($calc["has_logs"] === true): ?>
                        <a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_computations_show_log', 'job_id' => $calc["job_id"])); ?>">Log fragment</a>
                      <?php else: ?>
                        No log fragment
                      <?php endif ?>
                    </div>
                  </div>
                  <div class="row form-group">
                    <div class="col-md-3 text-right strong">Status file</div>
                    <div class="col-md-9 file_link"><?php echo $calc["status_file_id"]; ?> <i class="icon-spinner6 spinner position-left nojs-hide"></i></div>
                  </div>
                  <div class="row form-group">
                    <div class="col-md-3 text-right strong">Result file</div>
                    <div class="col-md-9 file_link"><?php echo $calc["result_file_id"]; ?> <i class="icon-spinner6 spinner position-left nojs-hide"></i></div>
                  </div>
                  <div class="row form-group">
                    <div class="col-md-3 text-right strong">Internal file</div>
                    <div class="col-md-9 file_link"><?php echo $calc["internal_file_id"]; ?> <i class="icon-spinner6 spinner position-left nojs-hide"></i></div>
                  </div>
                  <div class="row form-group">
                    <div class="col-md-3 text-right strong">Iterations file</div>
                    <div class="col-md-9 file_link"><?php echo $calc["iterations_file_id"]; ?> <i class="icon-spinner6 spinner position-left nojs-hide"></i></div>
                  </div>
                  <div class="row form-group">
                    <div class="col-md-3 text-right strong">Reduce file</div>
                    <div class="col-md-9 file_link"><?php echo $calc["reduce_file_id"]; ?> <i class="icon-spinner6 spinner position-left nojs-hide"></i></div>
                  </div>
                </div>
              </div>
            </td>
          </tr>
        <?php endforeach ?>
      </tbody>
    </table>
  <!-- table fin -->
  </div>
</div>

<?php
$this->append('script_footer');
?>

<script type="text/javascript">
<!--


  function escapeHtml(unsafe) {
      return String(unsafe)
           .replace(/&/g, "&amp;")
           .replace(/</g, "&lt;")
           .replace(/>/g, "&gt;")
           .replace(/"/g, "&quot;")
           .replace(/'/g, "&#039;");
  }

  //Finds y value of given object
  function find_y_pos(obj) {
    var curtop = 0;
    if (obj.offsetParent) {
        do {
            curtop += obj.offsetTop;
        } while (obj = obj.offsetParent);
        return [curtop];
    }
  }

  $(".clickable-row").click(function(event) {
      if($(this).hasClass("current_details")) {
        close_details(true);
      }
      else {
        show_details(this, true);
      }
  });

  function close_details(add_history=false){
      $(".current_details").removeClass("current_details");
      $(".dynamic_details").hide();
      if(add_history) {
        window.history.pushState({'path': ""}, null, "#");
      }
  }

  function set_project_raw() {
    var url = <?php echo json_encode($this->Html->url(array('plugin' => null,
                                                            'controller' => 'zephy_cloud',
                                                            'action' => 'admin_projects_set_status',
                                                            'project_uid' => $project["project_uid"],
                                                            'user_id' => $project["user_id"],
                                                            'status' => "raw"))); ?>;
    $("#loading-overlay").show();
    api_call(url, {
      on_success(data) {
        document.location.reload(true);
      },
      on_error(error_list) {
        text = "";
        for(var i = 0; i < error_list.length; i++) {
          console.error(error_list[i]);
          text += "<br/>" + error_list[i];
        }
        display_error(text, "Unable to change project status");
      },
      on_complete() {
         $("#loading-overlay").hide();
      }
    });
  }

  function set_mesh_failed(mesh_id) {
    var url = <?php echo json_encode($this->Html->url(array('plugin' => null,
                                                            'controller' => 'zephy_cloud',
                                                            'action' => 'admin_meshes_set_status',
                                                            'project_uid' => $project["project_uid"],
                                                            'user_id' => $project["user_id"],
                                                            'mesh_id' => "123456789987654321",
                                                            'status' => "canceled"))); ?>;
    var real_url = url.replace(/123456789987654321/g, mesh_id);
    $("#loading-overlay").show();
    api_call(real_url, {
      on_success(data) {
        document.location.reload(true);
      },
      on_error(error_list) {
        text = "";
        for(var i = 0; i < error_list.length; i++) {
          console.error(error_list[i]);
          text += "<br/>" + error_list[i];
        }
        display_error(text, "Unable to change mesh status");
      },
      on_complete() {
         $("#loading-overlay").hide();
      }
    });
  }

  function set_calc_failed(calc_id) {
    var url = <?php echo json_encode($this->Html->url(array('plugin' => null,
                                                            'controller' => 'zephy_cloud',
                                                            'action' => 'admin_calc_set_status',
                                                            'project_uid' => $project["project_uid"],
                                                            'user_id' => $project["user_id"],
                                                            'calc_id' => "123456789987654321",
                                                            'status' => "canceled"))); ?>;
    var real_url = url.replace(/123456789987654321/g, calc_id);
    $("#loading-overlay").show();
    api_call(url, {
      on_success(data) {
        document.location.reload(true);
      },
      on_error(error_list) {
        text = "";
        for(var i = 0; i < error_list.length; i++) {
          console.error(error_list[i]);
          text += "<br/>" + error_list[i];
        }
        display_error(text, "Unable to change calc status");
      },
      on_complete() {
         $("#loading-overlay").hide();
      }
    });
  }


  function show_details(row, add_history=false) {
      close_details();
      if(!row) {
        return;
      }

      var $row = $(row);
      var $details = $row.next('tr');
      if(!$details.hasClass("dynamic_details")) {
        return;
      }
      $row.addClass("current_details");
      $details.show(400);
      $(".file_link", $details).each(function(i) {
          var element = this;
          var url = <?php echo json_encode($this->Html->url(array('plugin' => null,
                                                                  'controller' => 'zephy_cloud',
                                                                  'action' => 'admin_projects_file_url',
                                                                  'project_uid' => $project["project_uid"],
                                                                  'user_id' => $project["user_id"],
                                                                  'file_id' => 123456789987654321))); ?>;
          var file_id = this.textContent.replace(/^\s+|\s+$/g, '');
          if(file_id == "") {
            $("i", element).remove();
            return;
          }
          var real_url = url.replace(/123456789987654321/g, file_id);
          api_call(real_url, {
            on_success(data) {
              $(element).append($('<a href="'+data+'">'+data+'</a>'));
            },
            on_error(error_list) {
              text = "";
              for(var i = 0; i < error_list.length; i++) {
                console.error(error_list[i]);
                text += "<br/>" + error_list[i];
              }
              display_error(text, "Unable to load file "+file_id);
              $(element).append("Not found");
            },
            on_complete() {
              $("i", element).remove();
            }
          });
      });
      window.scroll(0, find_y_pos(row));
      var meta_url = $row.data('metaurl');
      if(meta_url && add_history) {
        window.history.pushState({'path': meta_url, }, null, "#"+meta_url);
      }
  }

  function init_details() {
      $(".dynamic_details").hide();

      window.addEventListener('popstate', function(e){
        if ((e.state == null) || (e.state.path == "")){
            if(window.location.hash.length > 1) {
              show_details($('.clickable-row[data-metaurl="'+window.location.hash.substr(1)+'"]').get(0));
            }
            else {
              close_details();
            }
        }
        else {
            show_details($('.clickable-row[data-metaurl="'+e.state.path+'"]'));
        }
      });
      if(window.location.hash.length > 1) {
        show_details($('.clickable-row[data-metaurl="'+window.location.hash.substr(1)+'"]').get(0));
      }
  }

  init_details();

-->
</script>

<?php
$this->end();
?>
