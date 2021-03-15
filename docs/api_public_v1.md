# API v1

{{>toc}}

# API v1: Common information


All API calls are located on https://api.zephy-science.com/v1/

You can also forget the "v1" folder until a new API version is released and fixed as default API
The authentificatiuon is done using Basic Auth.

Some generic rules about the requets:
* All requests should be done via https
* All requests should be json requests.
* All requests require the user to be logged in.
* All requests sending files should call the file argument **files[]**
* All requests should call a trailling slash url (like a folder address)

All responses should have the following structure, even in case of error:

```json
{
    "success": 1,
    "error_msgs": ["List of error messages, or empty array in case of success"],
    "data": "Whatever data. Could be int, string, array or object"
}
```

# User

## status

* **description**: Get information about the current user
* **url**: ```https://api.zephy-science.com/v1/user/status/```
* **method**: GET
* **parameters**: Nothing
* **response**:
  * **user_status**: String, the user status, possible values: "bronze", "gold", "silver", "root", "guest"
  * **credit**: Float, the amount of zephycoins

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": {
      "user_status": "gold",
      "credit": 127.12
    }
}
```

# Jobs

## list
* **description**: List all jobs of current user
* **url**: ```https://api.zephy-science.com/v1/jobs/list/```
* **method**: GET, POST
* **parameters**:
  * **project_codename**: String, OPTIONAL, get only jobs related to given project
  * **limit**: int, OPTIONAL, only received a limited amount of jobs
  * **offset**: int, OPTIONAL, skip the first jobs from the list
  * **order**: string, OPTIONAL, an SQL like formatted string to sort the results. Ex: `status ASC, job_id DESC`). The allowed order fields are:
     * **job_id**
     * **project_uid**
     * **start_time**
     * **end_time**
     * **status**
* **response**: Array of objects, with fields:
  * **job_id**: int, the job identifier
  * **project_name**: String, the project codename
  * **start**: String, utc time at which the instance started. Possible values: "-","YYYY/MM/DD-hh:mm"
  * **end**: String, utc time at which the instance stopped. Possible values: "-","YYYY/MM/DD-hh:mm"
  * **ncoins**: Float>0, number of coins for the job
  * **status**: String, the job status. Possible values: "pending", "launching", "running", "canceled", "killed" and "finished"
  * **progress**: Float, a value between 0 and 1 giving an estimated progression rate of the job

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": [
      {
         "job_id": 17,
         "project_name": "e736b143-b795-4f47-a576-7a9ad1887899_4c2383f5c88e9110642953b5dd7c88a1",
         "start": "2018/04/23-16:35",
         "end": "-",
         "ncoins": 12.543,
         "status": "running",
         "progress": 0.543
      },
      {
         "job_id": 43,
         "project_name": "e736b143-b795-4f47-a576-7a9ad1887899_4c2383f5c88e9110642953b5dd7c88a1",
         "start": "2018/04/23-16:35",
         "end": "-",
         "ncoins": 12.543,
         "status": "running",
         "progress": 0.543
      },

   ]
}
```

## cancel

* **description**: Cancel or kill a running job
* **url**: ```https://api.zephy-science.com/v1/jobs/cancel/```
* **method**: POST
* **parameters**:
  * **job_id**: int, The id of the job to cancel
  * **reason**: String, OPTIONAL, why do we canceled the job
* **response**: String, the new status of the job

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": "canceled"
}
```

## status

* **description**: Get the status of a job
* **url**: ```https://api.zephy-science.com/v1/jobs/status/```
* **method**: POST
* **parameters**:
  * **job_id**: int, The id of the job to cancel
* **response**: Object, with fields:
  * **job_id**: int, The id of the job to cancel
  * **project_name**: String, the project codename
  * **start**: String, utc time at which the instance started. Possible values: "-","YYYY/MM/DD-hh:mm"
  * **end**: String, utc time at which the instance stopped. Possible values: "-","YYYY/MM/DD-hh:mm"
  * **ncoins**: Float>0, number of coins for the job
  * **status**: String, the job status. Possible values: "pending", "launching", "running", "canceled", "killed" and "finished"
  * **progress**: Float, a value between 0 and 1 giving an estimated progression rate of the job

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": {
       "job_id": 43,
       "project_name": "e736b143-b795-4f47-a576-7a9ad1887899_4c2383f5c88e9110642953b5dd7c88a1",
       "start": "2018/04/23-16:35",
       "end": "-",
       "ncoins": 12.543,
       "status": "running",
       "progress": 0.543
    }
}
```

# Provider

## list

* **description**: Get all available providers:
* **url**: ```https://api.zephy-science.com/v1/providers/list/```
* **method**: GET
* **parameters**:
  * **limit**: int, OPTIONAL, only received a limited amount of jobs
  * **offset**: int, OPTIONAL, skip the first jobs from the list
  * **order**: string, OPTIONAL, an SQL like formatted string to sort the results. Ex: `name ASC, location DESC`). The allowed order fields are:
     * **name**
     * **location**
