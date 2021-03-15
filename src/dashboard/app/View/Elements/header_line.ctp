
          <div class="breadcrumb-line bg-transparent">
            <ul class="breadcrumb bg-transparent">
              <li><a href="<?php echo $this->Html->url(array('plugin' => null,'controller' => 'home', 'action' => 'index')); ?>"><i class="icon-home2 position-left"></i> Home</a></li>
                <?php
                if (!empty($breadcrumb_array)) {
                  $lastElement = end($breadcrumb_array);
                  $lastElementKey = key($breadcrumb_array);
                  foreach($breadcrumb_array as $breadcrumb_key=>$breadcrumb_value) {
                      if($breadcrumb_key == $lastElementKey) {
                          echo '<li class="active">'.$breadcrumb_value["text"].'</li>';
                      }else{
                        echo '<li><a href="'.$breadcrumb_value["url"].'">'.$breadcrumb_value["text"].'</a></li>';
                      }
                  }
                }
                ?>

            </ul>

            <ul class="breadcrumb-elements">
              <li>
                <?php if(($time_machine_time == null) || !$time_machine_enabled): ?>
                  <button type="button" class="btn btn-icon btn-flat time-machine" <?php echo $time_machine_enabled ? "" : 'disabled="disabled"'; ?> ><i class="icon-history"></i></button>
                <?php else: ?>
                  <button type="button" class="btn btn-xs btn-danger btn-icon time-machine"><i class="icon-history"></i> <span><?php echo AziugoTools::human_date($time_machine_time); ?></span></button>
                <?php endif; ?>
              </li>
            </ul>
            <ul class="breadcrumb-elements">
              <li>
                <?php echo $this->Form->input('search_text', array('label'=>false, 'placeholder' => "Name search",'class'=>'form-control', "style"=>"margin-top: 5px; height: 2em;")); ?>
              </li>
            </ul>
          </div>
