<?php echo $this->Form->create(false, ['type' => 'post',
                                       'url'=> $this->Html->url(array('plugin' => null,'controller' => 'zephy_cloud', 'action' => 'admin_providers_machines_update', 'providers_name' => $provider, 'machine_name' => $machine['name']), true),
                                       "class"=>"form-horizontal form-bordered"]); ?>
  <div class="col-md-6 col-md-offset-3">
    <div class="panel panel-flat">
      <div class="panel-heading">
        <h3 class="panel-title" ><b>Edit <?php echo $machine['name']; ?> machine of <?php echo $provider; ?></b></h3>
      </div>
      <div class="panel-body">
        <!-- Input Text : start -->
        <div class="form-group">
          <label class="control-label col-md-3 text-right strong">Number of cores<span class="error-message">*</span></label>
          <div class="col-md-9">
            <?php echo $this->Form->input('cores', array('label'=>false, 'placeholder' => "Cores",'class'=>'form-control', 'type'=> "number", "min" => 1)); ?>
          </div>
        </div>
        <!-- Input Text : end -->

        <!-- Input Text : start -->
        <div class="form-group">
           <label class="control-label col-md-3 text-right strong">Ram (in bytes)<span class="error-message">*</span></label>
           <div class="col-md-9">
             <?php echo $this->Form->input('ram', array('label'=>false, 'placeholder' => "Ram",'class'=>'form-control', 'type'=> "number", "min" => 1024)); ?>
           </div>
        </div>
        <!-- Input Text : end -->

        <!-- Input Text : start -->
        <div class="form-group">
           <label class="control-label col-md-3 text-right strong">Available machines<span class="error-message">*</span></label>
           <div class="col-md-9">
             <?php echo $this->Form->input('availability', array('label'=>false, 'placeholder' => "Availability",'class'=>'form-control', 'type'=> "number", "min" => 1)); ?>
           </div>
        </div>
        <!-- Input Text : end -->

        <hr />
        <h4>Provider Cost</h4>
        <!-- Input Text : start -->
        <div class="form-group">
          <label class="control-label col-md-3 text-right strong">Currency<span class="error-message">*</span></label>
          <div class="col-md-9">
            <?php
              $allowed_currency = array();
              foreach($pricing['currency_to_euro'] as $currency => $rate) {
                $allowed_currency[$currency] = $currency;
              }
              echo $this->Form->input('cost_currency', [
                  'label'=>false,
                  'options' => $allowed_currency,
                  'data-placeholder' => 'Provider currency',
                  'class' => 'form-control',
                  'required' => 'required',
                  'default' => $pricing['default_cost_currency']
              ]);
            ?>
           </div>
        </div>
        <!-- Input Text : end -->

        <!-- Input Text : start -->
        <div class="form-group">
          <label class="control-label col-md-3 text-right strong">Cost per hour<span class="error-message">*</span></label>
          <div class="col-md-9">
            <?php echo $this->Form->input('cost_per_hour', array('label'=>false, 'placeholder' => "Cost per hour",'class'=>'form-control', 'type'=> "number", 'step' => "any", 'min' => 0)); ?>
          </div>
        </div>
        <!-- Input Text : end -->

        <!-- Input Text : start -->
        <div class="form-group">
          <label class="control-label col-md-3 text-right strong">Time granularity<span class="error-message">*</span><br/>(in seconds)</label>
          <div class="col-md-9">
            <?php echo $this->Form->input('cost_sec_granularity', array('label'=>false, 'placeholder' => "Cost sec granularity",'class'=>'form-control', 'default' => $pricing['default_cost_sec_granularity'], 'type'=> "number", "min" => 1)); ?>
          </div>
        </div>
        <!-- Input Text : end -->


        <!-- Input Text : start -->
        <div class="form-group">
          <label class="control-label col-md-3 text-right strong">Minimum time<span class="error-message">*</span><br/>(in seconds)</label>
          <div class="col-md-9">
            <?php echo $this->Form->input('cost_min_sec_granularity', array('label'=>false, 'placeholder' => "Cost min sec granularity",'class'=>'form-control', 'default' => $pricing['default_cost_min_sec_granularity'], 'type'=> "number", "min" => 1)); ?>
          </div>
        </div>
        <!-- Input Text : end -->

        <hr/>
        <h4>Pricing</h4>

        <!-- Input Text : start -->
        <div class="form-group">
          <label class="control-label col-md-3 text-right strong" for="auto_update">Auto update prices<br/></label>
          <div class="col-md-9">
            <?php echo $this->Form->input('auto_update', array('label'=>false, 'type'=>'checkbox', 'default' => $pricing['auto_update'])); ?>
          </div>
        </div>
        <!-- Input Text : end -->

        <!-- Input Text : start -->
        <div class="form-group">
          <label class="control-label col-md-3 text-right strong">Time granularity<span class="error-message">*</span><br/>(in seconds)</label>
          <div class="col-md-9">
            <?php echo $this->Form->input('price_sec_granularity', array('label'=>false, 'placeholder' => "Price sec granularity",'class'=>'form-control', 'type'=> "number", "min" => 1, "default" => $pricing['default_price_sec_granularity'])); ?>
          </div>
        </div>
        <!-- Input Text : end -->


        <!-- Input Text : start -->
        <div class="form-group">
          <label class="control-label col-md-3 text-right strong">Minimum time<span class="error-message">*</span><br/>(in seconds)</label>
          <div class="col-md-9">
            <?php echo $this->Form->input('price_min_sec_granularity', array('label'=>false, 'placeholder' => "Price min sec granularity",'class'=>'form-control', 'type'=> "number", "min" => 1, "default" => $pricing['default_price_min_sec_granularity'])); ?>
          </div>
        </div>
        <!-- Input Text : end -->

        <?php foreach(array('root', 'gold', 'silver', 'bronze') as $rank): ?>
          <!-- Input Text : start -->
          <div class="form-group">
            <label class="control-label col-md-3 text-right strong">Price for <?php echo $rank; ?> users<span class="error-message">*</span><br/>(in zephycoins/hour)</label>
            <div class="col-md-9">
              <?php echo $this->Form->input('prices_'.$rank, array('label'=>false, 'placeholder' => "Prices for ".$rank." users",'class'=>'form-control', 'type'=> "number", 'step' => "any", "min" => 0)); ?>
            </div>
          </div>
          <!-- Input Text : end -->
        <?php endforeach ?>

        <!-- Input Text : end -->
        <div class="btn-group">
          <button id="auto_price" class="btn btn-primary btn-sm" disabled="disabled" type="button">Calculate prices</button>
          <a id="auto_price_details" class="btn btn-primary btn-sm open-PricingDetails" data-toggle="modal" data-target="#PricingDetails"><i class="icon-cog5"></i></a>
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

