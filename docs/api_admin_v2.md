# API admin v2

# API admin: Common information

This API replace the admin API v1

All API calls are located on https://api.zephy-science.com/admin/

The authentication is done using Basic Auth.

Some generic rules about the requests: 
* All requests should be done via https
* All requests should be json requests.
* All requests sending files should call the file argument **files[]**
* All requests should call a trailing slash url (like a folder address)
* All request require admin user credentials.

Those credentials are located here: https://dashboard.aziugo.com/api/users/secrets/data/slug/zephycloud-admin-api.html

All responses should have the following structure, even in case of error:

```json
{
    "success": 1,
    "error_msgs": ["List of error messages, or empty array in case of success"],
    "data": "Whatever data. Could be int, string, array or object"
}
```

In case of list response, an additional field called **total** can be present, containing the total count of the list if it is paginated
ex:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": [...],
    "total": 53
}
```




# Providers

## list

* **description**: Get all available providers:
* **url**: ```https://api.zephy-science.com/admin/providers/list/```
* **method**: GET, POST
* **parameters**:
  * **limit**: int, OPTIONAL, only received a limited amount of jobs
  * **offset**: int, OPTIONAL, skip the first jobs from the list
  * **order**: string, OPTIONAL, an SQL like formatted string to sort the results. Ex: `status ASC, job_id DESC`). The allowed order fields are:
     * **name**
     * **location**
     * **type**
* **response**: Array of object, with fields:
  * **name**: String, the name of the provider
  * **location**: String, a geographic location of the provider
  * **type**: String, the kind of provider 
  * **provider_specific**: object: list of provider specific informations. Each provider have his own set of fields.
  * **aws** *provider_specific* fields:
     * **region**: String, the name of the region

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": [
       {
         "name": "aws_eu",
         "location": "eu",
         "type": "aws",
         "provider_specific": {
			"region": "eu-west-1"
         }
       },
       {
         "name": "aws_eu_spot",
         "location": "eu",
         "type": "aws_spot",
		  "provider_specific": {
			"region": "eu-west-1"
         }
       }
    ]
}
```

## list_all_machines

* **description**: List all existing machines
* **url**: ```https://api.zephy-science.com/admin/providers/list_all_machines/```
* **method**: GET, POST
* **parameters**: None
* **response**: An object with the provider (string) as key and a list of machine names (string) as value

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": {
       "aws_eu": [
          "c5.2xlarge", 
          "c5.9xlarge", 
          "c5.4xlarge", 
          "c5.xlarge", 
          "c5.18xlarge"
       ], 
       "aws_eu_old": [
          "c4.8xlarge", 
          "c4.xlarge", 
          "c4.2xlarge", 
          "c4.4xlarge", 
          "x1.16xlarge"
       ], 
       ....
    }
}
```

# Provider machines

## list

* **description**: List all available kinds of workers for a provider:
* **url**: ```https://api.zephy-science.com/admin/machines/list/```
* **method**: GET, POST
* **parameters**:
  * **provider_name**: String, the name of the provider
  * **date**: int, OPTIONAL, UTC timestamp, in seconds. Allow to see the result at a specific point in time
  * **limit**: int, OPTIONAL, only received a limited amount of jobs
  * **offset**: int, OPTIONAL, skip the first jobs from the list
  * **order**: string, OPTIONAL, an SQL like formatted string to sort the results. Ex: `name ASC, cores DESC`). The allowed order fields are:
     * **name**
     * **cores**
     * **ram**
     * **availability**
* **response**: Array of object, with fields:
  * **name**: String, the name of the machine. It should be uniq per provider
  * **cores**: int, the number of cores the worker have
  * **ram**: int, the amount of RAM the worker have, in bytes
  * **availability**: int, How many workers can we launch simultaneously
  * **prices**: An object with the rank (string) as key, and the cost per hour in zephycoins (float) as value
  * **price_sec_granularity**: int, the time slice, in seconds, used to charge the user
  * **price_min_sec_granularity**: int, the first time slice, in seconds, used to charge the user
  * **cost_per_hour**: float, how many money the provider charge us for using this worker
  * **cost_currency**: string, the currency the provider uses for charging us
  * **cost_sec_granularity**: int, the time slice, in seconds, the provider uses to charge us
  * **cost_min_sec_granularity**: int, the first time slice, in seconds, the provider uses to charge us
  * **auto_update**: bool, do we update automaticaly the price when currency exchange change or provider cost change ?

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": [
		{
			"name":"c5.xlarge",
			"cores": 4,
			"ram": 8589934592,
			"availability": 400,
			"prices":{
				"root": 0.19,
				"gold": 0.38,
				"silver": 0.76,
				"bronze": 1.9
			},
			"price_sec_granularity": 500,
			"price_min_sec_granularity": 500,
			"cost_per_hour": 0.025
			"cost_currency": "dollar",
			"cost_sec_granularity": 1,
			"cost_min_sec_granularity": 60,
			"auto_update": true
		},
		{
			"name":"c5.2xlarge",
			"cores":8,
			"ram":16,
			"availability":400,
			"prices":{
				"root":0.34,
				"gold":0.68,
				"silver":1.36,
				"bronze":3.40
			},
			"price_sec_granularity": 500,
			"price_min_sec_granularity": 500,
			"cost_per_hour": 0.051
			"cost_currency": "dollar",
			"cost_sec_granularity": 1,
			"cost_min_sec_granularity": 60,
			"auto_update": true
		},
    ]
}
```

## show

* **description**: List all available kinds of workers for a provider:
* **url**: ```https://api.zephy-science.com/admin/machines/show/```
* **method**: GET, POST
* **parameters**:
  * **provider_name**: String, the name of the provider
  * **machine_name**: String, the name of the machine
