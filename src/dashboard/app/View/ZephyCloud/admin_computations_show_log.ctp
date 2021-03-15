
    <div class="row">
      <div class="col-md-12">
        <!-- Titre debut -->
        <div class="panel panel-flat">
          <div class="panel-heading">
            <h3 class="panel-title"><b>Logs</b></h3>
          </div>
          <div class="panel-body">
                  <pre><?php echo str_replace("ERROR", '<span style="color:red;font-weight: bold">ERROR</span>', $logs)  ; ?></pre>
          </div>
        </div>
      </div>
    </div>

<?php
$this->append('script_footer'); 
?>

<?php
$this->end(); 
?>
