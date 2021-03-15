<?php if ($this->Paginator->param('pageCount') > 1): ?>

	<div class="row">
		<div class="col-md-12">
			<div align="center">
				<ul class="pagination">
<?php
	$named = array();
	$pass = array();
	if(!empty($this->params['named'])){
		$named = $this->params['named'];
	}
	if(!empty($this->params['pass'])){
		$pass = $this->params['pass'];
	}

	$query_params = array_merge($named,$pass);
	$this->Paginator->options(array(
	  								'url' => array('plugin' => null,'controller' => $this->request->params["controller"], 'action' => $this->request->params["action"],'?' => $query_params),
	));
?>




				<?php
	 				
					//echo $this->Paginator->numbers(array('separator'=>false));
				    echo $this->Paginator->first('&lsaquo;', array('tag' => 'li', 'title' => __('Première page'), 'escape' => false));
				    echo $this->Paginator->prev('&laquo;', array('tag' => 'li',  'title' => __('précédente'), 'disabledTag' => 'span', 'escape' => false), null, array('tag' => 'li', 'disabledTag' => 'span', 'escape' => false, 'class' => 'disabled'));
				    echo $this->Paginator->numbers(array('separator' => false, 'tag' => 'li', 'currentTag' => 'span', 'currentClass' => 'active'));
				    echo $this->Paginator->next('&raquo;', array('tag' => 'li', 'disabledTag' => 'span', 'title' => __('Suivante'), 'escape' => false), null, array('tag' => 'li', 'disabledTag' => 'span', 'escape' => false, 'class' => 'disabled'));
				    echo $this->Paginator->last('&rsaquo;', array('tag' => 'li', 'title' => __('Dernière page'), 'escape' => false));
				?>
				</ul>
			</div>
		</div>
	</div>
	
<?php endif ?>
