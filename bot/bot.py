#!/usr/bin/python3
## -*- coding: utf-8 -*-


#	OmnomIRC COPYRIGHT 2010,2011 Netham45
#					   2012-2016 Sorunome
#
#	This file is part of OmnomIRC.
#
#	OmnomIRC is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	OmnomIRC is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with OmnomIRC.  If not, see <http://www.gnu.org/licenses/>.

import server,traceback,signal,json,time,pymysql,sys,re,oirc_include as oirc,os

try:
	import memcache
	memcached = memcache.Client(['127.0.0.1:11211'],debug=0)
except:
	class Memcached_fake:
		def get(self,str):
			return False
		def set(self,str,val,time=0):
			return False
		def delete(self,str):
			return False
	memcached = Memcached_fake()

#config handler
class Config:
	can_postload=False
	def __init__(self):
		self.readFile()
	def readFile(self):
		jsons = ''
		searchingJson = True
		f = open(oirc.DOCUMENTROOT+'/config.json.php')
		lines = f.readlines()
		f.close()
		for l in lines:
			if searchingJson:
				if l.strip()=='?>':
					searchingJson = False
			else:
				jsons += l + "\n"
		self.json = json.loads(jsons[:-1])
		if self.can_postload:
			self.postLoad()
	def postLoad(self):
		for i in range(len(self.json['networks'])):
			if self.json['networks'][i]['config'] == True:
				self.json['networks'][i]['config'] = sql.getVar('net_config_'+str(self.json['networks'][i]['id']))


#sql handler
class Sql:
	db = False
	def __init__(self):
		global config
	def fetchOneAssoc(self,cur):
		data = cur.fetchone()
		if data == None:
			return None
		desc = cur.description
		ret = {}
		for (name,value) in zip(desc,data):
			ret[name[0]] = value
		print(ret)
		return ret
	def getDbCursor(self):
		try:
			return self.db.cursor()
		except:
			print('(sql) creating new SQL connection...')
			try:
				self.db = pymysql.connect(
					host=config.json['sql']['server'],
					user=config.json['sql']['user'],
					password=config.json['sql']['passwd'],
					db=config.json['sql']['db'],
					unix_socket='/var/run/mysqld/mysqld.sock',
					charset='utf8',
					cursorclass=pymysql.cursors.DictCursor)
			except:
				self.db = pymysql.connect(
					host=config.json['sql']['server'],
					user=config.json['sql']['user'],
					password=config.json['sql']['passwd'],
					db=config.json['sql']['db'],
					charset='utf8',
					cursorclass=pymysql.cursors.DictCursor)
			return self.db.cursor()
	def query(self,q,p = []):
		try:
			
			cur = self.getDbCursor()
			cur.execute(q,tuple(p))
			self.db.commit()
			rows = []
			for row in cur:
				if row == None:
					break
				rows.append(row)
			cur.close()
			return rows
		except Exception as inst:
			print(config.json['sql'])
			print('(sql) Error',inst)
			traceback.print_exc()
			return False
	def getVar(self,var):
		res = self.query('SELECT value,type FROM irc_vars WHERE name=%s',[var])
		if isinstance(res,list) and len(res) > 0:
			res = res[0]
			if res['type'] == 0:
				return str(res['value'])
			if res['type'] == 1:
				return int(res['value'])
			if res['type'] == 2:
				return float(res['value'])
			if res['type'] == 3:
				try:
					return json.loads(res['value'])
				except:
					return False
			if res['type'] == 4:
				return bool(res['value'])
			if res['type'] == 5:
				try:
					return json.loads(res['value'])
				except:
					return False
			return False
		return False
	def close(self):
		try:
			self.db.close()
		except:
			pass


#fetch lines off of OIRC
class OIRCLink(server.ServerHandler):
	readbuffer = ''
	def recieve(self):
		try:
			data = oirc.makeUnicode(self.socket.recv(1024))
			if not data: # EOF
				return False
			self.readbuffer += data
		except:
			traceback.print_exc()
			return False
		temp = self.readbuffer.split('\n')
		self.readbuffer = temp.pop()
		for line in temp:
			try:
				data = json.loads(line)
				if data['t'] == 'server_updateconfig':
					handle.updateConfig()
				elif data['t'] == 'server_delete_modebuffer':
					handle.deleteModeBuffer(data['c'])
				else:
					print('(oirc)>> '+str(data))
					handle.sendToOther(data['n1'],data['n2'],data['t'],data['m'],data['c'],data['s'],data['uid'],False)
			except:
				traceback.print_exc()
		return True


