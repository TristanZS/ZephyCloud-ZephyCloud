<?php if (!empty($error_msgs)): ?>
  <div class="col-md-6 col-md-offset-3">
        <div class="panel panel-flat">
          <div class="panel-heading">
            <h3 class="panel-title" ><b>Errors messages</b></h3>
          </div>
          <div class="panel-body">
              <?php foreach ($error_msgs as $error_msg): ?>
                <div style="color:red;font-weight:bold;"><li><?php echo $error_msg ?></li></div>
              <?php endforeach ?>
          </div>
        </div>
  </div>
<?php endif ?>

<?php echo $this->Form->create(false, ["type" => "post", "class"=>"form-horizontal form-bordered",
                                       "url" => $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_toolchains_update', 'toolchain_name' => $toolchains['name']), true)]); ?>
  <div class="col-md-6 col-md-offset-3">
        <div class="panel panel-flat">
          <div class="panel-heading">
            <h3 class="panel-title" ><b>Edit <?php echo $toolchains["name"]; ?> Toolchain</b></h3>
          </div>
          <div class="panel-body">

              <h4>General information:</h4>

                    <!-- Input Text : start -->
                      <div class="form-group">
                         <label class="control-label col-md-3 text-right strong">Fixed price<span class="error-message">*</span><br/>(in zephycoins/week)</label>
                         <div class="col-md-9">
                           <?php echo $this->Form->input('fixed_price', array('label'=>false, 'placeholder' => "Fixed price",'class'=>'form-control', 'type'=> "number", "min" => 0, "step" => "any")); ?>
                         </div>
                      </div>
                    <!-- Input Text : end -->


                    <!-- Input Text : start -->
                      <div class="form-group">
                         <label class="control-label col-md-3 text-right strong">Machine limit<span class="error-message">*</span></label>
                         <div class="col-md-9">
                           <?php echo $this->Form->input('machine_limit', array('label'=>false, 'placeholder' => "machine_limit",'class'=>'form-control', 'type'=> "number", "min" => 1)); ?>
                         </div>
                      </div>
                    <!-- Input Text : end -->

              <h4>Allowed machines:</h4>
              <div style="padding-left: 25px; ">
                  <?php foreach($all_machines as $provider => $machine_list): ?>
                    <div class="form-group">
                      <label class="display-block text-semibold"><?php echo $provider; ?></label>
                      <?php foreach($machine_list as $machine): ?>
                        <div class="custom-control custom-checkbox" style="padding-left:15px;">
                            <?php echo $this->Form->checkbox('machines.'.$provider.".", array('div' => false, 'hiddenField' => false, 'label'=>false,
                                                                'id' => "machines_".$provider.'_'.$machine,
                                                                'class' =>'custom-control-input',
                                                                'value' => $machine,
                                                                'checked' => in_array($machine, $this->request->data['machines'][$provider])
                                                                )); ?>
                            <label class="custom-control-label" for="machines_<?php echo $provider.'_'.$machine; ?>"><?php echo $machine; ?></label>
                        </div>
                      <?php endforeach ?>
                    </div>
                  <?php endforeach ?>
              </div>
            <div class="col-md-12">
                <div class="text-center">
                    <button type="submit" class="btn btn-success">Save changes</button>
                </div>
            </div>

          </div>
        </div>
  </div>
<?php echo $this->Form->end(); ?>

<?php
$this->append('script_footer');
?>

<?php
$this->end();
?>












