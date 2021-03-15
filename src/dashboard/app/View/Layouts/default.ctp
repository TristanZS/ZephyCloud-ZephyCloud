<!DOCTYPE html>
<html lang="en">
<head>
 <!--  <meta charset="utf-8"> -->
  <?php echo $this->Html->charset(); ?>
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Aziugo Dashboard <?php echo (!empty($page_title))?" - " . $page_title:""; ?></title>

  <!-- Global stylesheets -->
  <link href="https://fonts.googleapis.com/css?family=Roboto:400,300,100,500,700,900" rel="stylesheet" type="text/css">
  <link href="<?php echo $this->Html->url('/', true); ?>css/icons/icomoon/styles.css" rel="stylesheet" type="text/css">
  <link href="<?php echo $this->Html->url('/', true); ?>css/bootstrap.min.css" rel="stylesheet" type="text/css">
  <link href="<?php echo $this->Html->url('/', true); ?>css/core.min.css" rel="stylesheet" type="text/css">
  <link href="<?php echo $this->Html->url('/', true); ?>css/components.min.css" rel="stylesheet" type="text/css">
  <link href="<?php echo $this->Html->url('/', true); ?>css/colors.min.css" rel="stylesheet" type="text/css">
  <link href="<?php echo $this->Html->url('/', true); ?>css/jquery-ui.min.css" rel="stylesheet" type="text/css">
  <link href="<?php echo $this->Html->url('/', true); ?>css/jquery-ui.structure.min.css" rel="stylesheet" type="text/css">
  <link href="<?php echo $this->Html->url('/', true); ?>css/custom.css" rel="stylesheet" type="text/css">

  <!-- Core JS files -->
  <script type="text/javascript" src="<?php echo $this->Html->url('/', true); ?>js/core/libraries/jquery.min.js"></script>
  <script type="text/javascript" src="<?php echo $this->Html->url('/', true); ?>js/core/libraries/jquery-ui.min.js"></script>
  <script type="text/javascript" src="<?php echo $this->Html->url('/', true); ?>js/core/libraries/bootstrap.min.js"></script>
  <!-- /core JS files -->

  <!-- Theme JS files -->
  <script type="text/javascript" src="<?php echo $this->Html->url('/', true); ?>js/core/app.min.js"></script>
  <!-- /theme JS files -->

  <script type="text/javascript" src="<?php echo $this->Html->url('/', true); ?>js/custom.js"></script>

  <!-- Time picker requirements -->
  <script src="<?php echo $this->Html->url('/', true); ?>js/core/libraries/moment.min.js"></script>
  <script src="<?php echo $this->Html->url('/', true); ?>js/core/libraries/daterangepicker-2.1.25.js"></script>
  <!-- /Time picker requirements -->

  <?php
      echo $this->fetch('meta');
      echo $this->fetch('css');
      echo $this->fetch('script');
      echo $this->fetch('script_header');
  ?>
  <style>
    .ui-autocomplete-loading {
      background: white url("<?php echo $this->Html->url('/', true); ?>images/ui-anim_basic_16x16.gif") right center no-repeat;
    }

    .back-to-the-future {
      background: url("<?php echo $this->Html->url('/', true); ?>images/past.svg");
    }
  </style>
</head>