* **response**: Array of object, with fields:
  * **name**: String, the name of the provider. If the name finishes with '_spot', it runs spot instances.
  * **location**: String, a geographic location of the provider

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": [
       {
         "name": "aws_eu",
         "location": "eu",
       },
       {
         "name": "aws_eu_spot",
         "location": "eu",
       }
    ]
}
```

## details

* **description**: Get all the prices and details of a provider machines
* **url**: ```https://api.zephy-science.com/v1/provider/details/```
* **method**: POST
* **parameters**:
  * **provider**: String, the provider you want to use. ex: "aws_eu"
* **response**: Object, with fields:
  * **price_granularity**: int, the pricing time granularity, in seconds
  * **machines_list**: Array of object, List of machines with fields, ordered by the number of cores then the number of RAM:
     * **name**: String, the name of the machine
     * **cores**: int, the number of virtual CPU
     * **ram**: int, the number of Gigabytes of RAM
     * **availability**: int, the number of available machines
     * **availability_max**: int, the maximum number of available machines
     * **spot_index**: 0=<float<=1., spot quality index, equal to 0 when no spot
     * **prices**: Object with user status (String) as key and price per hour (float) as value.
  * **fix_prices**: Object with operation (String) as key and price (float) as value
  * **configurations**: Object with operation (String) as key and Object as value with fields:
     * **cluster**: int, 0 when cluster is not allowed, maximum number of machines if >0
     * **machines**: array of strings defining the possible machines, each string defining a machine that has to be included in the **machines_list**

Example:

```json
{
	"success":1,
	"error_msgs":[],
	"data":{
		"granularity":300,
		"fix_prices":{
			"project":0.10,
			"mesh":0.05,
			"calc":0.05,
			"rose":0.05,
			"extra":0.05,
			"assess":0.05,
			},
		"configurations":{
			"anal":{
				"cluster":0,
				"machines":[
					"c5.x",
					"c5.2x",
					"c5.4x",
					"c5.9x",
					"c5.18x",
					],
				},
			"mesh":{
				"cluster":0,
				"machines":[
					"c5.x",
					"c5.2x",
					"c5.4x",
					"c5.9x",
					"c5.18x",
					],
				},
			"calc":{
				"cluster":5,
				"machines":[
					"c5.x",
					"c5.2x",
					"c5.4x",
					"c5.9x",
					"c5.18x",
					],
				},
			},
		"machines_list":[
			{
				"name":"c5.x",
				"cores":4,
				"ram":8,
				"availability":400,
				"availability_max":400,
				"spot_index":0.0,
				"prices":{
					"root":0.19,
					"gold":0.38,
					"silver":0.76,
					"bronze":1.9
					}
			},
			{
				"name":"c5.2x",
				"cores":8,
				"ram":16,
				"availability":400,
				"availability_max":400,
				"spot_index":0.0,
				"prices":{
					"root":0.34,
					"gold":0.68,
					"silver":1.36,
					"bronze":3.40
					}
			},
			{
				"name":"c5.4x",
				"cores":16,
				"ram":32,
				"availability":400,
				"availability_max":400,
				"spot_index":0.0,
				"prices":{
					"root":0.68,
					"gold":1.36,
					"silver":3.40,
					"bronze":6.80
					}
			},
			{
				"name":"c5.9x",
				"cores":36,
				"ram":72,
				"availability":10,
				"availability_max":400,
				"spot_index":0.0,
				"prices":{
					"root":1.53,
					"gold":3.06,
					"silver":6.12,
					"bronze":15.30
					}
			},
			{
				"name":"c5.18x",
				"cores":72,
				"ram":144,
				"availability":400,
				"availability_max":400,
				"spot_index":0.0,
				"prices":{
					"root":3.06,
					"gold":6.12,
					"silver":12.24,
					"bronze":30.60
					}
			}
			],
		}
	}




```

## availability

