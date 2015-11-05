<?php

namespace omnimaga\OmnomIRC\migrations;

class release_1_0_0 extends \phpbb\db\migration\migration
{
	public function effectively_installed()
	{
		return isset($this->config['oirc_height']);
	}
	static public function depends_on()
	{
		return array('\phpbb\db\migration\data\v310\alpha2');
	}
	public function update_data()
	{
		global $oirc_config,$only_include_oirc;
		$only_include_oirc = true;
		include_once(realpath(dirname(__FILE__)).'/../checkLogin/index.php');
		if(isset($this->config['oirc_config_installed'])){
			$oirc_config['installed'] = $this->config['oirc_config_installed']?true:false;
			$oirc_config['sigKey'] = $this->config['oirc_config_sigKey'];
			$oirc_config['network'] = (int)$this->config['oirc_config_network'];
			$oirc_config['oircUrl'] = $this->config['oirc_config_oircUrl'];
			writeConfig();
		}
		return array(
			array('config.add', array('oirc_height', 280)),
			array('config.add', array('oirc_title', 'OmnomIRC Chat')),
			array('config.add', array('oirc_topics', true)),
			array('config.add', array('oirc_posts', true)),
			array('config.add', array('oirc_edits', true)),
			array('config.add', array('oirc_topicnotification', '{COLOR}10New topic by {COLOR}03{NAME} {COLOR}04{TOPIC} {COLOR}12/index.php?topic={TOPICID}')),
			array('config.add', array('oirc_postnotification', '{COLOR}10New post by {COLOR}03{NAME} {COLOR}10in {COLOR}04{TOPIC} {COLOR}12/index.php?topic={TOPICID}.msg{POSTID}#msg{POSTID}')),
			array('config.add', array('oirc_editnotification', '{COLOR}10Edit by {COLOR}03{NAME} {COLOR}10on {COLOR}04{TOPIC} {COLOR}12/index.php?topic={TOPICID}.msg{POSTID}#msg{POSTID}')),
			array('config.add', array('oirc_frameurl', '')),
			array('config.add', array('oirc_config_installed', $oirc_config['installed'])),
			array('config.add', array('oirc_config_sigKey', $oirc_config['sigKey'])),
			array('config.add', array('oirc_config_network', $oirc_config['network'])),
			array('config.add', array('oirc_config_oircUrl', $oirc_config['oircUrl'])),
			array('module.add', array(
				'acp',
				'ACP_CAT_DOT_MODS',
				'ACP_OIRC_TITLE'
			)),
			array('module.add', array(
				'acp',
				'ACP_OIRC_TITLE',
				array(
					'module_basename' => '\omnimaga\OmnomIRC\acp\main_module',
					'modes' => array('general','notifications','checklogin'),
				),
			)),
		);
	}
}
?>