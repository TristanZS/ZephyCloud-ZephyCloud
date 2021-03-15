<div class="panel panel-flat">
  <div class="panel-heading">
    <h3 class="panel-title" ><b>Currencies</b></h3>
  </div>
  <div class="panel-body">
    <?php if (!empty($currencies)): ?>
      <table class="table table-bordered table-hover">
        <thead>
          <tr>
            <th>Name</th>
            <th>Ratio</th>
            <th style="width:180px;">Action</th>
          </tr>
        </thead>
        <tbody>
          <?php foreach ($currencies as $currency_name => $value): ?>
            <tr>
              <td><?= $currency_name ?></a></td>
              <td><?= $value; ?></td>
              <td>
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
<?php
  $this->append('script_footer');
?>
<?php
  $this->end();
?>