* **response**: An object, with fields:
  * **name**: String, the name of the machine. It should be uniq per provider
  * **cores**: int, the number of cores the worker have
  * **ram**: int, the amount of RAM the worker have, in bytes
  * **availability**: int, How many workers can we launch simultaneously
  * **prices**: An object with the rank (string) as key, and the cost per hour in zephycoins (float) as value
  * **price_sec_granularity**: int, the time slice, in seconds, used to charge the user
  * **price_min_sec_granularity**: int, the first time slice, in seconds, used to charge the user
  * **cost_per_hour**: float, how many money the provider charge us for using this worker
  * **cost_currency**: string, the currency the provider uses for charging us
  * **cost_sec_granularity**: int, the time slice, in seconds, the provider uses to charge us
  * **cost_min_sec_granularity**: int, the first time slice, in seconds, the provider uses to charge us
  * **auto_update**: bool, do we update automaticaly the price when currency exchange change or provider cost change ?

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": {
		"name":"c5.2xlarge",
		"cores":8,
		"ram":16,
		"availability":400,
		"prices":{
			"root":0.34,
			"gold":0.68,
			"silver":1.36,
			"bronze":3.40
		},
		"price_sec_granularity": 500,
		"price_min_sec_granularity": 500,
		"cost_per_hour": 0.051
		"cost_currency": "dollar",
		"cost_sec_granularity": 1,
		"cost_min_sec_granularity": 60,
		"auto_update": true
	}
}
```

## update

* **description**: Update an existing machine type
* **url**: ```https://api.zephy-science.com/admin/machines/update/```
* **method**: GET, POST
* **parameters**:
  * **provider_name**: String, the name of the provider
  * **machine_name**: String, the name of the machine. It should be unique per provider
* **optional parameters**: At least one of the following:
  * **cores**: int, the number of cores the worker have
  * **ram**: int, the amount of RAM the worker have, in bytes
  * **availability**: int, How many workers can we launch simultaneously
  * **prices**: An object with the rank (string) as key, and the cost per hour in zephycoins (float) as value
  * **price_sec_granularity**: int, the time slice, in seconds, used to charge the user
  * **price_min_sec_granularity**: int, the first time slice, in seconds, used to charge the user
  * **cost_per_hour**: float, how many money the provider charge us for using this worker
  * **cost_currency**: string, the currency the provider uses for charging us
  * **cost_sec_granularity**: int, the time slice, in seconds, the provider uses to charge us
  * **cost_min_sec_granularity**: int, the first time slice, in seconds, the provider uses to charge us
  * **auto_update**: bool, do we update automaticaly the price when currency exchange change or provider cost change ?
* **response**: Nothing

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": "ok"
}
```

## create

* **description**: Create a new machine type
* **url**: ```https://api.zephy-science.com/admin/machines/create/```
* **method**: GET, POST
* **parameters**:
  * **provider_name**: String, the name of the provider
  * **machine_name**: String, the name of the machine. It should be unique per provider
  * **cores**: int, the number of cores the worker have
  * **ram**: int, the amount of RAM the worker have, in bytes
  * **availability**: int, How many workers can we launch simultaneously
  * **prices**: An object with the rank (string) as key, and the cost per hour in zephycoins (float) as value
  * **price_sec_granularity**: int, the time slice, in seconds, used to charge the user
  * **price_min_sec_granularity**: int, the first time slice, in seconds, used to charge the user
  * **cost_per_hour**: float, how many money the provider charge us for using this worker
  * **cost_currency**: string, the currency the provider uses for charging us
  * **cost_sec_granularity**: int, the time slice, in seconds, the provider uses to charge us
  * **cost_min_sec_granularity**: int, the first time slice, in seconds, the provider uses to charge us
  * **auto_update**: bool, Do we change the price when currency exchange rates changes or provider change it's price ?
* **response**: Nothing

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": "ok"
}
```

## remove

* **description**: Remove an existing machine type
* **url**: ```https://api.zephy-science.com/admin/machines/remove/```
* **method**: GET, POST
* **parameters**:
  * **provider_name**: String, the name of the provider
  * **machine_name**: String, the name of the machine
* **response**: Nothing

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": "ok"
}
```


## list_toolchains
* **description**: List allowed toolchains for a given machine:
* **url**: ```https://api.zephy-science.com/admin/machines/list_toolchains/```
* **method**: POST
* **parameters**: 
  * **provider_name**: String, the name of a the machine provider
  * **machine_name**: str, The name of the machine
* **response**: A list of toolchain names (string)

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": [
        "extra", 
        "rose", 
        "assess", 
        "mesh", 
        "anal", 
        "calc"
    ]
}
```

# Toolchains

## list

* **description**: Get all allowed operations:
* **url**: ```https://api.zephy-science.com/admin/toolchains/list/```
* **method**: GET
* **parameters**:
  * **date**: int, OPTIONAL, UTC timestamp, in seconds. Allow to see the result at a specific point in time
  * **limit**: int, OPTIONAL, only received a limited amount of jobs
  * **offset**: int, OPTIONAL, skip the first jobs from the list
  * **order**: string, OPTIONAL, an SQL like formatted string to sort the results. Ex: `name ASC, fixed_price DESC`). The allowed order fields are:
     * **name**
     * **fixed_price**
     * **machine_limit**
* **response**: Array of object, with fields:
  * **name**: String, the name of the toolchain
  * **fixed_price**: float, the price of a computation, in zephycoin
  * **machine_limit**: int, how many machines can work on the same computation. Min 1; 2+ = cluster

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": [
       {
         "name": "upload_and_anal",
         "fixed_price": 0.1,
         "machine_limit": 1,
       },
       {
         "name": "upload_and_link",
         "fixed_price": 0.1,
         "machine_limit": 1,
       },
       ...
    ]
}
```

## show

* **description**: show an existing toolchain:
* **url**: ```https://api.zephy-science.com/admin/toolchains/show/```
* **method**: GET, POST
* **parameters**:
  * **toolchain_name**: String, the name of the toolchain