* **description**: Get all the availability of a provider machines
* **url**: ```https://api.zephy-science.com/v1/provider/availability/```
* **method**: POST
* **parameters**:
  * **provider**: String, the provider you want to use. ex: "aws_eu"
* **response**: Object with machine name (String) as key and number of available machines (int) as value

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": {
      "c5.2x" : 50,
      "c5.4x" : 42,
      ...
    }
}
```

# Storage

## list

* **description**: Get all available storages:
* **url**: ```https://api.zephy-science.com/v1/storages/list/```
* **method**: POST
* **parameters**:
  * **limit**: int, OPTIONAL, only received a limited amount of jobs
  * **offset**: int, OPTIONAL, skip the first jobs from the list
  * **order**: string, OPTIONAL, an SQL like formatted string to sort the results. Ex: `name ASC, location DESC`). The allowed order fields are:
     * **name**
     * **location**
     * **type**
* **response**: Array of object, with fields:
  * **name**: String, the name of the storage
  * **type**: String, the type of storage. Possible values: 's3' (nothing else yet)
  * **location**: String, a geographic location of the provider

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": [
       {
         "name": "s3_eu",
         "type": "s3",
         "location": "eu",
       },
       {
         "name": "s3_cn",
         "type": "s3",
         "location": "cn",
       }
    ]
}
```

# Project

## create_and_link

* **description**: Create an locally analysed project
* **url**: ```https://api.zephy-science.com/v1/project/create_and_link/```
* **method**: POST
* **parameters**:
  * **project_codename**: String, the project code name.
  * **storage**: String, OPTIONAL, the storage name (ex: 's3_eu')
  * A zip file containing the project data
  * Another zip file containing the project analyzed data
* **response**: int, the job id

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": "Ok"
}
```

## create_and_analyse

* **description**: Create a project and analyse it on the cloud
* **url**: ```https://api.zephy-science.com/v1/project/create_and_analyse/```
* **method**: POST
* **parameters**:
  * **project_codename**: String, the project code name.
  * **storage**: String, OPTIONAL, the storage name (ex: 's3_eu')
  * **provider**: String, the provider to run analysis on (ex: 'aws_eu')
  * **machine**: String, the type of machine you want (ex: 'c4.2xlager')
  * **nbr_machines**: Int, the number of amchine to run analysis. Should always be 1
  * A zip file containing the project raw data
* **response**: int, the job_id

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": 134
}
```

## status

* **description**: Create a project and analyse it on the cloud
* **url**: ```https://api.zephy-science.com/v1/project/status/```
* **method**: POST
* **parameters**:
  * **project_codename**: String, the project code name
* **response**: Object, the information about the project, with fields:
  * **project_status**: String, the project status, oen of the following values "pending", "analysed", "analysing" and "raw"
  * **project_url**: String, a url to download the analysed data of the project, a zip file
  * **already_spent**: Float, how many zephycoins have been already spent on this project

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": {
       "project_status": "analyzed",
       "project_data_url": "https://...",
       "already_spent": 12.54
    }
}
```

## watch

* **description**: Update the db with analysis process duration results
* **url**: ```https://api.zephy-science.com/v1/project/watch/```
* **method**: POST
* **parameters**:
  * **diamin**: Float, a distance characterizing the size of the project
  * **nh**: Int, the number of iso-heights over diaload (the distance over which the data are processed)
  * **np**: Int, the number of processors that ran the process
  * **duration**: Int, the duration for the analysis process, in seconds
* **response**: Object, the information about the project, with fields:
  * **new_db**: Dictionnary reporting the changes in the db (providing a set of variables specific to the process)

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": {
       "new_db": {"a":1.,"b":1.,"e":1.}
    }
}
```


## remove

* **description**: Delete a project, removing all related meshes and calculations
* **url**: ```https://api.zephy-science.com/v1/project/remove/```
* **method**: POST
* **parameters**:
  * **project_codename**: String, the project code name.
* **response**: Nothing

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": "Ok"
}
```

# Mesh

## create

* **description**: Generate a mesh for the project
* **url**: ```https://api.zephy-science.com/v1/mesh/create/```
* **method**: POST
* **parameters**:
  * **project_codename**: String, the project code name
  * **mesh_name**: String, the name of the mesh
  * **provider**: String, the provider to run the mesh computation (ex: "aws_eu")
  * **machine**: String, the machine type you want the mesh computation running on (ex: "c4.2xlarge")
  * **nbr_machines**: String, the machine type you want the mesh computation running on (ex: "c4.2xlarge")
  * A zip file containing the parameters of the mesh computation to run