<div id="PricingDetails" tabindex="-1" role="dialog" class="modal fade">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h3>Pricing details:</h3>
        <button type="button" class="close" data-dismiss="modal">
          <span aria-hidden="true">×</span>
          <span class="sr-only">Close</span>
        </button>
      </div>
      <div class="modal-body">
        <form class="form-horizontal">
          <div class="form-group">
            <label class="control-label col-md-5 text-right strong">Security margin</label>
            <div class="col-md-7">
              <input name="pricing_security_margin" id="pricing_security_margin" type="number" step="any" min="0"></input>
            </div>
          </div>

          <div class="form-group">
            <label class="control-label col-md-5 text-right strong">OpenFOAM donation ratio</label>
            <div class="col-md-7">
              <input name="pricing_openfoam" id="pricing_openfoam" type="number" step="any" min="0"></input>
            </div>
          </div>

          <div class="form-group">
            <label class="control-label col-md-5 text-right strong">Zephycoin price in <?php echo $pricing['default_currency']; ?></label>
            <div class="col-md-7">
              <input name="pricing_zephycoin_price" id="pricing_zephycoin_price" type="number" step="any" min="0"></input>
            </div>
          </div>

          <h5>Margin per rank</h5>
          <?php foreach(array('gold', 'silver', 'bronze') as $rank): ?>
            <div class="form-group">
              <label class="control-label col-md-5 text-right strong">Margin for <?php echo $rank; ?> users</label>
              <div class="col-md-7">
                <input name="pricing_rank_<?php echo $rank; ?>" id="pricing_rank_<?php echo $rank; ?>" type="number" step="any" min="1"></input>
              </div>
            </div>
          <?php endforeach ?>

          <h5>Currency conversion rates to euro</h5>
          <?php foreach($pricing['currency_to_euro'] as $currency => $unused): ?>
            <?php if($currency != "euro"): ?>
              <div class="form-group">
                <label class="control-label col-md-5 text-right strong"><?php echo $currency; ?></label>
                <div class="col-md-7">
                  <input name="pricing_currency_rate_<?php echo $currency; ?>" id="pricing_currency_rate_<?php echo $currency; ?>" type="number" step="any" min="0"></input>
                </div>
              </div>
            <?php endif ?>
          <?php endforeach ?>
        </form>
      </div>
      <div class="modal-footer">
        <div class="m-t-lg">
          <a class="btn btn-success validate" href="#" id="save_details">Apply</a>
          <button class="btn btn-default" data-dismiss="modal" type="button">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</div>