* **response**: An object, with fields:
  * **name**: String, the name of the toolchain
  * **fixed_price**: float, the price of a computation, in zephycoin
  * **machine_limit**: int, how many machines can work on the same computation. Min 1; 2+ = cluster

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": {
       "name": "upload_and_anal",
       "fixed_price": 0.1,
       "machine_limit": 1,
    }
}
```

## update

* **description**: Update an existing toolchain:
* **url**: ```https://api.zephy-science.com/admin/toolchains/update/```
* **method**: POST
* **parameters**: 
  * **toolchain_name**: str, The name of the toolchain
* **optional parameters**: At least one of the following parameter:
  * **fixed_price**: float, the price of a computation, in zephycoin
  * **machine_limit**: int, how many machines can work on the same computation. Min 1; 2+ = cluster
  * **machines**: object with the provider (string) as key and a list of machine name (string) as value
* **response**: Nothing

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": "ok"
}
```

## list_machines
* **description**: List allowed machines for a given toolchain:
* **url**: ```https://api.zephy-science.com/admin/toolchains/list_machines/```
* **method**: POST
* **parameters**: 
  * **toolchain_name**: str, The name of the toolchain
  * **provider**: String, OPTIONAL, the name of a specific provider to restrict the results
* **response**: An object with the provider (string) as key and a list of machine names (string) as value

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": {
       "aws_eu": [
          "c5.2xlarge", 
          "c5.9xlarge", 
          "c5.4xlarge", 
          "c5.xlarge", 
          "c5.18xlarge"
       ], 
       "aws_eu_old": [
          "c4.8xlarge", 
          "c4.xlarge", 
          "c4.2xlarge", 
          "c4.4xlarge", 
          "x1.16xlarge"
       ], 
       ....
    }
}
```

# User


## login available

* **description**: Check login is available
* **url**: ```https://api.zephy-science.com/admin/user/login_available/```
* **method**: POST
* **parameters**: 
  * **login**: String, the login to check 
* **response**: bool, true if the login is available

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": true
}
```


## email available

* **description**: Check email is available
* **url**: ```https://api.zephy-science.com/admin/user/email_available/```
* **method**: POST
* **parameters**: 
  * **email String, the email to check 
* **response**: bool, true if the login is available

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": true
}
```

## list


* **description**: List all users
* **url**: ```https://api.zephy-science.com/admin/users/```
* **method**: GET, POST
* **parameters**: 
  * **include_deleted**, bool, OPTIONAL, default True. Show also deleted users if true
  * **limit**: int, OPTIONAL, only received a limited amount of jobs
  * **offset**: int, OPTIONAL, skip the first jobs from the list
  * **rank**: string, OPTIONAL, one of the following walues: "bronze", "silver", "gold" or "root"
  * **order**: string, OPTIONAL, an SQL like formatted string to sort the results. Ex: `name ASC, fixed_price DESC`). The allowed order fields are:
     * **user_id**
     * **login**
     * **rank**
     * **credit**
     * **email**
  * **filter**: string or int, OPTIONAL, limit the results looking for the filter in user logins of the user id if 'filter' is an int
* **response**: An array of objects, with the following fields
  * **id**: int, the user ID
  * **login**: String, the user loging
  * **email**: String, the user email
  * **rank**: String, the user status, possible values: "bronze", "gold", "silver", "root"
  * **credit**: Float, the amount of zephycoins
  * **deleted**: bool, True if deleted, False otherwise

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": [{
      "id": 7,
      "login": "marcel",
      "email": "marcel@gmail.com", 
      "rank": "gold",
      "credit": 127.12,
      "deleted": false
    },
    {
      "id": 8,
      "login": "robert",
      "email": "robert@yahoo.com", 
      "rank": "gold",
      "credit": 0.0,
      "deleted": true
    }]
}
```

## new

* **description**: Create a new user
* **url**: ```https://api.zephy-science.com/admin/user/new/```
* **method**: GET, POST
* **parameters**: 
  * **login**: String, the user login. The accepted values should match the following format: ```^[a-z]+(\.[a-z]+)*$```
  * **email**: String, the user email
  * **pwd**: String, the user password
  * **rank**: String, The user rank, possible values: "bronze", "gold", "silver", "root"
  * **nbr_coins**: Float, OPTIONAL, the number of credit to give to the user
  * **reason**: String, OPTIONAL, Why do we add those credits
* **response**: int, The id of the new user

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": 9
}
```

## remove

* **description**: Delete a user
* **url**: ```https://api.zephy-science.com/admin/user/remove/```
* **method**: GET, POST
* **parameters**: 
  * **user_id**: int, the id of the user
* **response**: Nothing

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": "Ok"
}
```

## add credit

* **description**: Add credit to a user
* **url**: ```https://api.zephy-science.com/admin/user/credit/add/```
* **method**: GET, POST
* **parameters**: 
  * **user_id**: int, the user id
  * **nbr_coins**: Float, the amount of money to add
  * **reason**: String, Why do we add this credits
* **response**: Float, the new credit balance of the user

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": 120.00
}
```

## reset password

* **description**: Generate a new password for given user
* **url**: ```https://api.zephy-science.com/admin/user/reset_pwd/```
* **method**: POST
* **parameters**: 
  * **email**: String, the user email
* **response**: String, the new password

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": "qsd15fsqdf5"
}
```

## show

* **description**: Get user informations
* **url**: ```https://api.zephy-science.com/admin/user/show/```
* **method**: POST
* **parameters**: 
  * One of the following:
     * **user_id**: int, the user id
     * **login**: string, the login of the user
     * **email**: string, the user email
  * **include_deleted**, bool, OPTIONAL, default False. Show user 