<body class="has-detached-left">

  <div id="loading-overlay" class="overlay hidden">
    <div class="overlay-content">
      <img src="<?php echo $this->Html->url('/', true); ?>images/big_loader.gif" width="128" height="128" alt="loader"/>
    </div>
  </div>

  <!-- Main navbar -->
  <div class="navbar navbar-inverse">
    <div class="navbar-header">
      <a  href="<?php echo $this->Html->url('/', true); ?>"><img src="<?php echo $this->Html->url('/', true); ?>images/logo_light.png" alt="" style="padding: 8px 25px;"></a>

      <ul class="nav navbar-nav visible-xs-block">
        <li><a data-toggle="collapse" data-target="#navbar-mobile"><i class="icon-tree5"></i></a></li>
        <li><a class="sidebar-mobile-main-toggle"><i class="icon-paragraph-justify3"></i></a></li>
      </ul>
    </div>

    <div class="navbar-collapse collapse" id="navbar-mobile">
      <ul class="nav navbar-nav" style="margin-left: 0px!important; ">
        <li><a class="sidebar-control sidebar-main-toggle hidden-xs"><i class="icon-paragraph-justify3"></i></a></li>
      </ul>

      <ul class="nav navbar-nav navbar-right" style="margin-left: 0px!important; ">
      </ul>
    </div>
  </div>
  <!-- /main navbar -->


  <!-- Page container -->
  <div class="page-container">

    <!-- Page content -->
    <div class="page-content">

      <!-- Main sidebar -->
      <div class="sidebar sidebar-main">
        <div class="sidebar-content">
              <?php //echo $this->element('menu_users_info', array()); ?>
              <?php echo $this->element('menu', array()); ?>

        </div>
      </div>
      <!-- /main sidebar -->



      <!-- Main content -->
      <?php if(($time_machine_time == null) || !$time_machine_enabled): ?>
        <div class="content-wrapper">
      <?php else: ?>
        <div class="content-wrapper back-to-the-future">
      <?php endif ?>



        <!-- Page header -->
        <div class="page-header page-header-default">
          <?php echo $this->element('header_line', array()); ?>
        </div>
        <!-- /page header -->

        <div class="flash-container">
          <?php echo $this->Flash->render(); ?>
        </div>

        <!-- Content area -->
        <div class="content">
            <?php echo $this->fetch('content'); ?>
        </div>
        <!-- /content area -->

      </div>
      <!-- /main content -->

    </div>
    <!-- /page content -->

  </div>
  <!-- /page container -->

<?php echo $this->fetch('script_footer'); ?>
<?php echo $this->fetch('html_modal_footer'); ?>
    <script type="text/javascript">
      (function ($) {
        'use strict';
            $('*[data-plugin="select2"]').each(function(i){
                $(this).select2();
            });
      })(jQuery);
    </script>


<script>
$(document).on("click", ".open-DeleteConfirmation", function () {
     var myUrl = $(this).data('url');
     $(".modal-body #UrlConfirm").attr("href", myUrl);
});
$(".nojs-hide").show();
</script>

    <div id="DeleteConfirmation" tabindex="-1" role="dialog" class="modal fade">
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
              <p>Are you sure you want to remove this?</p>
              <div class="m-t-lg">
                <a class="btn btn-danger" href="#" id="UrlConfirm">Yes, Delete it!</a>
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
  $(document).ready(function(){
      $.widget( "custom.catcomplete", $.ui.autocomplete, {
        _create: function() {
          this._super();
          this.widget().menu( "option", "items", "> :not(.search-category)" );
        },
        _renderMenu: function( ul, items ) {
          var that = this;
          var currentCategory = "";
          $.each( items, function( index, item ) {
            var li;
            if ( item.category != currentCategory ) {
              ul.append( "<li class='search-category'>" + item.category + "</li>" );
              currentCategory = item.category;
            }
            li = that._renderItemData( ul, item );
            if ( item.category ) {
              li.attr( "aria-label", item.category + " : " + item.label );
            }
          });
        }
      });

      $('#search_text').catcomplete({
        source: function(request, response){
          $.ajax({
            url: <?php echo json_encode($this->Html->url(array('plugin' => null, 'controller' => 'zephy_cloud', 'action' => 'admin_search'))); ?>,
            type: 'GET',
            data: { "term": request.term },
            dataType: 'json',
            headers: {
              "Accept": "application/json",
              "Content-Type": "application/json"
            },
            success: function(req_result) {
              response(req_result.data);
            }
          });
        },
        minLength: 2,
        select: function( event, ui ) {
          window.location.href =(ui.item.url);
        }
      });
  });
  -->
</script>
</body>
</html>
