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


<?php echo $this->Form->create(false,array("class"=>"form-horizontal form-bordered")); ?>
  <div class="col-md-6 col-md-offset-3">
        <div class="panel panel-flat">
          <div class="panel-heading">
            <h3 class="panel-title" ><b>Cancel</b></h3>
          </div>
          <div class="panel-body">

                    <!-- Input Text : start -->
                      <div class="form-group">
                         <label class="control-label col-md-3 text-right strong">reason<span class="error-message">*</span></label>
                         <div class="col-md-9">
                           <?php echo $this->Form->input('reason', array('label'=>false, 'placeholder' => "reason",'class'=>'form-control')); ?>
                         </div>
                      </div>
                    <!-- Input Text : end -->
       
            <div class="col-md-12">
                <div class="text-center">
                          <button type="submit" class="btn btn-success">Confirm</button>
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