* **response**: 
  * **id**: int, the user ID
  * **login**: String, the user ID
  * **email**: String, the user email
  * **rank**: String, the user status, possible values: "bronze", "gold", "silver", "root"
  * **credit**: Float, the amount of zephycoins
  * **deleted**: bool, True if deleted, False otherwise

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": {
      "id": 7,
      "login": "marcel",
      "email": "marcel@gmail.com",
      "rank": "gold",
      "credit": 127.12,
      "deleted": false
    }
}
```

## consume

* **description**: Consume some user credits
* **url**: ```https://api.zephy-science.com/admin/user/consume/```
* **method**: POST
* **parameters**: 
  * **user_id**: int, the user id
  * **amount**, positive float, how many credits will be consume
  * **description**: String, a description of why the credits are consumed
  * **details**: String, more informations about the credit consumption (should be a json serialized string)
* **response**: Nothing

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": "ok"
}
```

## report

* **description**: Get the user credit consumption report
* **url**: ```https://api.zephy-science.com/admin/user/report/```
* **method**: POST
* **parameters**: 
  * **user_id**: int, the user id
  * **from** int, the date of the first transaction to take into account, in UTC timestamp
  * **to**: int, OPTIONAL, The date of the last transaction to take into account, in UTC timestamp, default now
  * **order**: string, OPTIONAL, ordering of the results, one of the following values: "description", "date", and "project". Default is "project"
* **response**: 
  * **user_id**: int, the user ID
  * **login**: String, the user login
  * **email**: String, the user email
  * **current_balance**: Float, the amount of zephycoins the user had at the "to" date
  * **previous_balance**: Float, the amount of zephycoins the user had at the "from" date
  * **details**: object, with the following structure:
     * **amount**: float, how much zephycoin the user earned (positive value) or consumed (negative value)
     * **date**: float, the timestamp of the last credit change for this kind of transaction
     * **description**: String: the reason of the credit change
     * **project**: String or null: the project related to this credit change
     * **cores_per_sec**: **NEW**: float or null: the number of cores*sec counted for this transaction
     * **calc_count**: **NEW**: int or null: the number of active calculations counted for this transaction
     * **mesh_count**: **NEW**: int or null: the number of active meshes counted for this transaction 


Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data":{
       "login":"sam",
       "user_id":2,
       "email" : "samuel.deal@aziugo.com",
       "current_balance":48344.563435,
       "previous_balance":0.0,
       "details":[
          {
             "amount":500.0,
             "date":1532622036.0,
             "description":"Initial credit for users",
             "project":null
          },
          {
             "amount":-0.5,
             "date":1539022337.102184,
             "description":"Analysis fixed cost",
             "project":"sam-1534788081.28-863f9f7a19194cac95fee2da7b380683QJUA0UQE7OJGJOLXPBG4TOW7PVCNRE"
          },
          ...
         ],
      }
   },
}
```

## change_rank

* **description**: Change user rank
* **url**: ```https://api.zephy-science.com/admin/user/change_rank/```
* **method**: POST
* **parameters**: 
  * **user_id**: int, the user id
  * **rank**: String, the new user rank, one of the following values: "root", "gold", "silver", "bronze"
* **response**: Nothing

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": "ok"
}
```

# Transactions

## list


* **description**: List all monetary transactions
* **url**: ```https://api.zephy-science.com/admin/transactions/list```
* **method**: GET, POST
* **parameters**: 
  * **user_id**: int, OPTIONAL: only show transactions related to a specifi user id
  * **project_uid**: String, OPTIONAL: only show transaction related to a project
  * **job_id**: int, OPTIONAL: only show transaction related to a specific computation
  * **limit**: int, OPTIONAL, only received a limited amount of jobs
  * **offset**: int, OPTIONAL, skip the first jobs from the list
  * **description**: string, OPTIONAL, only show transaction with specific description
  * **order**: string, OPTIONAL, an SQL like formatted string to sort the results. Ex: `date ASC, amount DESC`). The allowed order fields are:
     * **id**
     * **amount**
     * **date**
     * **job_id**
     * **login**
     * **email**
     * **description**
     * **project_uid**
     * **computing_start**
     * **computing_end**
* **response**: An array of objects, with the following fields
  * **id**: int, the transaction ID
  * **login**: String, the user login
  * **email**: String, the user email
  * **amount**: float, the number of zephycoins. Positive means we add money to the user account, negative means the user has spent money
  * **description**: String, The reason of the transaction
  * **date**: int, timestamp UTC in seconds
  * **project_uid**: string or null, The related project. May not be filled
  * **job_id**: int or null, The related work. May not be filled,
  * **computing_start**: int or null, The start of the time slice of computation we are charging, if any
  * **computing_end**: int or null, The end of the time slice of computation we are charging, if any
  

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": [{
      "id": 6,
      "login": "marcel",
      "email": "marcel@gmail.com",
      "amount": -0.10,
      "description": "fixed cost",
      "date": 1200532567,
      "project_uid": "marcel-ezotrizhefze5zefjiec9eriuter4po",
      "job_id":	127,
      "computing_start": null,
      "computing_end": null
    },
    {
      "id": 7,
      "login": "marcel",
      "email": "marcel@gmail.com",
      "amount": -0.23,
      "description": "computing power consumption",
      "date": 1200532567,
      "project_uid": "marcel-ezotrizhefze5zefjiec9eriuter4po",
      "job_id":	127,
      "computing_start": 1200532567,
      "computing_end": 1200532603
    },
    {
      "id": 8,
      "login": "marcel",
      "email": "marcel@gmail.com",
      "amount": -0.23,
      "description": "computing power consumption",
      "date": 1200532689,
      "project_uid": "marcel-ezotrizhefze5zefjiec9eriuter4po",
      "job_id": 127,
      "computing_start": 1200532603,
      "computing_end": 1200532689
    }]
}
```

## cancel


* **description**: Cancel some transaction, generating reverse transactions
* **url**: ```https://api.zephy-science.com/admin/transactions/cancel```
* **method**: GET, POST
* **parameters**: 
  * **transaction_ids**: Array of int, the transaction to cancel
  * **reason**: String, A description of why we want to cancel those transactions
