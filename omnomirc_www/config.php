<?php
/*
    OmnomIRC COPYRIGHT 2010,2011 Netham45
                       2012-2015 Sorunome

    This file is part of OmnomIRC.

    OmnomIRC is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    OmnomIRC is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with OmnomIRC.  If not, see <http://www.gnu.org/licenses/>.
*/

function getConfig(){
	$cfg = explode("\n",file_get_contents(realpath(dirname(__FILE__)).'/config.json.php'));
	$searchingJson = true;
	$json = "";
	foreach($cfg as $line){
		if($searchingJson){
			if(trim($line)=='//JSONSTART'){
				$searchingJson = false;
			}
		}else{
			if(trim($line)=='//JSONEND'){
				break;
			}
			$json .= "\n".$line;
		}
	}
	$json = implode("\n",explode("\n//",$json));
	return json_decode($json,true);
}
$config = getConfig();

if(isset($_GET['js'])){
	include_once(realpath(dirname(__FILE__)).'/omnomirc.php');
	header('Content-type: text/json');
	$channels = Array();
	foreach($config['channels'] as $chan){
		if($chan['enabled']){
			foreach($chan['networks'] as $cn){
				if($cn['id'] == $you->getNetwork()){
					$channels[] = Array(
						'chan' => $cn['name'],
						'high' => false,
						'ex' => $cn['hidden'],
						'id' => $chan['id'],
						'order' => $cn['order']
					);
				}
			}
		}
	}
	usort($channels,function($a,$b){
		if($a['order'] == $b['order']){
			return 0;
		}
		return (($a['order'] < $b['order'])?-1:1);
	});
	$net = $networks->get($you->getNetwork());
	$defaults = $net['config']['defaults'];
	$cl = $net['config']['checkLogin'];
	$ts = time();
	$cl .= '?sid='.urlencode(htmlspecialchars(str_replace(';','%^%',hash_hmac('sha512',(isset($_SERVER['HTTP_REFERER'])?$_SERVER['HTTP_REFERER']:'THE GAME'),$config['security']['sigKey'].$ts.$you->getNetwork()).'|'.$ts)));
	$dispNetworks = Array();
	foreach($config['networks'] as $n){
		$dispNetworks[] = Array(
			'id' => $n['id'],
			'normal' => $n['normal'],
			'userlist' => $n['userlist'],
			'name' => $n['name'],
			'type' => $n['type']
		);
	}
	echo json_encode(Array(
		'hostname' => $config['settings']['hostname'],
		'channels' => $channels,
		'smileys' => $vars->get('smileys'),
		'networks' => $dispNetworks,
		'network' => $you->getNetwork(),
		'checkLoginUrl' => $cl,
		'defaults' => $defaults,
		'websockets' => Array(
			'use' => $config['websockets']['use'],
			'host' => $config['websockets']['host'],
			'port' => $config['websockets']['port'],
			'ssl' => $config['websockets']['ssl']
		)
	));
}
?>
