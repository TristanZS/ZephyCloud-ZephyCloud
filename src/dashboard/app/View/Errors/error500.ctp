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
 * @package       app.View.Errors
 * @since         CakePHP(tm) v 0.10.0.1076
 * @license       https://opensource.org/licenses/mit-license.php MIT License
 */
?>

<?php
if (Configure::read('debug') > 0):
?>
	<h2><?php echo $message; ?></h2>
	<p class="error">
		<strong><?php echo __d('cake', 'Error'); ?>: </strong>
		<?php echo __d('cake', 'An Internal Error Has Occurred.'); ?>
	</p>
	<?php
	echo $this->element('exception_stack_trace');
?>
<?php else: ?>
<div align='center'>
<h1 style="font-size: 52px;font-weight: bold;">ERROR ! </h1>
<h2><?php //echo $message; ?>Message : <i><?php echo $error->getMessage(); ?></i></h2>
<br><br>
<img class="img-responsive" src="<?php echo $this->Html->url("/", true); ?>images/errorpicture.png" alt="Error">

</div>
<?php endif ?>
<!--
   - Unfortunately, Microsoft has added a clever new
   - "feature" to Internet Explorer. If the text of
   - an error's message is "too small", specifically
   - less than 512 bytes, Internet Explorer returns
   - its own error message. You can turn that off,
   - but it's pretty tricky to find switch called
   - "smart error messages". That means, of course,
   - that short error messages are censored by default.
   - IIS always returns error messages that are long
   - enough to make Internet Explorer happy. The
   - workaround is pretty simple: pad the error
   - message with a big comment like this to push it
   - over the five hundred and twelve bytes minimum.
   - Of course, that's exactly what you're reading
   - right now.
   -->