* **response**: Nothing

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": "ok"
}
```

# Computations

## list


* **description**: List all computations
* **url**: ```https://api.zephy-science.com/admin/computations/list/```
* **method**: GET
* **parameters**: optional parameters:
  * **user_id**: int, OPTIONAL, The id of the user if you want only jobs of a specific user
  * **project_uid**: string, OPTIONAL, the project codename if you only want only the jobs of a specific project
  * **status**: string, OPTIONAL, only list jobs with a specific status. Accepted values are: "pending", "launching", "running", "canceled", "killed" or "finished" 
  * **limit**: int, OPTIONAL, only received a limited amount of jobs
  * **offset**: int, OPTIONAL, skip the first jobs from the list
  * **order**: string, OPTIONAL, an SQL like formatted string to sort the results. Ex: `name ASC, fixed_price DESC`). The allowed order fields are:
     * **job_id**
     * **project_uid**
     * **status**
     * **start_time**
     * **end_time**
     * **email**
     * **login**
     * **user_id**
* **response**: An array of objects, with the following fields
  * **job_id**: int, the job ID
  * **login**: string, the login of the user
  * **email**: string, the email of the user
  * **project_uid**: String, the related project
  * **create_date**: int, utc time in seconds, when the user asks for this task
  * **start_time**: int or null, utc time in seconds, When the computation started, if it started, otherwise null
  * **end_time**: int or null, utc time in seconds, When the computation finished, if it started, otherwise null
  * **status**: String, the job status. Possible values: "pending", "launching", "running", "canceled", "killed" and "finished"
  * **progress**: Float, a value between 0 and 1 giving an estimated progression rate of the job
  * **has_logs**: bool, do the computation has some logs

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": [{
      "job_id": 6,
      "login": "marcel",
      "email": "marcel@gmail.com",
      "project_uid": "marcel-45qsfqsf6251w3ed5fr89srf",
      "create_date": 123456789,
      "start_time": 123456789,
      "end_time": 123456789,
      "status": "finished",
      "progress": 1.0,
      "has_logs": true
    },
    {
      "job_id": 7,
      "login": "robert",
      "email": "rober@yahoo.com",
      "project_uid": "robert-12qsfqsf687qzf3qs21fqsf5",
      "create_date": 123456789,
      "start_time": 123456789,
      "end_time": null,
      "status": "running",
      "progress": 0.42,
      "has_logs": false
    }]
}
```

## show


* **description**: show information about a specific computation
* **url**: ```https://api.zephy-science.com/admin/computations/show/```
* **method**: GET
* **parameters**: 
  * **job_id**: int, the id of the computation to show
* **response**: an object, with the following fields
  * **job_id**: int, the job ID
  * **login**: string, the login of the job owner
  * **email**: string, the email of the job owner
  * **user_id**: int the id of the job owner
  * **project_uid**: String, the related project
  * **create_date**: int, utc time in seconds, when the user asks for this task
  * **start_time**: int or null, utc time in seconds, When the computation started, if it started, otherwise null
  * **end_time**: int or null, utc time in seconds, When the computation finished, if it started, otherwise null
  * **status**: String, the job status. Possible values: "pending", "launching", "running", "canceled", "killed" and "finished"
  * **progress**: Float, a value between 0 and 1 giving an estimated progression rate of the job
  * **has_logs**: bool, do the computation has some logs
  * **provider**: String, the code of the provider
  * **machine**: String, the name of the machine type
  * **nbr_machines**: int, the number of machine that would work on the job
  * **user_rank**: string, the rank of the user at the time of the computation was ask. Values are "root", "gold", "silver" or "bronze"
  * **toolchain_name**: string, the name of the toolchain
  * **toolchain_id**: int, the id of the toolchain
  * **fixed_price**: float, the price, in zephycoin to launch the toolchain
  * **cost_per_sec_per_machine**: float, the cost the cloud provider charges us
  * **cost_currency**: string, the currency the cloud provider uses when it charges us
  * **cost_min_sec_granularity**: int, the min sec granularity of the cloud provider
  * **cost_sec_granularity**: int, the sec granularity of the cloud provider
  * **price_per_sec_per_machine**: float, how much zephycoin we charge the user
  * **price_min_sec_granularity**: int, the min sec granularity of zephycloud
  * **price_sec_granularity**: int, the sec granularity of zephycloud



Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": {
        "cost_currency": "dollar",
        "cost_min_sec_granularity": 60,
        "cost_per_sec_per_machine": 0,
        "cost_sec_granularity": 1,
        "create_date": 1530623211,
        "end_time": 1530623323,
        "fixed_price": 0.05,
        "job_id": 54,
        "login": "tristan",
        "email": "tristan@yopmail.com",
        "user_id": 1,
        "has_logs": true,
        "machine": "docker",
        "nbr_machines": 1,
        "price_min_sec_granularity": 300,
        "price_per_sec_per_machine": 0.00005618,
        "price_sec_granularity": 300,
        "progress": 1,
        "project_uid": "tristan-1530003652.88-68a602e0227749a18934ccee9597281dS6Z7V1JYYT4CCKB5F18E7HGIZVHBE2",
        "provider": "docker_local",
        "start_time": 1530623211,
        "status": "finished",
        "toolchain_id": 143,
        "toolchain_name": "calc",
        "user_rank": "gold"
    }
}
```

## show_logs


* **description**: show the logs of a specific computation
* **url**: ```https://api.zephy-science.com/admin/computations/show_logs/```
* **method**: GET, POST
* **parameters**: 
  * **job_id**: int, the id of the computation to show
