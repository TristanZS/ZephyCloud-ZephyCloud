#!/usr/bin/env python2
# -*- coding: utf-8 -*-

ddprog={
	'anal':'CFD_ANALYSE.py',
	'mesh':'CFD_MESH_01.py',
	'calc':'CFD_CALC_01.py',
	'rose':'CFD_ROSE.py',
	'extra':'CFD_EXTRA.py',
	'assess':'CFD_ASSESS.py',
}

ddin,ddout=dict(),dict()
for chain in ddprog:
	ddin[chain],ddout[chain]=list(),dict()
	ddout[chain]['files'],ddout[chain]['folders'],ddout[chain]['tree'],ddout[chain]['remove']=list(),list(),list(),list()
	for _ in range(10):
		ddin[chain].append(dict())
		ddin[chain][-1]['files'],ddin[chain][-1]['folders'],ddin[chain][-1]['folders_to_projectscfd'],ddin[chain][-1]['tree'],ddin[chain][-1]['remove']=list(),list(),list(),list(),list()

#Analysis file operations definition
ddin['anal'][0]['folders'].append('/APPLI/')
ddin['anal'][0]['folders'].append('/PROJECTS_CFD/')
ddout['anal']['files'].append('contours.xml')
ddout['anal']['files'].append('centre')
ddout['anal']['folders'].append('/ANALYSE/')
ddout['anal']['folders'].append('/DATA/')
ddout['anal']['remove'].append('/DATA/zsoro')
ddout['anal']['remove'].append('/DATA/zsrou')
ddout['anal']['remove'].append('/DATA/zsoro.info')
ddout['anal']['remove'].append('/DATA/zsrou.info')
ddout['anal']['remove'].append('/DATA/zsmast')
ddout['anal']['remove'].append('/DATA/zswt')
ddout['anal']['remove'].append('/DATA/zslidar')
ddout['anal']['remove'].append('/DATA/zspoint')
ddout['anal']['remove'].append('/DATA/zsmeso')
ddout['anal']['remove'].append('/DATA/zsmapping')
for i in range(100): ddout['anal']['remove'].append('/DATA/prop_mapping_%s'%i)
for i in range(100): ddout['anal']['remove'].append('/DATA/loc_'+str(i).zfill(2))

#Mesh file operations definition
ddin['mesh'][0]['folders'].append('/APPLI/')
ddin['mesh'][0]['folders'].append('/PROJECTS_CFD/')
ddin['mesh'][1]['files'].append('/contours.xml')
ddin['mesh'][2]['folders'].append('/APPLI/')
ddin['mesh'][2]['folders'].append('/PROJECTS_CFD/')
ddin['mesh'][2]['files'].append('/contours.xml')
ddout['mesh']['folders'].append('/MESH/')

#Calc file operations definition

ddin['calc'][0]['folders'].append('/PROJECTS_CFD/')
ddin['calc'][1]['folders_to_projectscfd'].append('/ANALYSE/')
ddin['calc'][1]['folders_to_projectscfd'].append('/DATA/')
ddin['calc'][2]['folders_to_projectscfd'].append('/MESH/')
ddin['calc'][3]['folders'].append('/APPLI/')
ddin['calc'][3]['folders'].append('/PROJECTS_CFD/')
ddout['calc']['folders'].append('/CALC/')