#main handler
class Main():
	relayTypes = {}
	relays = []
	bots = []
	modeBuffer = {}
	def __init__(self):
		self.config = config
		self.sql = sql
		for f in os.listdir('.'):
			relay = re.match(r'^relay_(\w+)\.py$',f)
			if relay:
				relay = relay.group(1)
				print('(handle) Found relay',relay,'importing...')
				relay = __import__('relay_'+relay)
				self.relayTypes[relay.relayType] = {
					'class':relay.Relay,
					'defaultCfg':relay.defaultCfg
				}
	def updateCurline(self):
		global config,sql
		try:
			f = open(config.json['settings']['curidFilePath'],'w')
			f.write(str(sql.query("SELECT MAX(line_number) AS max FROM irc_lines")[0]['max']))
			f.close()
		except Exception as inst:
			print('(handle) curline error',inst)
			traceback.print_exc()
	def addUser(self,u,c,i,uid=-1):
		temp = sql.query("SELECT usernum,isOnline FROM irc_users WHERE username=%s AND channel=%s AND online=%s",[u,c,int(i)])
		if(len(temp)==0):
			sql.query("INSERT INTO `irc_users` (`username`,`channel`,`online`,`uid`) VALUES (%s,%s,%s,%s)",[u,c,int(i),int(uid)])
			return True
		else:
			sql.query("UPDATE `irc_users` SET `isOnline`=1,`uid`=%s,`time`=0 WHERE `usernum`=%s",[int(uid),int(temp[0]['usernum'])])
			return temp[0]['isOnline'] == 0
	def removeUser(self,u,c,i):
		sql.query("UPDATE `irc_users` SET `isOnline`=0 WHERE `username` = %s AND `channel` = %s AND online=%s",[u,c,int(i)])
	def timeoutUser(self,u,c,i):
		sql.query("UPDATE `irc_users` SET `time` = UNIX_TIMESTAMP(CURRENT_TIMESTAMP) WHERE `username` = %s AND `channel` = %s AND online=%s",[u,c,int(i)])
	def removeAllUsersChan(self,c,i):
		sql.query("UPDATE `irc_users` SET `isOnline`=0 WHERE `channel` = %s AND online=%s",[c,int(i)])
	def removeAllUsersNetwork(self,i):
		sql.query("UPDATE `irc_users` SET `isOnline`=0 WHERE `online`=%s",[int(i)])
	def getCurline(self):
		global config
		f = open(config.json['settings']['curidFilePath'])
		lines = f.readlines()
		f.close()
		if len(lines)>=1:
			return int(lines[0])
		return 0
	def deleteModeBuffer(self,chan):
		self.modeBuffer.pop(chan,False)
	def getModeString(self,chan):
		if chan in self.modeBuffer:
			return self.modeBuffer[chan]
		res = sql.query("SELECT `modes` FROM `irc_channels` WHERE chan=LOWER(%s)",[oirc.makeUnicode(chan)])
		if len(res)==0:
			self.modeBuffer[chan] = '+-'
			return '+-'
		self.modeBuffer[chan] = res[0]['modes']
		return res[0]['modes']
	def isChanOfMode(self,chan,char,default = False):
		res = self.getModeString(chan)
		try:
			char = res.index(char)
			minus = res.index('-')
		except:
			return default
		return char < minus
	def sendTopicToOther(self,s,c,i):
		oircOnly = False
		try:
			int(c)
		except:
			oircOnly = True
		for r in self.relays:
			if (oircOnly and r.relayType==1) or not oircOnly:
				r.relayTopic(s,c,i)
	def sendToOther(self,n1,n2,t,m,c,s,uid = -1,do_sql = True):
		if self.isChanOfMode(c,'c'):
			m = stripIrcColors(m)
		
		oircOnly = (t in ('join','part','quit') and uid!=-1)
		try:
			c = int(c)
		except:
			oircOnly = True
		for r in self.relays:
			if (oircOnly and r.relayType==1) or not oircOnly:
				try:
					r.relayMessage(n1,n2,t,m,c,s,uid)
				except:
					traceback.print_exc()
		
		print('(handle) (relay) '+str({'name1':n1,'name2':n2,'type':t,'message':m,'channel':c,'source':s,'uid':uid}))
		if do_sql:
			c = oirc.makeUnicode(str(c))
			sql.query("INSERT INTO `irc_lines` (`name1`,`name2`,`message`,`type`,`channel`,`time`,`online`,`uid`) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",[n1,n2,m,t,c,str(int(time.time())),int(s),uid])
			try:
				lines_cached = memcached.get('oirc_lines_'+c)
				if lines_cached:
					try:
						lines_cached = json.loads(lines_cached)
						if len(lines_cached) > 200:
							lines_cached.pop(0)
						lines_cached.append({
							'curLine': 0,
							'type': t,
							'network': int(s),
							'time': int(time.time()),
							'name': n1,
							'message': m,
							'name2': n2,
							'chan': c,
							'uid': uid
						})
						memcached.set('oirc_lines_'+c,json.dumps(lines_cached,separators=(',',':')),int(time.time())+(60*60*24*3))
					except:
						traceback.print_exc()
						memcached.delete('oirc_lines_'+c)
			except Exception as inst:
				print('(handle) (relay) ERROR: couldn\'t update memcached: ',inst)
			if t=='topic':
				memcached.set('oirc_topic_'+c,m)
				temp = sql.query("SELECT channum FROM `irc_channels` WHERE chan=%s",[c.lower()])
				if len(temp)==0:
					sql.query("INSERT INTO `irc_channels` (chan,topic) VALUES(%s,%s)",[c.lower(),m])
				else:
					sql.query("UPDATE `irc_channels` SET topic=%s WHERE chan=%s",[m,c.lower()])
			if t=='action' or t=='message':
				sql.query("UPDATE `irc_users` SET lastMsg=UNIX_TIMESTAMP(CURRENT_TIMESTAMP) WHERE username=%s AND channel=%s AND online=%s",[n1,c,int(s)])
		self.updateCurline()
	def findRelay(self,id):
		for r in self.relays:
			if id == r.id:
				return r
		return False
	def addRelay(self,n):
		if n['type']==-1: # websocket, we only allow one of this type!
			found = False
			for r in self.relays:
				if r.id == -1:
					found = True
					break
			if not found:
				self.relays.append(self.relayTypes[-1]['class'](n,handle))
		elif n['type'] in self.relayTypes:
			self.relays.append(self.relayTypes[n['type']]['class'](n,handle))
		
	def get_net_cheat(self):
		net_cheat = config.json['networks'][:]
		net_cheat = [{
			'id':-1,
			'type':-1,
			'enabled':config.json['websockets']['use'],
			'config':config.json['websockets']
		}] + net_cheat
		return net_cheat
	def updateConfig(self):
		print('(handle) Got signal to update config!')
		oldInternalSock = config.json['settings']['botSocket']
		config.readFile()
		
		if oldInternalSock != config.json['settings']['botSocket']:
			self.oircLink.stop()
			self.startOircLink()
		
		for n in self.get_net_cheat():
			r = self.findRelay(n['id'])
			if not n['enabled'] and r:
				r.stopRelay_wrap()
				self.relays.remove(r)
				continue
			if n['enabled']:
				if r:
					r.updateRelay_wrap(n)
				else:
					size_before = len(self.relays)
					self.addRelay(n)
					if size_before < len(self.relays):
						self.relays[len(self.relays)-1].startRelay_wrap() # start it straigt away!
	def sigquit(self,e,s):
		print('(handle) sigquit')
		self.quit()
	def startOircLink(self):
		sock = config.json['settings']['botSocket']
		if sock.startswith('unix:'):
			self.oircLink = server.Server(sock[5:],0,OIRCLink)
		else:
			res = re.match(r'^([\w\.]+):(\d+)',sock)
			if not res:
				print('(handle) ERROR: invalid internal socket ',sock)
				return False
			self.oircLink = server.Server(res.group(1),int(res.group(2)),OIRCLink)
		self.oircLink.start()
		return True
	def serve(self):
		signal.signal(signal.SIGQUIT,self.sigquit)
		self.calcNetwork = -1
		
		
		for n in self.get_net_cheat():
			if n['enabled']:
				self.addRelay(n)
		
		if not self.startOircLink():
			self.exit(42)
		
		try:
			for r in self.relays:
				r.startRelay_wrap()
			
			while True:
				time.sleep(30)
				r = oirc.execPhp('omnomirc.php',{'cleanUsers':''});
				if not r['success']:
					print('(handle) Something went wrong updating users...',r)
		except KeyboardInterrupt:
			print('(handle) KeyboardInterrupt, exiting...')
			self.quit()
		except:
			traceback.print_exc()
	def quit(self,code=1):
		global config
		for r in self.relays:
			r.stopRelay_wrap()
		for r in self.relays:
			r.joinThread()
		self.oircLink.stop()
		self.oircLink.join()
		sql.close()
		
		oirc.execPhp('admin.php',{'internalAction':'deactivateBot'})
		sys.exit(code)

if __name__ == "__main__":
	print('Starting OmnomIRC bot...')
	config = Config()
	oirc.execPhp('admin.php',{'internalAction':'activateBot'})
	sql = Sql()
	config.can_postload = True
	config.postLoad()
	handle = Main()
	handle.serve()