* **response**: string, the logs of the computation



Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data":  "2018-07-03 13:06:54,452 - Job     54 - INFO - Waiting for input file\n2018-07-03 13:07:01,367 - Job     54 - INFO - Running task\n2018-07-03 13:07:01,410 - Job     54 - INFO - Extracting file /home/aziugo/worker_scripts/workdir/project_file.zip\n2018-07-03 13:07:01,476 - Job     54 - INFO - Extracting file /home/aziugo/worker_scripts/workdir/anal.zip\n2018-07-03 13:07:01,527 - Job     54 - INFO - Extracting file /home/aziugo/worker_scripts/workdir/mesh.zip\n2018-07-03 13:07:03,398 - Job     54 - INFO - Extracting file /home/aziugo/worker_scripts/workdir/calc_params.zip\n2018-07-03 13:07:03,401 - Job     54 - INFO - Starting toolchain\n2018-07-03 13:08:20,196 - Job     54 - INFO - Calculation Process 1 Calculation is over.\n2018-07-03 13:08:20,260 - Job     54 - INFO - Toolchain finished with exit code 0\n2018-07-03 13:08:20,260 - Job     54 - INFO - Packaging results\n2018-07-03 13:08:27,521 - Job     54 - INFO - Results are ready to fetch\n2018-07-03 13:08:27,522 - Job     54 - INFO - Task finished\n2018-07-03 13:08:27,522 - Job     54 - INFO - Waiting for output fetch to complete\n"
}
```

## kill


* **description**: Stop a running or pending computation
* **url**: ```https://api.zephy-science.com/admin/computations/kill/```
* **method**: GET, POST
* **parameters**: 
  * **job_id**: int, the id of the computation to stop
* **response**: Nothing

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": "ok"
}
```


## disable shutdown


* **description**: Disable worker instance shutdown for debug purpose
* **url**: ```https://api.zephy-science.com/admin/computations/disable_shutdown/```
* **method**: GET, POST
* **parameters**: 
  * **job_id**: int, the id of the computation to stop
* **response**: Nothing

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": "ok"
}
```

# Projects

## list

* **description**: list all projects
* **url**: ```https://api.zephy-science.com/admin/projects/list/```
* **method**: GET, POST
* **parameters**: 
  * **user_id**: int, OPTIONAL, only show projects of given user
  * **date**: int, OPTIONAL, UTC timestamp, in seconds. Allow to see the result at a specific point in time
  * **limit**: int, OPTIONAL, only received a limited amount of jobs
  * **offset**: int, OPTIONAL, skip the first jobs from the list
  * **order**: string, OPTIONAL, an SQL like formatted string to sort the results. Ex: `name ASC, fixed_price DESC`). The allowed order fields are:
     * **id**
     * **project_uid**
     * **storage**
     * **status**
     * **email**
     * **creation_date**
  * **filter**: string, OPTIONAL, return only project where the project_uid contains the given filter
  * **status**: string, OPTIONAL, return only project with given status. Should be a value in the following list: "pending", "raw", "analysing", "analysed"
  * **storage**: string, OPTIONAL, return only project with given storage
* **response**: A list of objects, with the following fields
  * **login**: string, the project's owner login
  * **email**: string, the project's owner email
  * **user_id**: int, the project's owner identifier
  * **project_uid**: string, the project codename
  * **status**: string, the status of the project
  * **storage**: string, the name of the storage used for all the files of this project
  * **create_date**: int, the UTC timestamp of the project creation


Example:


```json
{
    "data": [
        {
            "login": "tristan",
            "project_uid": "tristan-1529949694.06-7b6765804a2244f98e66a2200ca86de6C8QPJJO9BMFCSOEIWUD8LWVICHHQEL",
            "status": "analysed",
            "storage": "docker_filesystem",
            "create_date": 1558552415
        },
        {
            "login": "tristan",
            "project_uid": "tristan-1530003652.88-68a602e0227749a18934ccee9597281dS6Z7V1JYYT4CCKB5F18E7HGIZVHBE2",
            "status": "analysed",
            "storage": "docker_filesystem",
            "create_date": 1553282004
        }
    ],
    "error_msgs": [],
    "success": 1
}
```

## show

* **description**: Show the details of a project
* **url**: ```https://api.zephy-science.com/admin/projects/show/```
* **method**: GET, POST
* **parameters**: 
  * **user_id**: int, the user_id of the project's owner
  * **project_uid**: string, the project codename
  * **include_deleted**: bool, OPTIONAL, tell if you want to include deleted meshes and calculations
* **response**: An object with the following fields
  * **user_id**: int, the project's owner user id
  * **login**: string, the project's owner login
  * **email**: string, the project's owner email
  * **project_uid**: string, the project codename
  * **create_date**: int, utc timestamp
  * **status**: string, the status of the project
  * **storage**: string, the name of the storage used for all the files of this project
  * **total_size**: int, the sum of all non-deleted files sizes of this project (in bytes)
  * **raw_file_url**: String or null, the url of the file containing initial project data
  * **analyzed_file_url**: String or null, the url of the analysed data
  * **progress**: Float, a value between 0 and 1 giving an estimated progression rate of the job
  * **amount**: Float, How many credits have been burned on this project
  * **meshes**: Array of object, with the following fields:
     * **mesh_id**: int, the id of this mesh
     * **name**: string, the name of this mesh
     * **status**: string, the status of the mesh
     * **create_date**: int, the date of creation
     * **delete_date**: int or null, the date of deletion, if deleted, else null
     * **preview_file_id**: int or null, the id of the preview file
     * **result_file_id**: int or null, the id of the result file
  * **calculations**: Array of object, with the following fields:
     * **job_id**: int, the id of the calculation
     * **name**: string, the name of the calculation
     * **status**: string, the status of the calculation
     * **create_date**: int, the date of creation
     * **delete_date**: int or null, the date of deletion, if deleted, else null
     * **mesh_id**: int, the id of the mesh used by this calculation
     * **status_file_id**: int or null, the id of the status file
     * **result_file_id**: int or null, the id of the result file
     * **iterations_file_id**: int or null, the id of the result file containing iterations
     * **reduce_file_id**: int or null, the id of the result file containing the REDUCED folder
     * **internal_file_id**: int or null, the id of the internal file archive
     * **has_logs**: bool, do the computation has some logs
 

