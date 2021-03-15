<?php
/**
 * CakePHP(tm) : Rapid Development Framework (https://cakephp.org)
 * Copyright (c) Cake Software Foundation, Inc. (https://cakefoundation.org)
 *
 * Licensed under The MIT License
 * For full copyright and license information, please see the LICENSE.txt
 * Redistributions of files must retain the above copyright notice.
 *
 * @copyright     Copyright (c) Cake Software Foundation, Inc. (https://cakefoundation.org)
 * @link          https://cakephp.org CakePHP(tm) Project
 * @package       app.View.Layouts
 * @since         CakePHP(tm) v 0.10.0.1076
 * @license       https://opensource.org/licenses/mit-license.php MIT License
 */

$cakeDescription = __d('cake_dev', 'CakePHP: the rapid development php framework');
?>
<!DOCTYPE html>
<html lang="en">
<head>
 <!--  <meta charset="utf-8"> -->
  <?php echo $this->Html->charset(); ?>
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Aziugo Dashboard <?php echo (!empty($page_title))?" - " . $page_title:"Internal error"; ?></title>
	<?php
		echo $this->fetch('meta');
		echo $this->fetch('css');
		echo $this->fetch('script');
	?>
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
</head>
<body>
	<div id="container">
		<div id="content">
			<?php echo $this->fetch('content'); ?>
		</div>
	</div>
	<?php echo $this->element('sql_dump'); ?>
</body>
</html>
