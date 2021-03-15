<?php if(empty($params["options"])){
		$params["options"] = array();
	  }
?>
<script>
  var title = '<?php echo addslashes($params["title"]);?>';
  var message = '<?php echo addslashes($message); ?>';
  var type    = '<?php echo addslashes($params["type"]); ?>';
  var options = <?php echo json_encode($params["options"]); ?>;
toastr[type](message, title, options);
</script>