Example:


```json
{
    "data": {
        "login": "tristan",
        "email": "tristan@yopmail.com",
        "user_id": 1,
        "project_uid": "tristan-1529949694.06-7b6765804a2244f98e66a2200ca86de6C8QPJJO9BMFCSOEIWUD8LWVICHHQEL",
        "status": "analysed",
        "create_date": 1553282004,
        "storage": "docker_filesystem",
        "total_size": 313826697
        "raw_file_url": "https://zephycloud.sam.local/local_files/docker_filesystem/project_tristan-1529949694.06-b6765804a2244f98e66a2200ca86de6C8QPJJO9BMFCSOEIWUD8LWVICHHQEL.zip",
        "analyzed_file_url": "https://zephycloud.sam.local/local_files/docker_filesystem/tristan-1529949694.06-7b6765804a2244f98e66a2200ca86de6C8QPJJO9BMFCSOEIWUD8LWVICHHQEL-anal-1.zip",
        "calculations": [
            {
                "job_id": 6,
                "create_date": 1529952274,
                "delete_date": null,
                "mesh_id": 1,
                "name": "tristan-1529949694.06-7b6765804a2244f98e66a2200ca86de6C8QPJJO9BMFCSOEIWUD8LWVICHHQEL_D0050_S5_C1_ZS_test_M1_ZS_M010_Slope_Auto",
                "result_file_url": null,
                "status": "canceled",
                "status_file_url": null,
                "has_logs": false
            },
            {
                "job_id": 7,
                "create_date": 1529952407,
                "delete_date": null,
                "mesh_id": 1,
                "name": "tristan-1529949694.06-7b6765804a2244f98e66a2200ca86de6C8QPJJO9BMFCSOEIWUD8LWVICHHQEL_D0100_S5_C1_ZS_test_M1_ZS_M010_Slope_Auto",
                "result_file_url": "https://zephycloud.sam.local/local_files/docker_filesystem/tristan-1529949694.06-7b6765804a2244f98e66a2200ca86de6C8QPJJO9BMFCSOEIWUD8LWVICHHQEL-534bb820-37b6-4b08-9260-2372bb06132b.zip",
                "status": "computed",
                "status_file_url": "https://zephycloud.sam.local/local_files/docker_filesystem/tristan-1529949694.06-7b6765804a2244f98e66a2200ca86de6C8QPJJO9BMFCSOEIWUD8LWVICHHQEL_calc_status_3.zip",
                "internal_file_url": "https://zephycloud.sam.local/local_files/docker_filesystem/tristan-1529949694.06-7b6765804a2244f98e66a2200ca86de6C8QPJJO9BMFCSOEIWUD8LWVICHHQEL_calc_internal_3.zip",
                "has_logs": true,
                "iterations_file_url": null,
                "iterations_file_url": null
            },
        ],
        "meshes": [
            {
                "create_date": 1529949762,
                "delete_date": null,
                "mesh_id": 1,
                "name": "M1_ZS_M010_Slope_Auto",
                "preview_file_url": "https://zephycloud.sam.local/local_files/docker_filesystem/tristan-1529949694.06-7b6765804a2244f98e66a2200ca86de6C8QPJJO9BMFCSOEIWUD8LWVICHHQEL-4845155d-6e01-4dc8-b943-7ce699ae7f56.zip",
                "result_file_url": "https://zephycloud.sam.local/local_files/docker_filesystem/tristan-1529949694.06-7b6765804a2244f98e66a2200ca86de6C8QPJJO9BMFCSOEIWUD8LWVICHHQEL-66068175-25b8-42b5-adb9-570274323456.zip",
                "status": "computed",
            }
        ],
    },
    "error_msgs": [],
    "success": 1
}
```

## remove

* **description**: Delete an existing project
* **url**: ```https://api.zephy-science.com/admin/projects/remove/```
* **method**: POST
* **parameters**: 
  * **project_uid**: string, the project codename
  * **user_id**: int, the id of the project owner
  * **include_deleted**: bool, OPTIONAL, remove the project, even if it's already deleted or it's owner is deleted
* **response**: Nothing

Example:


```json
{
    "data": "ok",
    "error_msgs": [],
    "success": 1
}
```

## get file url

* **description**: Delete an existing project
* **url**: ```https://api.zephy-science.com/admin/projects/file_url/```
* **method**: POST
* **parameters**: 
  * **project_uid**: string, the project codename
  * **user_id**: int, the id of the project owner
  * **file_id**: int, the file identifier
  * **include_deleted**: bool, OPTIONAL, remove the project, even if it's already deleted or it's owner is deleted
* **response**: String

Example:


```json
{
    "data": "https://zephycloud-eu-test.s3-eu-west-1.amazonaws.com/zephycloud/apidev.zephy-science.com/theo-1559916465.31-dc69c595b21d4107b4f69233c33ecdea-2bac9098-f80a-419e-b36d-3ce66e3d9808.zip",
    "error_msgs": [],
    "success": 1
}
```

# Reports

## all users

* **description**: Get all user credit consumption reports
* **url**: ```https://api.zephy-science.com/admin/reports/users/```
* **method**: POST
* **parameters**: 
  * **from** int, OPTIONAL the date of the first transaction to take into account, in UTC timestamp, default last report date or (if none) Jan, 1st 1970 at midnight UTC
  * **to**: int, OPTIONAL, The date of the last transaction to take into account, in UTC timestamp, default now
  * **order**: string, OPTIONAL, ordering of the results, one of the following values: "description", "date", and "project". Default is "project"
