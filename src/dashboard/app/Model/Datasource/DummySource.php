<?php
class DummySource extends DataSource {
    // trick : https://bakery.cakephp.org/2012/01/19/Cakephp-V2-without-a-database-Fixed.html
    function connect() {
        $this->connected = true;
        return $this->connected;
    }

    function disconnect() {
        $this->connected = false;
        return !$this->connected;
    }

    function isConnected() {

        return true;
    }

}