<script>
  <!--
  var pricing = {
    "security_margin": <?php echo $pricing['security_margin']; ?>,
    "openfoam": <?php echo $pricing['openfoam_donations']; ?>,
    "zephycoin_price": <?php echo $pricing['zephycoin_price']; ?>,
    <?php foreach(array('gold', 'silver', 'bronze') as $rank): ?>
      "rank_<?php echo $rank;?>": <?php echo $pricing['margins'][$rank]; ?>,
    <?php endforeach ?>
    <?php foreach($pricing['currency_to_euro'] as $currency => $rate): ?>
      "currency_rate_<?php echo $currency?>": <?php echo $rate; ?>,
    <?php endforeach ?>
  };

  function update_auto_price_btn_status() {
    var price = $('#cost_per_hour').val();
    if(isNaN(price) || (price <= 0)) {
      $("#auto_price").prop('disabled', true);
    }
    else {
      $("#auto_price").prop('disabled', false);
    }
  }

  $('#cost_per_hour').change(function() {
    update_auto_price_btn_status();
  });

  $('#auto_price').click(function() {
    var price = $('#cost_per_hour').val();
    if(isNaN(price) || (price <= 0)) {
      update_auto_price_btn_status();
      return;
    }
    price = parseFloat(price);
    var cost_currency = $('#cost_currency').val();
    var rate = pricing['currency_rate_'+cost_currency] / pricing['currency_rate_<?php echo $pricing['default_currency'];?>'] / pricing['zephycoin_price'];
    var ref_price = price * (1.0 + pricing['security_margin'] + pricing['openfoam']);
    $("#prices_root").val(ref_price * rate);
    <?php foreach(array('gold', 'silver', 'bronze') as $rank): ?>
      $("#prices_<?php echo $rank; ?>").val(ref_price * rate * pricing['rank_<?php echo $rank; ?>']);
    <?php endforeach ?>
  });

  $('#PricingDetails').on('show.bs.modal', function (event) {
    var modal = $(this);
    modal.find("#pricing_security_margin").val(pricing['security_margin']);
    modal.find("#pricing_openfoam").val(pricing['openfoam']);
    modal.find("#pricing_zephycoin_price").val(pricing['zephycoin_price']);
    <?php foreach(array('gold', 'silver', 'bronze') as $rank): ?>
      modal.find("#pricing_rank_<?php echo $rank;?>").val(pricing['rank_<?php echo $rank; ?>']);
    <?php endforeach ?>
    <?php foreach($pricing['currency_to_euro'] as $currency => $unused): ?>
      <?php if($currency != "euro"): ?>
        modal.find("#pricing_currency_rate_<?php echo $currency;?>").val(pricing['currency_rate_<?php echo $currency; ?>']);
      <?php endif ?>
    <?php endforeach ?>
  })

  $('#PricingDetails').find(".validate").on("click", function () {
    var modal = $('#PricingDetails');
    modal.modal('hide');
    pricing['security_margin'] = parseFloat(modal.find("#pricing_security_margin").val());
    pricing['openfoam'] = parseFloat(modal.find("#pricing_openfoam").val());
    pricing['zephycoin_price'] = parseFloat(modal.find("#pricing_zephycoin_price").val());
    <?php foreach(array('gold', 'silver', 'bronze') as $rank): ?>
      pricing['rank_<?php echo $rank; ?>'] = parseFloat(modal.find("#pricing_rank_<?php echo $rank;?>").val());
    <?php endforeach ?>
    <?php foreach($pricing['currency_to_euro'] as $currency => $unused): ?>
      <?php if($currency != "euro"): ?>
        pricing['currency_rate_<?php echo $currency; ?>'] = parseFloat(modal.find("#pricing_currency_rate_<?php echo $currency;?>").val());
      <?php endif ?>
    <?php endforeach ?>

    event.preventDefault();
    return false;
  });

  update_auto_price_btn_status();
  -->
</script>


<?php
$this->append('script_footer');
?>

<?php
$this->end();
?>