* **response**: An array of the following values:
  * **user_id**: int, the user ID
  * **login**: String, the user login
  * **email**: int, the user email
  * **current_balance**: Float, the amount of zephycoins the user had at the "to" date
  * **previous_balance**: Float, the amount of zephycoins the user had at the "from" date
  * **details**: object, with the following structure:
     * **amount**: float, how much zephycoin the user earned (positive value) or consumed (negative value)
     * **date**: float, the timestamp of the last credit change for this kind of transaction
     * **description**: String: the reason of the credit change
     * **project**: String or null: the project related to this credit change
     * **cores_per_sec**: **NEW**: float or null: the number of cores*sec counted for this transaction
     * **calc_count**: **NEW**: int or null: the number of active calculations counted for this transaction
     * **mesh_count**: **NEW**: int or null: the number of active meshes counted for this transaction 


Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data":[
       {
          "login":"sam",
          "email": "samuel.deal@aziugo.com",
          "user_id":2
          "current_balance":48344.563435,
          "previous_balance":0.0,
          "details":[
             {
                "amount":500.0,
                "date":1532622036.0,
                "description":"Initial credit for users",
                "project":null
             },
             {
                "amount":-0.5,
                "date":1539022337.102184,
                "description":"Analysis fixed cost",
                "project":"sam-1534788081.28-863f9f7a19194cac95fee2da7b380683QJUA0UQE7OJGJOLXPBG4TOW7PVCNRE"
             },
             ...
          ],
      },
      {
          "login":"tristan",
          "email": "tristan@yopmail.com",
          "user_id":1
          "current_balance": 0.0,
          "previous_balance":0.0,
          "details":[],
      }, 
      ...
   ],
}
```

## benefits

* **description**: Get report about aziugo benefits
* **url**: ```https://api.zephy-science.com/admin/reports/benefits/```
* **method**: POST
* **parameters**: 
  * **from** int, OPTIONAL the date of the first transaction to take into account, in UTC timestamp, default last report date or (if none) Jan, 1st 1970 at midnight UTC
  * **to**: int, OPTIONAL, The date of the last transaction to take into account, in UTC timestamp, default now
  * **currency**: String, OPTIONAL, The currency of the report, allowed value: "euro", "dollar", "yuan". Default depends of the server configuration
  * **user_id**: int, OPTIONAL, The id of a specific user. default will return all users who have consumed zephycoins.
* **response**: An array of the following values:
  * **user_id**: int, the id of this user
  * **login**: String, the login of this user
  * **email**: String, the email of this user
  * **currency**: String, the currency of the following report
  * **computation_cost**: float, How much we paid our cloud provider to satisfy this user
  * **factured_computation**: float, How mush the user burned for computations
  * **factured_storage**: float, How mush the user burned for storage
  * **openfoam_commission**: float, how much we should pay the openfoam foundation
  * **benefits**: float, How much benefits aziugo have made from this user

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data":[
       {
          "user_id": 1,
          "login": "tristan",
          "email": "tristan@yopmail.com",
          "currency": "euro",
          "computation_cost": 17.467941762,
          "factured_computation": 42.475968,
          "factured_storage": 73965.8,
          "openfoam_commission": 2.1237984,
          "benefits": 73988.684227838,
       },
       {
          "user_id": 2
          "login": "sam",
          "email": "samuel.deal@aziugo.com",
          "currency": "euro",
          "computation_cost": 4.306674685,
          "factured_computation": 15.94626,
          "factured_storage": 48605.8,
          "openfoam_commission": 0.797313,
          "benefits": 48616.642272315,
        },
        ...
   ],
}
```

## get date


* **description**: Get the date of the last generated report
* **url**: ```https://api.zephy-science.com/admin/report/get_date/```
* **method**: GET, POST
* **parameters**: None
* **response**: The date in UTC timestamp, or null
Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": 1558531898
}
```

## set date

* **description**: Set the date of the last generated report
* **url**: ```https://api.zephy-science.com/admin/report/set_date/```
* **method**: POST
* **parameters**: 
  * **date**: int, the date in UTC timestamp
* **response**: Nothing

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": "ok"
}
```


## pricing constants

* **description**: Get the several constants and config used for pricing
* **url**: ```https://api.zephy-science.com/admin/reports/pricing_constants/```
* **method**: GET or POST
* **parameters**: None
* **response**: An object with the following values:
  * **default_cost_currency**: string, the default currency for a cloud provider
  * **default_cost_sec_granularity**: int, the time granularity a cloud provider use to charge aziugo
  * **default_cost_min_sec_granularity**: int, the minimum number of second a provider charge us
  * **default_currency**: String, the default currency used for price conversion
  * **default_price_sec_granularity**: int, the time granularity we use to charge a client in zephycoins
  * **default_price_min_sec_granularity**: int, the time minimum time we charge a client in zephycoins
  * **openfoam_donations**: float, the ratio of the money we give back to the openfoam foundation
  * **security_margin**: float, a security margin we use for pricing
  * **zephycoin_price**: float, a much a zephycoin worth in default_currency
  * **margin**: an object with the user rank (string) as key and the margin we make (float) as value
  * **currency_to_euro**: an object with the currency (string) as key, and the conversion rate (float) as value

Example:

```json
{
  "success": 1
  "error_msgs": [], 
  "data": {
    "default_cost_currency": "dollar", 
    "default_cost_min_sec_granularity": 60, 
    "default_cost_sec_granularity": 1, 
    "default_currency": "euro", 
    "default_price_min_sec_granularity": 300, 
    "default_price_sec_granularity": 300, 
    "openfoam_donations": 0.05, 
    "security_margin": 0.05, 
    "zephycoin_price": 4.0,
    "margins": {
      "bronze": 10, 
      "gold": 2, 
      "root": 1, 
      "silver": 4
    }, 
    "currency_to_euro": {
      "dollar": 0.85, 
      "euro": 1.0, 
      "yuan": 0.13
    }
  }
}

```
