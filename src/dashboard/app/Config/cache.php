<?php

/**
 * Cache Engine Configuration
 * Default settings provided below
 *
 * File storage engine.
 *
 *     Cache::config('default', array(
 *        'engine' => 'File', //[required]
 *        'duration' => 3600, //[optional]
 *        'probability' => 100, //[optional]
 *        'path' => CACHE, //[optional] use system tmp directory - remember to use absolute path
 *        'prefix' => 'cake_', //[optional]  prefix every cache file with this string
 *        'lock' => false, //[optional]  use file locking
 *        'serialize' => true, //[optional]
 *        'mask' => 0664, //[optional]
 *    ));
 *
 * APC (http://pecl.php.net/package/APC)
 *
 *     Cache::config('default', array(
 *        'engine' => 'Apc', //[required]
 *        'duration' => 3600, //[optional]
 *        'probability' => 100, //[optional]
 *        'prefix' => Inflector::slug(APP_DIR) . '_', //[optional]  prefix every cache file with this string
 *    ));
 *
 * Xcache (http://xcache.lighttpd.net/)
 *
 *     Cache::config('default', array(
 *        'engine' => 'Xcache', //[required]
 *        'duration' => 3600, //[optional]
 *        'probability' => 100, //[optional]
 *        'prefix' => Inflector::slug(APP_DIR) . '_', //[optional] prefix every cache file with this string
 *        'user' => 'user', //user from xcache.admin.user settings
 *        'password' => 'password', //plaintext password (xcache.admin.pass)
 *    ));
 *
 * Memcached (http://www.danga.com/memcached/)
 *
 * Uses the memcached extension. See http://php.net/memcached
 *
 *     Cache::config('default', array(
 *        'engine' => 'Memcached', //[required]
 *        'duration' => 3600, //[optional]
 *        'probability' => 100, //[optional]
 *        'prefix' => Inflector::slug(APP_DIR) . '_', //[optional]  prefix every cache file with this string
 *        'servers' => array(
 *            '127.0.0.1:11211' // localhost, default port 11211
 *        ), //[optional]
 *        'persistent' => 'my_connection', // [optional] The name of the persistent connection.
 *        'compress' => false, // [optional] compress data in Memcached (slower, but uses less memory)
 *    ));
 *
 *  Wincache (http://php.net/wincache)
 *
 *     Cache::config('default', array(
 *        'engine' => 'Wincache', //[required]
 *        'duration' => 3600, //[optional]
 *        'probability' => 100, //[optional]
 *        'prefix' => Inflector::slug(APP_DIR) . '_', //[optional]  prefix every cache file with this string
 *    ));
 */

/**
 * Configure the cache handlers that CakePHP will use for internal
 * metadata like class maps, and model schema.
 *
 * By default File is used, but for improved performance you should use APC.
 *
 * Note: 'default' and other application caches should be configured in app/Config/bootstrap.php.
 *       Please check the comments in bootstrap.php for more info on the cache engines available
 *       and their settings.
 */
$engine = 'File';

// In development mode, caches should expire quickly.
$duration = '+999 days';
if (Configure::read('debug') > 0) {
    $duration = '+10 seconds';
}
$session_duration = "+2 hours";

// Prefix each application on the same server with a different string, to avoid Memcache and APC conflicts.
$prefix = API_NAME . '_';

/**
 * Configure the cache used for general framework caching. Path information,
 * object listings, and translation cache files are stored with this configuration.
 */

$persistent_folder = rtrim($cache_folder, DS) . DS . 'persistent' . DS;
if(!file_exists($persistent_folder)) {
    mkdir($persistent_folder, 0750, true);
}
Cache::config('_cake_core_', array(
    'engine' => $engine,
    'prefix' => $prefix . 'cake_core_',
    'path' => $persistent_folder,
    'serialize' => ($engine === 'File'),
    'duration' => $duration
));

/**
 * Configure the cache for model and datasource caches. This cache configuration
 * is used to store schema descriptions, and table listings in connections.
 */
$model_folder = rtrim($cache_folder, DS) . DS . 'models' . DS;
if(!file_exists($model_folder)) {
    mkdir($model_folder, 0750, true);
}
Cache::config('_cake_model_', array(
    'engine' => $engine,
    'prefix' => $prefix . 'cake_model_',
    'path' => $model_folder,
    'serialize' => ($engine === 'File'),
    'duration' => $duration
));

/**
 * Configure the cache for model and datasource caches. This cache configuration
 * is used to store schema descriptions, and table listings in connections.
 */
$session_folder = rtrim($session_folder, DS) . DS;
if(!file_exists($session_folder)) {
    mkdir($session_folder, 0750, true);
}
Cache::config('session', array(
    'engine' => $engine,
    'prefix' => $prefix . 'cake_session_',
    'path' => $session_folder,
    'serialize' => ($engine === 'File'),
    'duration' => $session_duration
));
