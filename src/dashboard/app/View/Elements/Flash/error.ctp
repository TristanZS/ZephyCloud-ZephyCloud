<div class="alert alert-danger bg-light text-default alert-styled-left alert-arrow-left alert-dismissible">
  <button type="button" class="close" data-dismiss="alert"><span>×</span></button>
  <?php if(isset($params['title'])): ?>
    <h6 class="alert-heading font-weight-semibold mb-1"><?php echo h($params['title']); ?></h6>
  <?php endif ?>
  <?php echo h($message); ?>
</div>