* **response**: Int, the job id

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": {
       "job_id": 156
    }
}
```

## list

* **description**: List all meshes
* **url**: ```https://api.zephy-science.com/v1/mesh/list/```
* **method**: POST
* **parameters**:
  * **project_codename**: String, the project code name
  * **limit**: int, OPTIONAL, only received a limited amount of jobs
  * **offset**: int, OPTIONAL, skip the first jobs from the list
  * **order**: string, OPTIONAL, an SQL like formatted string to sort the results. Ex: `status ASC, name ASC`). The allowed order fields are:
     * **name**
     * **status**
* **response**: List of Objects, with fields:
  * **name**: String, the name of the mesh
  * **status**: String, status of the mesh, possible values are "pending", "computing", "computed" and "canceled"
  * **mesh_parameters**: TODO

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": [
       {
         "name": "mesh_05",
         "status": "computing"
       },
       {
         "name": "mesh_10",
         "status": "computed"
       },
       ...
    ]
}
```

## show

* **description**: Get informations about one mesh
* **url**: ```https://api.zephy-science.com/v1/mesh/show/```
* **method**: POST
* **parameters**:
  * **project_codename**: String, the project code name
  * **mesh_name**: String, the name of the mesh
* **response**: Object, the data of the mesh
  * **status**: String, status of the mesh, possible values are "pending", "computing", "computed" and "canceled"
  * **mesh_data_url**: The url of the data to download. Optional, only if the mesh is computed
  * **preview_url**: The url of the data to download. Optional, only if the mesh is computed

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": {
      "status": "computed",
      "mesh_data_url": "https://....",
      "preview_url": "https://...."
    }
}
```

## watch

* **description**: Update the db with mesh process duration results
* **url**: ```https://api.zephy-science.com/v1/mesh/watch/```
* **method**: POST
* **parameters**:
  * **npground_fine**: Int, the number of ground nodes for the fine mesh
  * **npground_coarse**: Int, the number of ground nodes for the coarse mesh
  * **npground_reduced**: Int, the number of ground nodes for the reduced mesh
  * **nz**: Int, the number of layers of cells in vertical direction
  * **nh**: Int, the number of iso-heights over diadom (characterizing the size of the calculation domain)
  * **np**: Int, the number of processors that ran the process
  * **duration**: Int, the duration for the analysis process, in seconds
* **response**: Object, the information about the project, with fields:
  * **new_db**: Dictionnary reporting the changes in the db (providing a set of variables specific to the process)

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": {
       "new_db": {"a":1.,"b":1.,"e":1.}
    }
}
```


## remove

* **description**: Delete a mesh and all computation using this mesh
* **url**: ```https://api.zephy-science.com/v1/mesh/remove/```
* **method**: POST
* **parameters**:
  * **project_codename**: String, the project code name
  * **mesh_name**: String, the name of the mesh
* **response**: Nothing

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": "ok"
}
```

# Calculation

## run

* **description**: Run new calculation
* **url**: ```https://api.zephy-science.com/v1/calculation/run/```
* **method**: POST
* **parameters**:
  * **project_codename**: String, the project code name
  * **mesh_name**: String, the name of the mesh
  * **calculation_name**: String, the name of the calculation to create
  * **provider**: String, the provider to run the mesh computation (ex: "aws_eu")
  * **machine**: String, the machine type you want the mesh computation running on (ex: "c4.2xlarge")
  * **nbr_machines**: Int, the number of machines to instanciate
  * **split_results**: Bool, Optional, default FALSE. Do you want the results to be splitted in 3 files ?
  * A zip file containing the parameters of the computation to run
* **response**: Object with fields:
  * **calculation_id**: Int, the id of the new calculation
  * **job_id**: Int, the job id

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": {
      "calculation_id": 678,
      "job_id": 207
    }
}
```

## show

* **description**: Get the details of an existing calculation
* **url**: ```https://api.zephy-science.com/v1/calculation/show/```
* **method**: POST
* **parameters**:
  * **project_codename**: String, the project code name
  * **calculation_name**: String, the name of the calculation to show
* **response**: Object with fields:
  * **status**: String, the status of the calculation
  * **job_id**: Int, the job id
  * **status**: String, the calculation status, possible values: "pending", "computing", "canceled", "computed", "stopped"
  * **start_date**: int or Null, the last date when the calculation started, in UTC second timestamp
  * **stop_date**: int or Null, the stop date of last calculation action if any, in UTC second timestamp
  * **follow_url**: String or Null, the url of the follow file if it exists
  * **follow_date**: int or Null, the date of last change of the calculation status change, in UTC second timestamp
  * **result_url**: String or Null, the url of the result file if computation has successfully finished
  * **iterations_url**: String or Null, the url of the result file containing the iterations if computation has successfully finished and results have been splitted
  * **reduce_url**: String or Null, the url of the result file containing the REDUCED folder if computation has successfully finished and results have been splitted
  * **nbr_coins**: float, the number of coins burnt on this computation

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": {
      "calculation_id": 207,
      "job_id": 678,
      "status": "computing",
      "start_date": 12506975,
      "stop_date": null,
      "follow_url": "https://...",
      "follow_date": 12507501,
      "result_url": null,
      "iterations_url": null,
      "reduce_url": null,
      "nbr_coins": 1.23
    }
}
```

## restart

* **description**: Restart an already launched and stoped calculation
* **url**: ```https://api.zephy-science.com/v1/calculation/restart/```
* **method**: POST
* **parameters**:
  * **project_codename**: String, the project code name
  * **calculation_name**: String, the name of the calculation to create
  * **provider**: String, the provider to run the mesh computation (ex: "aws_eu")
  * **machine**: String, the machine type you want the mesh computation running on (ex: "c4.2xlarge")
  * **nbr_machines**: Int, the number of machines to instanciate
  * **nbr_iterations**: Int, the number of iterations
  * **split_results**: Bool, Optional, default FALSE. Do you want the results to be splitted in 3 files ?
  * A zip file containing the parameters of the computation to run
* **response**: Object with fields:
  * **job_id**: Int, the job id
  * **url**: String, the url of the data

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": {
      "job_id": 208
      "url": "https://..."
    }
}
```

## stop

* **description**: Stop a running calculation
* **url**: ```https://api.zephy-science.com/v1/calculation/stop/```
* **method**: POST
* **parameters**:
  * **project_codename**: String, the project code name
  * **calculation_name**: String, the name of the calculation to create
* **response**: String, "Ok"

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": "Ok"
}
```

## watch

* **description**: Update the db with mesh process duration results
* **url**: ```https://api.zephy-science.com/v1/calculation/watch/```
* **method**: POST
* **parameters**:
  * **ncells_fine**: Int, the number of cells for the fine mesh
  * **ncells_coarse**: Int, the number of cells for the coarse mesh
  * **zix**: Int, a variable characterizing the complexity of the terrain
  * **np**: Int, the number of processors that ran the process
  * **duration**: Int, the duration for the analysis process, in seconds
* **response**: Object, the information about the project, with fields:
  * **new_db**: Dictionnary reporting the changes in the db (providing a set of variables specific to the process)

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": {
       "new_db": {"a":1.,"b":1.,"e":1.}
    }
}
```

## remove

* **description**: delete a calculation
* **url**: ```https://api.zephy-science.com/v1/calculation/remove/```
* **method**: POST
* **parameters**:
  * **project_codename**: String, the project code name
  * **calculation_name**: String, the name of the calculation to create
* **response**: None

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": "ok"
}
```

## list

* **description**: List all calculations
* **url**: ```https://api.zephy-science.com/v1/calculation/list/```
* **method**: POST
* **parameters**:
  * **project_codename**: String, the project code name
  * **limit**: int, OPTIONAL, only received a limited amount of jobs
  * **offset**: int, OPTIONAL, skip the first jobs from the list
  * **order**: string, OPTIONAL, an SQL like formatted string to sort the results. Ex: `status ASC, name ASC`). The allowed order fields are:
     * **name**
     * **status**
* **response**: List of Objects, with fields:
  * **name**: String, the name of the calculation
  * **status**: String, status of the calculation, possible values are "pending", "computing", "computed", "canceled" and "stopped"

Example:

```json
{
    "success": 1,
    "error_msgs": [],
    "data": [
       {
         "name": "tristan-1556896266.23-f316f57d08344050a3f6f24b97df7048_D3150_S5_C1_ZS-Robust_M1_ZS-Coarse_Slope_Auto",
         "status": "computing"
       },
       {
         "name": "tristan-1556896266.23-f316f57d08344050a3f6f24b97df7048_D0850_S5_C1_ZS-Robust_M1_ZS-Coarse_Slope_Auto",
         "status": "computed"
       },
       ...
    ]
}
```
