# -*- coding: utf-8 -*-
#
# dFlash Plugin by gutemine
#
dflash_version="9.4.2 MOD for openATV"
#
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.config import config, ConfigSubsection, ConfigText, ConfigBoolean, ConfigInteger, ConfigSelection, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Plugins.Plugin import PluginDescriptor
from Components.Pixmap import Pixmap
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox 
from Screens.InputBox import InputBox
from Components.Input import Input
from Screens.ChoiceBox import ChoiceBox
from Components.AVSwitch import AVSwitch
from Components.SystemInfo import SystemInfo
from Screens.Console import Console                                                                           
from Components.MenuList import MenuList       
from enigma import  ePoint, getDesktop, quitMainloop, eConsoleAppContainer, eDVBVolumecontrol, eTimer, eActionMap
from Tools.LoadPixmap import LoadPixmap
import Screens.Standby  
import sys, os, struct, stat, time
from fcntl import ioctl
from struct import unpack
from array import array

from os import statvfs, path as os_path, chmod as os_chmod, write as os_write, open as os_open,\
		close as os_close, unlink as os_unlink
from twisted.web import resource, http
import gettext, datetime

dflash_plugindir="/usr/lib/enigma2/python/Plugins/Extensions/dFlash" 
dflash_pluginlink="/tmp/dFlash" 
dflash_bin="%s/bin" % dflash_pluginlink
dflash_busy="/tmp/.dflash"
dflash_script="/tmp/dflash.sh"
dflash_backup="/tmp/.dbackup"
dflash_backupscript="/tmp/dbackup.sh"
dflash_backuplog="/tmp/dbackup.log"
rambo_minpartsize=511
rambo_maxflash=2000

if not os.path.exists(dflash_pluginlink):
	os.symlink(dflash_plugindir,dflash_pluginlink)
# add local language file
dflash_sp=config.osd.language.value.split("_")
dflash_language = dflash_sp[0]
if os.path.exists("%s/locale/%s" % (dflash_plugindir,dflash_language)):
	_=gettext.Catalog('dflash', '%s/locale' % dflash_plugindir,dflash_sp).gettext

boxtype="dm7020hd"
if os.path.exists("/proc/stb/info/model"):
	f=open("/proc/stb/info/model")
	boxtype=f.read()
	f.close()
	boxtype=boxtype.replace("\n","").replace("\l","")
	
dflash_position=80

yes_no_descriptions = {False: _("no"), True: _("yes")}    

config.plugins.dflash = ConfigSubsection()
config.plugins.dflash.backuplocation = ConfigText(default = "/media/hdd/backup", fixed_size=False, visible_width=40)
config.plugins.dflash.sort = ConfigBoolean(default = True, descriptions=yes_no_descriptions)
config.plugins.dflash.keep = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
if boxtype != "dm7025":
	config.plugins.dflash.restart = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
else:
	config.plugins.dflash.restart = ConfigBoolean(default = True, descriptions=yes_no_descriptions)
config.plugins.dflash.loopswap = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
config.plugins.dflash.swapsize = ConfigInteger(default = 250, limits = (0, 2047))
config.plugins.dflash.position = ConfigInteger(default = dflash_position, limits = (-dflash_position, dflash_position))
config.plugins.dflash.ramfs = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
config.plugins.dflash.usr = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
config.plugins.dflash.squashfs = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
config.plugins.dflash.summary = ConfigBoolean(default = True, descriptions=yes_no_descriptions)
config.plugins.dflash.zip = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
if boxtype != "dm8000" and boxtype != "dm7020hd":
	config.plugins.dflash.summary.value = False
compression=[]
compression.append(( "lzo", _("lzo") ))
compression.append(( "zlib", _("zlib") ))
if boxtype == "dm8000" or boxtype == "dm7020hd":
	compression.append(( "none", _("none") ))
config.plugins.dflash.compression = ConfigSelection(default = "zlib", choices = compression)
config.plugins.dflash.extension = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
flashtools=[]
flashtools.append(( "writenfi", _("writenfi") ))
#flashtools.append(( "nfidump", _("nfidump") ))
flashtools.append(( "nandwrite", _("nandwrite") ))
if os.path.exists("/sbin/rambo"):
	flashtools.append(( "rambo", _("rambo") ))
	config.plugins.dflash.flashtool = ConfigSelection(default = "rambo", choices = flashtools)
else:
	config.plugins.dflash.flashtool = ConfigSelection(default = "writenfi", choices = flashtools)
if boxtype == "dm8000":
	if os.path.exists("/sbin/rambo"):
		config.plugins.dflash.volsize = ConfigInteger(default = 248, limits = (59, rambo_maxflash))
	else:
		config.plugins.dflash.volsize = ConfigInteger(default = 248, limits = (59, 248))
elif boxtype == "dm7020hd":
	if os.path.exists("/sbin/rambo"):
		config.plugins.dflash.volsize = ConfigInteger(default = 397, limits = (59, rambo_maxflash))
	else:
		config.plugins.dflash.volsize = ConfigInteger(default = 397, limits = (59, 960))
elif boxtype == "dm7020hdv2":
	if os.path.exists("/sbin/rambo"):
		config.plugins.dflash.volsize = ConfigInteger(default = 402, limits = (59, rambo_maxflash))
	else:
		config.plugins.dflash.volsize = ConfigInteger(default = 402, limits = (59, 960))
else:
	if os.path.exists("/sbin/rambo"):
		config.plugins.dflash.volsize = ConfigInteger(default = 59, limits = (40, rambo_maxflash))
	else:
		config.plugins.dflash.volsize = ConfigInteger(default = 59, limits = (40, 59))
config.plugins.dflash.console = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
config.plugins.dflash.subpage = ConfigBoolean(default = True, descriptions=yes_no_descriptions)
jcompression=[]                    
jcompression.append(( "zlib", _("zlib") ))
jcompression.append(( "none", _("none") ))
if boxtype == "dm8000" or boxtype == "dm7020hd":
	config.plugins.dflash.jffs2compression = ConfigSelection(default = "zlib", choices = jcompression)
#	config.plugins.dflash.jffs2compression = ConfigSelection(default = "none", choices = jcompression)
else:
	config.plugins.dflash.jffs2compression = ConfigSelection(default = "zlib", choices = jcompression)

ucompression=[]                    
ucompression.append(( "none", _("none") ))
ucompression.append(( "lzo", _("lzo") ))
ucompression.append(( "favor_lzo", _("favor_lzo") ))
ucompression.append(( "zlib", _("zlib") ))
ucompression.append(( "xz", _("xz") ))
if boxtype == "dm8000" or boxtype == "dm7020hd":
	config.plugins.dflash.ubifsrootcompression = ConfigSelection(default = "favor_lzo", choices = ucompression)
else:
	config.plugins.dflash.ubifsrootcompression = ConfigSelection(default = "zlib", choices = ucompression)
if boxtype == "dm8000" or boxtype == "dm7020hd":
	config.plugins.dflash.ubifsdatacompression = ConfigSelection(default = "favor_lzo", choices = ucompression)
else:
	config.plugins.dflash.ubifsdatacompression = ConfigSelection(default = "zlib", choices = ucompression)
config.plugins.dflash.databackup = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
if boxtype != "dm7025":
	config.plugins.dflash.fade = ConfigBoolean(default = True, descriptions=yes_no_descriptions)
else:
	config.plugins.dflash.fade = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
	
backuptools=[]
backuptools.append(( "mkfs.jffs2", _("mkfs.jffs2") ))
kernel="unknown"
for name in os.listdir("/lib/modules"):                          
	kernel = name
if boxtype != "dm800" and boxtype != "dm7025" and kernel.find("3.2") is not -1:
	# no ubifs in OE 1.6 and on old dm7025 and dm800pvr
	backuptools.append(( "mkfs.ubifs", _("mkfs.ubifs") ))
backuptools.append(( "nanddump", _("nanddump") ))
f=open("/proc/mounts","r")
mm=f.read()
f.close()
if mm.find("/ ubifs") is not -1 and boxtype != "dm800" and boxtype != "dm7025":
	config.plugins.dflash.backuptool = ConfigSelection(default = "mkfs.ubifs", choices = backuptools)
else:
	config.plugins.dflash.backuptool = ConfigSelection(default = "mkfs.jffs2", choices = backuptools)
config.plugins.dflash.overwrite = ConfigBoolean(default = False, descriptions=yes_no_descriptions)

fileupload_string=_("Select nfi image for flashing")
disclaimer_header=_("Disclaimer")
disclaimer_string=_("This way of flashing your Dreambox is potentially\ndangerous and not supported in any way from DMM.\n\nYou are using it completely at you own risk!\nIf you want to flash your Dreambox safely use the Webinterface or DreamUP!\n\nMay the Null modem cable be with you!")
disclaimer_wstring=disclaimer_string.replace("\n","<br>")
plugin_string=_("direct Flash Plugin by gutemine Version %s") % dflash_version
waiting_string=_("%i MB Swapspace OK") % config.plugins.dflash.swapsize.value
flashing_string=_("Flashing") 
backup_string=_("Backup") 
setup_string=_("Configuring")
checking_string=_("Checking")
running_string=_("dFlash is busy ...")
backupimage_string=_("Enter Backup Imagename")
backupdirectory_string=_("Enter Backup Path")
unsupported_string=_("Sorry, currently not supported on this Dreambox type")
nonfi_string=_("Sorry, no correct nfi file selected")
nonfiunzip_string=_("Sorry, no nfi file unzipped")
badblocks_string=_("Sorry, bad blocks in %s Flash, better try DreamUP with recover bad sectors")
refresh_string=_("Refresh")
mounted_string=_("Nothing mounted at %s")
barryallen_string=_("Sorry, use Barry Allen for Backup")
lowfat_string=_("Sorry, use LowFAT for Backup")
dumbo_string=_("Sorry, use Dumbo for Backup")

header_string  =""
header_string +="<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.01 Transitional//EN\""
header_string +="\"http://www.w3.org/TR/html4/loose.dtd\">"
header_string +="<head><title>%s</title>" % plugin_string
header_string +="<link rel=\"shortcut icon\" type=\"/web-data/image/x-icon\" href=\"/web-data/img/favicon.ico\">"
header_string +="<meta content=\"text/html; charset=UTF-8\" http-equiv=\"content-type\">"
header_string +="</head><body bgcolor=\"black\">"
header_string +="<font face=\"Tahoma, Arial, Helvetica\" color=\"yellow\">"
header_string +="<font size=\"3\" color=\"yellow\">"

dflash_backbutton=_("use back button in browser and try again!") 
dflash_flashing=""
dflash_flashing += header_string
dflash_flashing += "<br>%s ...<br><br>" % flashing_string
dflash_flashing +="<br><img src=\"/web-data/img/dflash.png\" alt=\"%s ...\"/><br><br>" % (flashing_string)

dflash_backuping  =""
dflash_backuping += header_string
dflash_backuping += "<br>%s<br><br>" % running_string
dflash_backuping +="<br><img src=\"/web-data/img/ring.png\" alt=\"%s ...\"/><br><br>" % (backup_string)
dflash_backuping +="<form method=\"GET\">"
dflash_backuping +="<input name=\"command\" type=\"submit\" size=\"100px\" title=\"%s\" value=\"%s\">" % (refresh_string,"Refresh")
dflash_backuping +="</form>"                        

class dFlash(Screen):
	skin = """
		<screen position="center,80" size="680,60" title="Flashing" >
		<widget name="logo" position="10,10" size="100,40" transparent="1" alphatest="on" />
		<widget name="buttonred" position="120,10" size="130,40" backgroundColor="red" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
		<widget name="buttongreen" position="260,10" size="130,40" backgroundColor="green" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
		<widget name="buttonyellow" position="400,10" size="130,40" backgroundColor="yellow" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
		<widget name="buttonblue" position="540,10" size="130,40" backgroundColor="blue" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
	</screen>"""
	def __init__(self, session, args = 0):
		Screen.__init__(self, session)
		self.onShown.append(self.setWindowTitle)      
		self.onLayoutFinish.append(self.byLayoutEnd)
		self["logo"] = Pixmap()
		self["buttonred"] = Label(_("Cancel"))
		self["buttongreen"] = Label(_("Backup"))
		self["buttonyellow"] = Label(_("Flashing"))
		self["buttonblue"] = Label(setup_string)
		
		self.dimmed=30
		eActionMap.getInstance().bindAction('', -0x7FFFFFFF, self.doUnhide)
		        
		self["actions"] = ActionMap([ "dFlashActions", "ColorActions" ],
			{
			"green": self.backup,
			"red": self.leaving,
			"blue": self.config,
			"yellow": self.flash,
			"save": self.leaving,
			"cancel": self.leaving,
			})

	def setWindowTitle(self):
		if os.path.exists(dflash_busy):                                                                   
			self["logo"].instance.setPixmapFromFile("%s/ring.png" % dflash_plugindir)
		else:                                                                            
			self["logo"].instance.setPixmapFromFile("%s/dflash.png" % dflash_plugindir)
		self.setTitle(flashing_string+" & "+backup_string+" V%s" % dflash_version)

	def byLayoutEnd(self):
		self["logo"].instance.setPixmapFromFile("%s/dflash.png" % dflash_plugindir)

	def leaving(self):
		if os.path.exists(dflash_busy):
			self.session.open(MessageBox, running_string, MessageBox.TYPE_ERROR)
		else:
			config.plugins.dflash.position.save()
			eActionMap.getInstance().unbindAction('', self.doUnhide)
			self.close()

	def checking(self):      
		self.session.open(dFlashChecking)

	def doHide(self):
		if config.plugins.dflash.fade.value:
			print "[dFLASH] hiding"
			self.dimmed=30
			self.DimmingTimer = eTimer()
			self.DimmingTimer.callback.append(self.doDimming)
			self.DimmingTimer.start(5000, True)
		else:
			print "[dFLASH] no hiding"

	def doDimming(self):
		self.dimmed=self.dimmed-1
		self.DimmingTimer.stop()
		if self.dimmed > 0:
			f=open("/proc/stb/video/alpha","w")
			f.write("%i" % (config.osd.alpha.getValue()*self.dimmed/30))
			f.close()
		self.DimmingTimer.start(100, True)

	def doUnhide(self, key, flag):                                                                 
		print "[dFLASH] unhiding"
		if config.plugins.dflash.fade.value:
			if self.dimmed < 30:
				f=open("/proc/stb/video/alpha","w")
				f.write("%i" % (config.osd.alpha.getValue()))
				f.close()
		if os.path.exists(dflash_busy):
			self.doHide()
		else:
			print "[dFLASH] no unhiding"

	def flash(self):
		if os.path.exists(dflash_busy):
			self.session.open(MessageBox, running_string, MessageBox.TYPE_ERROR)
		else:
			f=open("/proc/stb/info/model")
			self.boxtype=f.read()
			f.close()
			self.boxtype=self.boxtype.replace("\n","").replace("\l","")
			if self.boxtype == "dm7025":
				self.session.open(MessageBox, unsupported_string, MessageBox.TYPE_ERROR)
			else:
				self.session.openWithCallback(self.askForImage, ChoiceBox, title=fileupload_string, list=self.getImageList())

	def askForImage(self,image):
		if image is None:
			self.session.open(MessageBox, nonfi_string, MessageBox.TYPE_ERROR)
		else:
			self.nfiname=image[0]
			self.nfifile=image[1]
			self.nfidirectory=self.nfifile.replace(self.nfiname,"").replace(".nfi.zip","")
			if self.nfifile.endswith(".nfi.zip"):
				self.session.openWithCallback(self.startUnzip,MessageBox,_("Are you sure that you want to unzip %s ?") %(self.nfifile), MessageBox.TYPE_YESNO)
			else:
				self.unzipDone(False)                                                                        

	def startUnzip(self,option):                     
		if option is False:
			self.session.open(MessageBox, _("Sorry, unzip of %s was canceled!") % self.nfifile, MessageBox.TYPE_ERROR)
		else:
			# now do the unzip
			os.system("touch %s" % dflash_busy)                                                            
			command="unzip -o %s -d %s" % (self.nfifile, self.nfidirectory)
			print "[dFLASH] unzip command: %s\n" % command
			self.container = eConsoleAppContainer()                                                        
			self.container.appClosed.append(self.unzipDone)                                                                        
			self.container.execute(command)                                                           

	def unzipDone(self,status):                     
		print "[dFLASH] unzip status %d\n" % status
		if os.path.exists(dflash_busy):
			os.remove(dflash_busy)
		self.nfizipfile="none"
		if self.nfifile.endswith(".zip"):
			self.nfizipfile=self.nfifile
			self.nfifile=self.nfizipfile.replace(".nfi.zip",".nfi")
		if status or not os.path.exists(self.nfifile):
			self.session.open(MessageBox, nonfiunzip_string, MessageBox.TYPE_ERROR)
		else:
			if os.path.exists(self.nfizipfile):
				os.remove(self.nfizipfile)
			nfisize=os.path.getsize(self.nfifile)	
			print "[dFLASH] nfi file size %i" % nfisize
			f = open(self.nfifile,"r")
			header = f.read(32)     
			f.close()
			machine_type = header[4:4+header[4:].find("\0")]                        
			b=open("/proc/stb/info/model","r")
			dreambox=b.read().rstrip("\n")
			b.close()
			if os.path.exists("/var/lib/opkg/status"):
				v = open("/var/lib/opkg/status","r")
			else:
				v = open("/usr/lib/opkg/status","r")
			line = v.readline()     
			found=False
			loaderversion=0
			while (line) and not found:                                                                   
				line = v.readline()                                                
				if line.startswith("Package: dreambox-secondstage"):                                            
					found=True                                                  
					line = v.readline()                                                
					line=line.replace("Version: ","")
					loader=line.split("-")
					loaderversion=int(loader[0])
			v.close()
			# Flash
			flashdev="/dev/mtd/0"
			if os.path.exists("/dev/mtd0"):
				flashdev="/dev/mtd0"
			fd=open(flashdev) 
			mtd_info = array('c',"                                ")
			memgetinfo=0x40204D01
			ioctl(fd.fileno(), memgetinfo, mtd_info)
			fd.close()
			tuple=unpack('HLLLLLLL',mtd_info)
			self.blocksize="%d" % tuple[4]
			print "[dFLASH] %s %s %i %s %s" % (machine_type,dreambox,loaderversion,header[:4],self.blocksize)
			if machine_type.startswith(dreambox) is False and dreambox is not "dm7020":                                        
				print "[dFLASH] wrong header"
				self.session.open(MessageBox, nonfi_string, MessageBox.TYPE_ERROR)
			elif (dreambox == "dm800" or dreambox == "dm800se" or dreambox == "dm500hd" or dreambox == "dm7020hd") and loaderversion < 84 and header[:4] == "NFI2":
				print "[dFLASH] wrong header"
				self.session.open(MessageBox, nonfi_string, MessageBox.TYPE_ERROR)
			elif (dreambox == "dm7020hd") and loaderversion < 87 and header[:4] == "NFI3":
				print "[dFLASH] wrong header"
				self.session.open(MessageBox, nonfi_string, MessageBox.TYPE_ERROR)
			elif (dreambox == "dm800" or dreambox == "dm800se" or dreambox == "dm500hd" or dreambox == "dm7020hd") and loaderversion >= 84 and header[:4] != "NFI2":
				print "[dFLASH] wrong header"
				self.session.open(MessageBox, nonfi_string, MessageBox.TYPE_ERROR)
			elif dreambox == "dm8000" and header[:4] != "NFI1":
				print "[dFLASH] wrong header"
				self.session.open(MessageBox, nonfi_string, MessageBox.TYPE_ERROR)
			elif dreambox == "dm7020hd" and header[:4] == "NFI3" and self.blocksize == "4096":
				print "[dFLASH] wrong header"
				self.session.open(MessageBox, nonfi_string, MessageBox.TYPE_ERROR)
			else:
				if config.plugins.dflash.flashtool.value == "rambo":
					self.session.openWithCallback(self.askForDevice,ChoiceBox,title=_("choose rambo device"),list=self.getDeviceList())
				else:
					self.session.openWithCallback(self.startFlash,MessageBox,_("Are you sure that you want to flash now %s ?") %(self.nfifile), MessageBox.TYPE_YESNO)

	def getImageList(self):                                               
		list = []
		for name in os.listdir("/tmp"):
			if name.endswith(".nfi") or name.endswith(".nfi.zip"):
				list.append(( name.replace(".nfi.zip","").replace(".nfi",""), "/tmp/%s" % name ))                         
				if config.plugins.dflash.sort.value:
					list.sort()
				return list
		if not config.plugins.dflash.backuplocation.value.startswith("/media/net") or config.plugins.dflash.ramfs.value:
			if os.path.exists(config.plugins.dflash.backuplocation.value):
				for name in os.listdir(config.plugins.dflash.backuplocation.value):
					if name.endswith(".nfi") or name.endswith(".nfi.zip"):
						list.append(( name.replace(".nfi.zip","").replace(".nfi",""), "%s/%s" % (config.plugins.dflash.backuplocation.value,name)))                         
			for directory in os.listdir("/media"):
				if os.path.exists("/media/%s" % directory) and os.path.isdir("/media/%s" % directory) and directory.endswith("net") is False and directory.endswith("hdd") is False:
					for name in os.listdir("/media/%s" % directory):
						if name.endswith(".nfi") or name.endswith(".nfi.zip"):
							list.append(( name.replace(".nfi.zip","").replace(".nfi",""), "/media/%s/%s" % (directory,name) ))                         
		if config.plugins.dflash.sort.value:
			list.sort()
			return list                                                

	def startFlash(self,option):
		if option is False:
			self.session.open(MessageBox, _("Sorry, Flashing of %s was canceled!") % self.nfifile, MessageBox.TYPE_ERROR)
		else:
			CreateScript()
			self.session.openWithCallback(self.doFlash, MessageBox, _("Press OK now for flashing\n\n%s\n\nBox will reboot automatically when finished!") % self.nfifile, MessageBox.TYPE_INFO)
				
	def getDeviceList(self):                                                                                                                     
		found=False                                                                                                                             
		s=open("/proc/swaps","r")                                                                                                          
		swaps=s.read()
		s.close()
		f=open("/proc/partitions","r")                                                                                                          
		devlist= []                                                                                                                          
		line = f.readline()                                                                                                                  
		line = f.readline()                                                                                                                  
		sp=[]                                                                                                                
		while (line):                                                                                                                        
			line = f.readline()                                                                                                          
			if line.find("sd") is not -1:                                                                                                  
				sp=line.split()                                                                                                   
				print sp
				devsize=int(sp[2])                                                                                       
				mbsize=devsize/1024                                                                                      
				devname="/dev/%s" % sp[3]                                                                                        
				print devname, devsize
				if len(devname) > 8 and mbsize > rambo_minpartsize and swaps.find(devname) is -1:
					found=True
					devlist.append(("%s %d %s" % (devname,mbsize,"MB"), devname,mbsize))
				f.close()                                                                                         
				if not found:                                                                                    
					devlist.append(("no device found, shutdown, add device and reboot" , "nodev", 0))         
				return devlist                                                                                    

	def askForDevice(self,device):                                                                            
		if device is None:                                                                                
			self.session.open(MessageBox, _("Sorry, no device choosen"), MessageBox.TYPE_ERROR)
		elif device[1] == "nodev":                                                                        
			self.session.open(MessageBox, _("Sorry, no device found"), MessageBox.TYPE_ERROR)
		else:                                                                                             
			self.device=device[1]                                                                                                         
			self.session.openWithCallback(self.ramboFlash,MessageBox,_("Are you sure that you want to flash now %s ?") %(self.nfifile), MessageBox.TYPE_YESNO)

	def ramboFlash(self,option):                                                                            
		if option is False:
			self.session.open(MessageBox, _("Sorry, Flashing of %s was canceled!") % self.nfifile, MessageBox.TYPE_ERROR)
		else:
			os.system("touch %s" % dflash_busy)                                                            
			if not os.path.exists("/tmp/rambo"):
				os.mkdir("/tmp/rambo")
				os.system("umount /tmp/rambo")                                                            
				os.system("mount %s /tmp/rambo" % self.device)                                                            
				f=open("/proc/mounts", "r")
				m = f.read()                                                    
				f.close()
				if m.find("/tmp/rambo") is not -1:
					self["logo"].instance.setPixmapFromFile("%s/ring.png" % dflash_plugindir)                      
					for name in os.listdir("/tmp/rambo"):                                                          
						if name.endswith(".nfi"):                                                              
							os.remove("/tmp/rambo/%s" % name)                                              
							command="cp %s /tmp/rambo/%s.nfi" % (self.nfifile,self.nfiname)                                
							self.container = eConsoleAppContainer()                                                        
							self.container.appClosed.append(self.copyDone)                                                                        
							self.container.execute(command)                                                           
				else:
					if os.path.exists(dflash_busy):
						os.remove(dflash_busy)
					self.session.open(MessageBox, _("Sorry, %s device not mounted") % self.device, MessageBox.TYPE_ERROR)

	def copyDone(self,status):                     
		if os.path.exists(dflash_busy):
			os.remove(dflash_busy)
		self["logo"].instance.setPixmapFromFile("%s/dflash.png" % dflash_plugindir)
		result=_("Copied %s.nfi to %s,\nreboot for activating it ?") % (self.nfiname,self.device)                                    
		self.session.openWithCallback(self.doreboot,MessageBox, result, MessageBox.TYPE_YESNO)              

	def doreboot(self,answer):                                                                                                                            
		if answer is True:                                                                                                                            
			quitMainloop(2)                 

	def doFlash(self,option):
		if option:
			print "[dFLASH] is flashing now %s" % self.nfifile
			if (eDVBVolumecontrol.getInstance().isMuted()) is False:
				eDVBVolumecontrol.getInstance().volumeToggleMute()
			self.avswitch = AVSwitch()
			if SystemInfo["ScartSwitch"]:
				self.avswitch.setInput("SCART")
			else:
				self.avswitch.setInput("AUX")
			print "[dFLASH] is flashing now %s" % self.nfifile
			os.system("start-stop-daemon -S -b -x %s \"%s\"" % (dflash_script,self.nfifile))
			self.FlashTimer = eTimer()
			self.FlashTimer.stop()
			self.FlashTimer.timeout.get().append(self.secondFlash)
			self.FlashTimer.start(60000,True)
		else:
			print "[dFLASH] cancelled flashing %s" % self.nfifile

	def secondFlash(self):
		print "[dFLASH] second flashing now %s" % self.nfifile
		os.system("%s \"%s\" &" % (dflash_script,self.nfifile))
		self.FlashTimer.stop()

	def cancel(self):
		self.close(False)

	def backup(self):
		if os.path.exists(dflash_backup):
			print "[dFLASH] found finished backup ..."
			self.TimerBackup = eTimer()                                       
			self.TimerBackup.stop()                                           
			if os.path.exists(dflash_busy):
				os.remove(dflash_busy)
			if os.path.exists(dflash_backupscript) and not config.plugins.dflash.keep.value:
				os.remove(dflash_backupscript)
			if config.plugins.dflash.fade.value:
				f=open("/proc/stb/video/alpha","w")
				f.write("%i" % (config.osd.alpha.getValue()))
				f.close()
			f=open(dflash_backup)
			line=f.readline()
			f.close()
			os.remove(dflash_backup)
			sp=[]
			sp=line.split("	")
			print sp
			length=len(sp)
			size=""
			image=""
			path=""
			if length > 0:
				size=sp[0].rstrip().lstrip()
				sp2=[]
				sp2=sp[length-1].split("/")
				print sp2
				length=len(sp2)
				if length > 0:
					image=sp2[length-1]
					path=line.replace(size,"").replace(image,"")
					image=image.replace(".nfi\n","")
					image=image.rstrip().lstrip()
			print "[dFLASH] found backup %s" % line
			self.session.open(MessageBox,size+"B "+_("Flash Backup to %s finished with imagename:\n\n%s.nfi") % (path,image),  MessageBox.TYPE_INFO)                 
		else:
			if os.path.exists(dflash_busy):
				self.session.open(MessageBox, running_string, MessageBox.TYPE_ERROR)
			elif os.path.exists("/.bainfo"):
				self.session.open(MessageBox, barryallen_string, MessageBox.TYPE_ERROR)
			elif os.path.exists("/.lfinfo"):
				self.session.open(MessageBox, lowfat_string, MessageBox.TYPE_ERROR)
			elif os.path.exists("/dev/disk/by-label/TIMOTHY") and not os.path.exists("/boot/autoexec.bat"):
				self.session.open(MessageBox, dumbo_string, MessageBox.TYPE_ERROR)
			else:
				self.session.openWithCallback(self.askForBackupPath,InputBox, title=backupdirectory_string, text="%s                                 " % config.plugins.dflash.backuplocation.value, maxSize=48, type=Input.TEXT)

	def askForBackupPath(self,path):
		if path is None:
			self.session.open(MessageBox,_("nothing entered"),  MessageBox.TYPE_ERROR)                 
		else:
			sp=[]
			sp=path.split("/")
			print sp
			if len(sp) > 1:
				if sp[1] != "media":
					self.session.open(MessageBox,mounted_string % path,  MessageBox.TYPE_ERROR)                 
					return
			mounted=False
			self.swappable=False
			sp2=[]
			f=open("/proc/mounts", "r")
			m = f.readline()                                                    
			while (m) and not mounted:
				if m.find("/%s/%s" % (sp[1],sp[2])) is not -1:
					mounted=True
					print m
					sp2=m.split(" ")
					print sp2
					if sp2[2].startswith("ext") or sp2[2].startswith("xfs") or sp2[2].endswith("fat"):
						print "[dFlash] swappable"
						self.swappable=True
				m = f.readline()                                                 
			f.close()		
			if not mounted:
				self.session.open(MessageBox,mounted_string % path,  MessageBox.TYPE_ERROR)                 
				return
			path=path.lstrip().rstrip().replace(" ","")
			config.plugins.dflash.backuplocation.value=path
			config.plugins.dflash.backuplocation.save()
			if not os.path.exists(config.plugins.dflash.backuplocation.value):
				os.mkdir(config.plugins.dflash.backuplocation.value,0777)
			f=open("/proc/stb/info/model")
			self.boxtype=f.read()
			f.close()
			self.boxtype=self.boxtype.replace("\n","").replace("\l","")
			name="OE"
			if os.path.exists("/etc/image-version"):
				f=open("/etc/image-version")
				line = f.readline()                                                    
				while (line):                                             
					line = f.readline()                                                 
					if line.startswith("creator="):                                    
						name=line
				f.close()                                                              
				name=name.replace("creator=","")
				sp=[]
				if len(name) > 0:
					sp=name.split(" ")
					if len(sp) > 0:
						name=sp[0]
						name=name.replace("\n","")
			self.creator=name.rstrip().lstrip()
			self.imagetype="exp"
			if name == "OoZooN" and os.path.exists("/etc/issue.net"):
				f=open("/etc/issue.net")
				i=f.read()
				f.close()
				if i.find("xperimental") is -1:
					self.imagetype="rel"
			name=name+"-"+self.imagetype
			self.session.openWithCallback(self.askForBackupName,InputBox, title=backupimage_string, text="%s-%s-%s-%s                        " % (name,self.boxtype,datetime.date.today(),time.strftime("%H-%M")), maxSize=40, type=Input.TEXT)

        def askForBackupName(self,name):
           if name is None:
              self.session.open(MessageBox,_("nothing entered"),  MessageBox.TYPE_ERROR)                 
           else:
	      self.backupname=name.replace(" ","").replace("[","").replace("]","").replace(">","").replace("<","").replace("|","").rstrip().lstrip()
      	      if os.path.exists("%s/%s.nfi" % (config.plugins.dflash.backuplocation.value,self.backupname)):
               		self.session.openWithCallback(self.confirmedBackup,MessageBox,"%s.nfi" % self.backupname +"\n"+_("already exists,")+" "+_("overwrite ?"), MessageBox.TYPE_YESNO)
	      else:
			self.confirmedBackup(True)

        def confirmedBackup(self,answer):
	      if answer is True:
	      	 if os.path.exists("%s/%s.nfi" % (config.plugins.dflash.backuplocation.value,self.backupname)):
	      		os.remove("%s/%s.nfi" % (config.plugins.dflash.backuplocation.value,self.backupname))
	      	 if os.path.exists("%s/%s.nfo" % (config.plugins.dflash.backuplocation.value,self.backupname)):
	      		os.remove("%s/%s.nfo" % (config.plugins.dflash.backuplocation.value,self.backupname))
	      	 # check if swapfile too small
	         fm=open("/proc/meminfo")                                                
       	         line = fm.readline()                                                    
       	         swapspace=0                                                                  
                 while (line):                                             
           	    line = fm.readline()                                                 
           	    if line.startswith("SwapTotal:"):                                    
              		swapspace=int(line.replace("SwapTotal: ","").replace("kB",""))/1000             
                 fm.close()                                                              
	         print "[dFLASH] swapspace: %i MB" % swapspace
		 self.ownswap=False
	         if swapspace < config.plugins.dflash.swapsize.value: 
			if self.swappable or config.plugins.dflash.loopswap.value:
		 		action_string=_("\n\nUsing temporary swapspace.")
		 	else:
		 		action_string=_("\n\nEnigma2 will restart due to lack of swapspace,\ncheck result with Backup in Plugin afterwards.")
	         elif config.plugins.dflash.swapsize.value == 0: 
		 	action_string=_("\n\nWithout swapspace.")
			self.ownswap=True
		 else:
		 	action_string=_("\n\nUsing existing swapspace.")
			self.ownswap=True
                 self.session.openWithCallback(self.startBackup,MessageBox, _("Press OK for starting backup to\n\n%s.nfi\n\nBe patient, this takes 5-10min ... ") % self.backupname + action_string, MessageBox.TYPE_INFO)
	      else:
              	 self.session.open(MessageBox,_("not confirmed"),  MessageBox.TYPE_ERROR)                 
		
        def startBackup(self,answer):
              if answer is True:
	         print "[dFLASH] is backuping now ..."
                 self["logo"].instance.setPixmapFromFile("%s/ring.png" % dflash_plugindir)
                 self.doHide()
	         BackupImage(self.session,self.backupname,self.imagetype,self.creator,self.swappable,self.ownswap)

	def config(self):
	        if os.path.exists(dflash_busy):
			self.session.open(MessageBox, running_string, MessageBox.TYPE_ERROR)
		else:
        	 	self.session.open(dFlashConfiguration)

def startdFlash(session, **kwargs):
       	session.open(dFlash)   

def autostart(reason,**kwargs):
        if kwargs.has_key("session") and reason == 0:           
		session = kwargs["session"]                       
		print "[dFLASH] autostart"
		if os.path.exists(dflash_busy):
			os.remove(dflash_busy)

def sessionstart(reason, **kwargs):                                               
        if reason == 0 and "session" in kwargs:                                                        
		if os.path.exists("/usr/lib/enigma2/python/Plugins/Extensions/WebInterface/WebChilds/Toplevel.pyo"):
                        from Plugins.Extensions.WebInterface.WebChilds.Toplevel import addExternalChild
                        addExternalChild( ("dflash", wFlash(), "dFlash", "1", True) )          
                else:                                                                                  
			print "[dFLASH] Webif not found"
			
def Plugins(**kwargs):
	return [PluginDescriptor(where = [PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART], fnc = autostart),
			PluginDescriptor(name=flashing_string, description=flashing_string+" & "+backup_string, where = PluginDescriptor.WHERE_PLUGINMENU, icon="dflash.png" , fnc=startdFlash),
            PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart, needsRestart=False)
			]

def mainconf(menuid):
    if menuid != "setup":                                                  
        return [ ]                                                     
    return [(flashing_string+" & "+backup_string, startdFlash, "dflash", None)]                                                 
   

###############################################################################
# dFlash Webinterface by gutemine
###############################################################################

class wFlash(resource.Resource):

	def render_GET(self, req):
		file = req.args.get("file",None)
		directory = req.args.get("directory",None)
		command = req.args.get("command",None)
		print "[dFLASH] received %s %s %s" % (command,directory,file)
		req.setResponseCode(http.OK)
		req.setHeader('Content-type', 'text/html')
                req.setHeader('charset', 'UTF-8')
		if os.path.exists("/usr/lib/enigma2/python/Plugins/Extensions/WebInterface/web-data/img/dflash.png") is False:
			os.symlink("%s/dflash.png" % dflash_plugindir,"/usr/lib/enigma2/python/Plugins/Extensions/WebInterface/web-data/img/dflash.png")
		if os.path.exists("/usr/lib/enigma2/python/Plugins/Extensions/WebInterface/web-data/img/ring.png") is False:
			os.symlink("%s/ring.png" % dflash_plugindir,"/usr/lib/enigma2/python/Plugins/Extensions/WebInterface/web-data/img/ring.png")
		if os.path.exists(dflash_busy):
			return header_string+dflash_backuping
		if command is None or command[0] == "Refresh":
		        fm=open("/proc/meminfo")                                                
       		 	line = fm.readline()                                                    
       		 	swapspace=0                                                                  
			line=True
        		while (line):                                             
           			line = fm.readline()                                                 
           			if line.startswith("SwapTotal:"):                                    
              				swapspace=int(line.replace("SwapTotal: ","").replace("kB",""))/1000             
        		fm.close()                                                              
			b=open("/proc/stb/info/model","r")
			dreambox=b.read().rstrip("\n")
			b.close()
			htmlnfi=""
			entries=os.listdir("/tmp")
	 		for name in sorted(entries):                          
				if name.endswith(".nfi"):
       			       		name=name.replace(".nfi","")                        
					htmlnfi += "<option value=\"/tmp/%s.nfi\" class=\"black\">%s</option>\n" % (name,name)
			if not config.plugins.dflash.backuplocation.value.startswith("/media/net") or config.plugins.dflash.ramfs.value:
				if os.path.exists(config.plugins.dflash.backuplocation.value):
					entries=os.listdir(config.plugins.dflash.backuplocation.value)
       					for name in sorted(entries):                          
						if name.endswith(".nfi"):
       	 	      					name=name.replace(".nfi","")                        
							htmlnfi += "<option value=\"%s/%s.nfi\" class=\"black\">%s</option>\n" % (config.plugins.dflash.backuplocation.value,name,name)
			entries=os.listdir("/media")
       			for directory in sorted(entries):                          
				if os.path.exists("/media/%s" % directory) and os.path.isdir("/media/%s" % directory) and directory.endswith("net") is False and directory.endswith("hdd") is False:
       					for name in os.listdir("/media/%s" % directory):                          
						if name.endswith(".nfi"):
        	 	      				name=name.replace(".nfi","")                        
							htmlnfi += "<option value=\"%s/%s.nfi\" class=\"black\">%s</option>\n" % (directory,name,name)
  			f=open("/proc/stb/info/model")
  			self.boxtype=f.read()
  			f.close()
  			self.boxtype=self.boxtype.replace("\n","").replace("\l","")
			name="OE"
			if os.path.exists("/etc/image-version"):
				f=open("/etc/image-version")
	 			line = f.readline()                                                    
        			while (line):                                             
        				line = f.readline()                                                 
        				if line.startswith("creator="):                                    
						name=line
        			f.close()                                                              
				name=name.replace("creator=","")
				sp=[]
				if len(name) > 0:
					sp=name.split(" ")
					if len(sp) > 0:
						name=sp[0]
						name=name.replace("\n","")
			self.creator=name.rstrip().lstrip()
			self.imagetype="exp"
			if name == "OoZooN" and os.path.exists("/etc/issue.net"):
				f=open("/etc/issue.net")
				i=f.read()
				f.close()
				if i.find("xperimental") is -1:
					self.imagetype="rel"
			name=name+"-"+self.imagetype
		 	return """
				<html>
				%s<br>
				<u>%s</u><br><br>
				%s:<br><br>
                                %s<hr>
				%s @ Dreambox<br>
				<form method="GET">
                	       	<select name="file">%s
                                <input type="reset" size="100px"> 
                		<input name="command" type="submit" size=="100px" title=\"%s\" value="%s"> 
				</select>
                               	</form>                             
				<img src="/web-data/img/dflash.png" alt="%s ..."/><br><br>
                               	<hr>
				%s & %s @ Dreambox<br>
				<form method="GET">
 				<input name="directory" type="text" size="48" maxlength="48" value="%s">
 				<input name="file" type="text" size="48" maxlength="48" value="%s-%s-%s-%s">
                                <input type="reset" size="100px"> 
                		<input name="command" type="submit" size=="100px" title=\"%s\" value="%s"> 
				</select>
                               	</form>                             
				<img src="/web-data/img/ring.png" alt="%s ..."/><br><br>
                               	<hr>
    			""" % (header_string,plugin_string,disclaimer_header,disclaimer_wstring,fileupload_string, htmlnfi,flashing_string, "Flashing",flashing_string,backupdirectory_string,backupimage_string,config.plugins.dflash.backuplocation.value,name,self.boxtype,datetime.date.today(),time.strftime("%H-%M"),backup_string,"Backup",backup_string)
		else:
		   if command[0]=="Flashing":
		        # file command is received
			self.nfifile=file[0]
			if os.path.exists(self.nfifile):
		 		if self.nfifile.endswith(".nfi"):
 					f = open(self.nfifile,"r")
	 				header = f.read(32)     
  					f.close()
       					machine_type = header[4:4+header[4:].find("\0")]                        
					b=open("/proc/stb/info/model","r")
					dreambox=b.read().rstrip("\n")
					b.close()
		 			if os.path.exists("/var/lib/opkg/status"):
 						v = open("/var/lib/opkg/status","r")
 					else:
 						v = open("/usr/lib/opkg/status","r")
 					line = v.readline()     
					found=False
					loaderversion=0
					while (line) and not found:                                                                   
                		        	line = v.readline()                                                
                        			if line.startswith("Package: dreambox-secondstage"):                                            
                           			     	found=True                                                  
	                    			    	line = v.readline()                                                
                                    			line=line.replace("Version: ","")
							loader=line.split("-")
							loaderversion=int(loader[0])
  					v.close()
					mtd_info = array('c',"                                ")
					memgetinfo=0x40204D01
					# Flash
					flashdev="/dev/mtd/0"
					if os.path.exists("/dev/mtd0"):
						flashdev="/dev/mtd0"
					fd=open(flashdev) 
					ioctl(fd.fileno(), memgetinfo, mtd_info)
					fd.close()
					tuple=unpack('HLLLLLLL',mtd_info)
					self.blocksize="%d" % tuple[4]
					print "[dFLASH] %s %s %i %s %s" % (machine_type,dreambox,loaderversion,header[:4],self.blocksize)

					if machine_type.startswith(dreambox) is False and dreambox is not "dm7020":                                        
						print "[dFLASH] wrong header"
						return header_string+nonfi_string
					elif (dreambox == "dm800" or dreambox == "dm800se" or dreambox == "dm500hd" or dreambox == "dm7020hd") and loaderversion < 84 and header[:4] == "NFI2":
						print "[dFLASH] wrong header"
						return header_string+nonfi_string
					elif dreambox == "dm7020hd" and loaderversion < 87 and header[:4] == "NFI3":
						print "[dFLASH] wrong header"
						return header_string+nonfi_string
					elif (dreambox == "dm800" or dreambox == "dm800se" or dreambox == "dm500hd" or dreambox == "dm7020hd") and loaderversion >= 84 and header[:4] != "NFI2":
						print "[dFLASH] wrong header"
						return header_string+nonfi_string
					elif dreambox == "dm8000" and header[:4] != "NFI1":
						print "[dFLASH] wrong header"
						return header_string+nonfi_string
					elif dreambox == "dm7020hd" and header[:4] == "NFI3" and self.blocksize == "4096":
						print "[dFLASH] wrong header"
						return header_string+nonfi_string
					else:
						print "[dFLASH] correct header"
					CreateScript()
					if (eDVBVolumecontrol.getInstance().isMuted()) is False:
						eDVBVolumecontrol.getInstance().volumeToggleMute()
					self.avswitch = AVSwitch()
					if SystemInfo["ScartSwitch"]:
						self.avswitch.setInput("SCART")
					else:
						self.avswitch.setInput("AUX")
					print "[dFLASH] is flashing now %s" % self.nfifile
    					os.system("start-stop-daemon -S -b -x %s \"%s\"" % (dflash_script,self.nfifile))
					self.FlashTimer = eTimer()
     			 		self.FlashTimer.stop()
     				   	self.FlashTimer.timeout.get().append(self.secondFlash)
 				       	self.FlashTimer.start(60000,True)
					return dflash_flashing
				else:
					print "[dFLASH] wrong filename"
 					return header_string+nonfi_string
		 	else:
				print "[dFLASH] filename not found"
 				return header_string+nonfi_string

		   elif command[0]=="Backup":
		        if os.path.exists("/.bainfo"):
				return header_string+" "+barryallen_string+", "+dflash_backbutton
		        elif os.path.exists("/.lfinfo"):
				return header_string+" "+lowfat_string+", "+dflash_backbutton
		        elif os.path.exists("/dev/disk/by-label/TIMOTHY") and not os.path.exists("/boot/autoexec.bat"):
				return header_string+" "+dumbo_string+", "+dflash_backbutton
			self.backupname=file[0].replace(" ","").replace("[","").replace("]","").replace(">","").replace("<","").replace("|","").rstrip().lstrip()
			path=directory[0]
			sp=[]
			sp=path.split("/")
			print sp
			if len(sp) > 1:
				if sp[1] != "media":
					return header_string+" "+mounted_string % path +", "+dflash_backbutton
			mounted=False
		      	# check if swapfile too small
		        fm=open("/proc/meminfo")                                                
       	        	line = fm.readline()                                                    
       	         	swapspace=0                                                                  
                 	while (line):                                             
           	    		line = fm.readline()                                                 
           	    		if line.startswith("SwapTotal:"):                                    
              				swapspace=int(line.replace("SwapTotal: ","").replace("kB",""))/1000             
                    	fm.close()                                                              
	         	print "[dFLASH] swapspace: %i MB" % swapspace
		 	self.ownswap=True
	         	if swapspace < config.plugins.dflash.swapsize.value: 
		 		self.ownswap=False
			self.swappable=False
			sp2=[]
                	f=open("/proc/mounts", "r")
       		 	m = f.readline()                                                    
        		while (m) and not mounted:                                             
				if m.find("/%s/%s" % (sp[1],sp[2])) is not -1:
					mounted=True
					print m
					sp2=m.split(" ")
					print sp2
					if sp2[2].startswith("ext") or sp2[2].startswith("xfs") or sp2[2].endswith("fat"):
						print "[dFLASH] swappable"
						self.swappable=True
           			m = f.readline()                                                 
			f.close()	
			if not mounted:
				return header_string+" "+mounted_string % path +", "+dflash_backbutton
			path=path.lstrip().rstrip().replace(" ","")
	      		config.plugins.dflash.backuplocation.value=path
	      		config.plugins.dflash.backuplocation.save()
		        if not os.path.exists(config.plugins.dflash.backuplocation.value):
		 		os.mkdir(config.plugins.dflash.backuplocation.value,0777)
			if os.path.exists("%s/%s.nfi" % (config.plugins.dflash.backuplocation.value,self.backupname)):
				print "[dFLASH] filename already exists"
				return header_string+"%s.nfi" % self.backupname+" "+_("already exists,")+" "+dflash_backbutton
			else:
		 		if self.backupname.endswith(".nfi") or len(self.backupname) < 1:
					print "[dFLASH] filename with .nfi"
 					return header_string+nonfi_string+", "+dflash_backbutton
				elif self.backupname.find(" ") is not -1:
					print "[dFLASH] filename with blank"
 					return header_string+nonfi_string+", "+dflash_backbutton
				else:
					# backupfile request
                 			BackupImage(False,self.backupname,self.imagetype,self.creator,self.swappable,self.ownswap)
					return header_string+dflash_backuping
		   else:
			print "[dFLASH] unknown command"
              		return header_string+_("nothing entered")                 

	def secondFlash(self):
		print "[dFLASH] second flashing now %s" % self.nfifile
 		os.system("%s \"%s\" &" % (dflash_script,self.nfifile))

class CreateScript:
	b=open("/proc/stb/info/model","r")
	dreambox=b.read().rstrip("\n")
	b.close()
	print "[dFLASH] Dreambox: !%s!" % dreambox
	f=open(dflash_script,"w")
	f.write("#!/bin/sh -x\n")
   	f.write("sleep 1\n")
	if dreambox.startswith("dm500hd"):
		f.write("echo FFFFFFFF > /proc/stb/fp/led0_pattern\n") 
	else:
		f.write("echo 20 > /proc/progress\n")
	if config.plugins.dflash.ramfs.value:
		f.write("mkdir /tmp/ramfs\n")
		f.write("mount -t ramfs ramfs /tmp/ramfs\n")
		f.write("cp \"$1\" /tmp/ramfs/flash.nfi\n")
	if config.plugins.dflash.flashtool.value == "writenfi":
		f.write("cp %s/writenfi /tmp/writenfi\n" % dflash_bin)
		f.write("chmod 755 /tmp/writenfi\n")
	elif config.plugins.dflash.flashtool.value == "nandwrite":
		f.write("mkdir %s/tmp\n" % config.plugins.dflash.backuplocation.value)
		f.write("cp %s/flash_erase /tmp/flash_erase\n" % dflash_bin)
		f.write("chmod 755 /tmp/flash_erase\n")
		f.write("cp %s/nfidump /tmp/nfidump\n" % dflash_bin)
		f.write("chmod 755 /tmp/nfidump\n")
		f.write("cp %s/nandwrite /tmp/nandwrite\n" % dflash_bin)
		f.write("chmod 755 /tmp/nandwrite\n")
		f.write("cp /sbin/reboot /tmp/reboot\n")
		f.write("chmod 755 /tmp/reboot\n")
	else:
		f.write("cp %s/nfidump /tmp/nfidump\n" % dflash_bin)
		f.write("chmod 755 /tmp/nfidump\n")
	if os.path.exists("/dev/mtdblock/3"):
		f.write("ln -sfn /dev/mtdblock/3 /dev/root\n")
	else:
		f.write("ln -sfn /dev/mtdblock3 /dev/root\n")
	if os.path.exists("/dev/mtd/0"):
		f.write("chmod 777 /dev/mtd/0\n")
	else:
		f.write("chmod 777 /dev/mtd0\n")
   	f.write("killall -9 enigma2\n")
	f.write("init 1\n")
	if dreambox.startswith("dm500hd"):
		f.write("echo 00000000 > /proc/stb/fp/led0_pattern\n") 
		f.write("echo 00000000 > /proc/stb/fp/led1_pattern\n") 
	else:
		f.write("echo 40 > /proc/progress\n")
	f.write("sleep 4\n")
	if dreambox.startswith("dm500hd"):
		f.write("echo FFFFFFFF > /proc/stb/fp/led0_pattern\n") 
	else:
		f.write("echo 60 > /proc/progress\n")
	f.write("sync\n")
	if config.plugins.dflash.flashtool.value == "writenfi":
		f.write("mount -no remount,ro /dev/root  /\n")
		if config.plugins.dflash.ramfs.value:
			f.write("/tmp/writenfi /tmp/ramfs/flash.nfi --reboot\n")
		else:
			f.write("/tmp/writenfi \"$1\" --reboot\n")
	elif config.plugins.dflash.flashtool.value == "nandwrite":
		if config.plugins.dflash.ramfs.value:
			f.write("/tmp/nfidump --j /tmp/ramfs/flash.nfi %s/tmp\n" % config.plugins.dflash.backuplocation.value)
		else:
			f.write("/tmp/nfidump --j \"$1\" %s/tmp\n" % config.plugins.dflash.backuplocation.value)
		f.write("umount /boot\n")
		if os.path.exists("/dev/mtd2"):
			f.write("/tmp/flash_erase -j /dev/mtd2\n")
			f.write("/tmp/nandwrite -q -m /dev/mtd2 %s/tmp/boot.jffs2\n" % config.plugins.dflash.backuplocation.value)
		else:
			f.write("/tmp/flash_erase -j /dev/mtd/2\n")
			f.write("/tmp/nandwrite -q -m /dev/mtd/2 %s/tmp/boot.jffs2\n" % config.plugins.dflash.backuplocation.value)
		if os.path.exists("/dev/mtd3"):
			f.write("/tmp/flash_erase -j /dev/mtd3\n")
			f.write("/tmp/nandwrite -q -m /dev/mtd3 %s/tmp/root.jffs2\n" % config.plugins.dflash.backuplocation.value)
		else:
			f.write("/tmp/flash_erase -j /dev/mtd/3\n")
			f.write("/tmp/nandwrite -q -m /dev/mtd/3 %s/tmp/root.jffs2\n" % config.plugins.dflash.backuplocation.value)
		f.write("/tmp/reboot -f -n\n")
	else:
		f.write("mkdir /tmp/root\n")
		f.write("mount -no remount,rw /boot\n")
		if os.path.exists("/dev/mtdblock3"):
			f.write("mount -t jffs2 /dev/mtdblock3 /tmp/root\n")
		else:
			f.write("mount -t jffs2 /dev/mtdblock/3 /tmp/root\n")
		f.write("mkdir /tmp/root/boot\n")
		if os.path.exists("/dev/mtdblock2"):
			f.write("mount -t jffs2 /dev/mtdblock2 /tmp/root/boot\n")
		else:
			f.write("mount -t jffs2 /dev/mtdblock/2 /tmp/root/boot\n")
		f.write("mount -o remount,size=160M /tmp\n")
		if config.plugins.dflash.overwrite.value:
			if config.plugins.dflash.ramfs.value:
				f.write("/tmp/nfidump --overwrite --temp --reboot /tmp/ramfs/flash.nfi /tmp/root\n")
			else:
				f.write("/tmp/nfidump --overwrite --temp --reboot \"$1\" /tmp/root\n")
		else:
			if config.plugins.dflash.ramfs.value:
				f.write("/tmp/nfidump --reboot /tmp/ramfs/flash.nfi /tmp/root\n")
			else:
				f.write("/tmp/nfidump --reboot \"$1\" /tmp/root\n")
	if dreambox.startswith("dm500hd"):
		f.write("echo 00000000 > /proc/stb/fp/led0_pattern\n") 
		f.write("echo FFFFFFFF > /proc/stb/fp/led1_pattern\n") 
	else:
		f.write("echo 100 > /proc/progress\n")
	f.write("init 3\n")
	f.write("exit 0\n")
	f.close()
	os.system("chmod 755 %s" % dflash_script)
	print "[dFLASH] %s created" % dflash_script

class BackupImage(Screen):                                                      
        def __init__(self,session,backupname,imagetype,creator,swappable,ownswap):            
        	print "[dFLASH] does backup"
		os.system("touch %s" % dflash_busy)
        	self.session=session    
        	self.backupname=backupname               
        	self.imagetype=imagetype                                        
        	self.creator=creator                 
        	self.swappable=swappable                 
        	self.ownswap=ownswap                
		f=open("/proc/stb/info/model")
		self.boxtype=f.read()
		f.close()
		self.boxtype=self.boxtype.replace("\n","").replace("\l","")
		self.kernel="3.2-%s" % boxtype
        	for name in os.listdir("/lib/modules"):                          
			self.kernel = name
		self.kernel = self.kernel.replace("\n","").replace("\l","").replace("\0","")
		if not os.path.exists("/boot/autoexec.bat"):
			os.system("mount -t jffs2 /dev/mtdblock2 /boot")
		if os.path.exists("/boot/vmlinux-%s.gz" % self.kernel):               
			os.system("gunzip /boot/vmlinux-%s.gz -c > /tmp/vmlinux" % self.kernel)               
		else:
			os.system("gunzip /boot/vmlinux.gz -c > /tmp/vmlinux")               
		content=""
		if os.path.exists("/tmp/vmlinux"):
			f = open("/tmp/vmlinux","r")                                                                        
			content = f.read()                                                                       
			f.close()                       
		print "[dFLASH] boxtype %s kernel %s" % (self.boxtype,self.kernel)
		
		if os.path.exists("%s/r.ubi" % config.plugins.dflash.backuplocation.value):
			os.remove("%s/r.ubi" % config.plugins.dflash.backuplocation.value)
		if os.path.exists("%s/d.ubi" % config.plugins.dflash.backuplocation.value):
			os.remove("%s/d.ubi" % config.plugins.dflash.backuplocation.value)
		if os.path.exists("%s/r.img" % config.plugins.dflash.backuplocation.value):
			os.remove("%s/r.img" % config.plugins.dflash.backuplocation.value)
		if os.path.exists("%s/b.img" % config.plugins.dflash.backuplocation.value):
			os.remove("%s/b.img" % config.plugins.dflash.backuplocation.value)
		if os.path.exists("%s/s.bin" % config.plugins.dflash.backuplocation.value):
			os.remove("%s/s.bin" % config.plugins.dflash.backuplocation.value)
		if self.boxtype.startswith("dm7020hd") and not os.path.exists("/data"):
			os.mkdir("/data")
			
		if os.path.exists("/var/lib/opkg/status"):
			v = open("/var/lib/opkg/status","r")
		else:
			v = open("/usr/lib/opkg/status","r")
		line = v.readline()     
		found=False
		loaderversion=0
		while (line) and not found:                                                                   
                       	line = v.readline()                                                
                       	if line.startswith("Package: dreambox-secondstage"):                                            
                               	found=True                                                  
                        	line = v.readline()                                                
                                line=line.replace("Version: ","")
				loader=line.split("-")
				loaderversion=int(loader[0])
		v.close()
		mtd_info = array('c',"                                ")                                               
		memgetinfo=0x40204D01                                                                                  
		# Flash                                                                                                
		flashdev="/dev/mtd/0"                                                                                  
		if os.path.exists("/dev/mtd0"):                                                                        
		        flashdev="/dev/mtd0"                                                                           
	        fd=open(flashdev)                                                                                      
	        ioctl(fd.fileno(), memgetinfo, mtd_info)                                                               
	        fd.close()                                                                                             
	        tuple=unpack('HLLLLLLL',mtd_info)                                                                      
	        self.blocksize="%d" % tuple[4]                                                                         
	        
	        print "[dFLASH] loaderversion: %i blocksize %s" % (loaderversion,self.blocksize) 
		
		# backup only as NFI2 if the loader is already NFI2 capable 
		if (self.boxtype == "dm8000" or self.boxtype == "dm7025") or ((self.boxtype == "dm800" or self.boxtype == "dm800se" or self.boxtype == "dm500hd") and loaderversion < 84):
			self.brcmnand=""
		else:
			self.brcmnand="--brcmnand"
		self.flashsize="4000000"
		self.loadersize="40000"
		self.bootsize="3C0000"
		self.rootsize="3C00000"
	     	self.eraseblocksize=16384         
		self.minimumiosize=512      
		self.subpagesize=512
		self.lebsize=15360
                self.offset=512

		if self.boxtype == "dm8000":
		     	self.eraseblocksize=131072        
		        self.minimumiosize=2048       
		        self.lebsize=129024
			self.flashsize="10000000"
			self.loadersize="100000"
			self.bootsize="700000"
			self.rootsize="F800000"
		elif self.boxtype.startswith("dm7020hd"):
			self.flashsize="10000000"
			self.loadersize="100000"
			self.bootsize="700000"
			self.rootsize="3F800000"
			if self.blocksize > 2048:
			        self.minimumiosize=4096      
		     		self.eraseblocksize=262144       
			        self.lebsize=253952
		                self.offset=4096
		     	else: 	# dm7020hdv2
			        self.minimumiosize=2048       
		     		self.eraseblocksize=131072  
			        self.lebsize=126976
		                self.offset=2048
			# ubifs uses full flash on dm7020hd
		      	if config.plugins.dflash.backuptool.value == "mkfs.ubifs":
                        	self.rootsize="3F800000"                     			
		elif (self.boxtype == "dm7025"):
			self.flashsize="2000000"
			self.rootsize="1C00000"
			
		self.maxlebcountroot=config.plugins.dflash.volsize.value*1024*1024/self.lebsize
		if config.plugins.dflash.volsize.value > 960:
			self.maxlebcountdata=(2048-config.plugins.dflash.volsize.value)*1024*1024/self.lebsize
		else:
			self.maxlebcountdata=(971-config.plugins.dflash.volsize.value)*1024*1024/self.lebsize
		
		uc=open("/tmp/ubinize.cfg","w")
		c  ="[rootfs]\n"
		c +="mode=ubi\n"
		c +="image=%s/r.ubi\n" % config.plugins.dflash.backuplocation.value
		c +="vol_id=0\n"
		c +="vol_name=rootfs\n"
		c +="vol_type=dynamic\n"
		if self.boxtype.startswith("dm7020hd"):
			v=int(config.plugins.dflash.volsize.value)
			c +="vol_size=%dMiB\n" % v
			c +="[data]\n"
			c +="mode=ubi\n"
			if config.plugins.dflash.databackup.value:  
				c +="image=%s/d.ubi\n" % config.plugins.dflash.backuplocation.value
			c +="vol_id=1\n"
			c +="vol_name=data\n"
			c +="vol_type=dynamic\n"
			if config.plugins.dflash.volsize.value > 960:
				v=int(2048-config.plugins.dflash.volsize.value)
			else:
				v=int(971-config.plugins.dflash.volsize.value)
			c +="vol_size=%dMiB\n" % v
		else:
			c +="vol_flags=autoresize\n"
		c +="\n"
		uc.write(c)
		uc.close()
                        	
		self.buildoptions="%s/buildimage %s -a %s -e %s -f 0x%s -s %s -b 0x%s:%s/s.bin -d 0x%s:%s/b.img -d 0x%s:%s/r.img > %s/%s.nfi\n" % (dflash_bin,self.brcmnand,self.boxtype,self.eraseblocksize,self.flashsize,self.blocksize,self.loadersize,config.plugins.dflash.backuplocation.value,self.bootsize,config.plugins.dflash.backuplocation.value,self.rootsize,config.plugins.dflash.backuplocation.value,config.plugins.dflash.backuplocation.value,self.backupname)
		print "[dFLASH] buildoptions %s" % self.buildoptions
		self.jffs2options=" -e %s -n -l" % (self.eraseblocksize)
		print "[dFLASH] jffs2options %s" % self.jffs2options
	        # ubifs stuff 	
		if config.plugins.dflash.subpage.value:
			self.ubifsrootoptions="-m %d -e %d -c %d -F" % (self.minimumiosize,self.lebsize,self.maxlebcountroot)
			self.ubifsdataoptions="-m %d -e %d -c %d -F" % (self.minimumiosize,self.lebsize,self.maxlebcountdata)
			self.ubinizeoptions="-m %d -p %d -s %d -O %d" % (self.minimumiosize,self.eraseblocksize,self.subpagesize,self.offset)
		else:
			self.ubifsrootoptions="-m 2048 -e 126976 -c %d -F" % self.maxlebcountroot
			self.ubifsdataoptions="-m 2048 -e 126976 -c %d -F" % self.maxlebcountdata
			self.ubinizeoptions="-m 2048 -p 131072 -s 2048 -O 2048"
			
		print "[dFLASH] ubifs root options %s" % self.ubifsrootoptions
		print "[dFLASH] ubifs data options %s" % self.ubifsdataoptions
		print "[dFLASH] ubinize options %s" % self.ubinizeoptions
		
		if os.path.exists("/dev/mtd/1"):
			mtdev="/dev/mtd/1"
		else:
			mtdev="/dev/mtd1"

		# here comes the fun ...
		
		command  = "#!/bin/sh -x\n"
		command += "exec > %s 2>&1\n" % dflash_backuplog
		command +="cat %s\n" % dflash_backupscript
		command +="df -h\n"
	      	if not self.ownswap and (self.swappable or config.plugins.dflash.loopswap.value): # I do it my way ...
			if config.plugins.dflash.loopswap.value is True:
				if not os.path.exists("/dev/loop8"):
                			command +="mknod /dev/loop8 b 7 8\n"
                		command +="swapoff /dev/loop8\n"
                		command +="losetup -d /dev/loop8\n"
			else:
                		command +="swapoff %s/swapfile\n" % config.plugins.dflash.backuplocation.value                        
                	command +="rm %s/swapfile\n" % config.plugins.dflash.backuplocation.value                        
                	command +="dd if=/dev/zero of=%s/swapfile bs=1024 count=%i\n" % (config.plugins.dflash.backuplocation.value,int(config.plugins.dflash.swapsize.value*1024))
                	command +="mkswap %s/swapfile\n" % config.plugins.dflash.backuplocation.value                                
			if config.plugins.dflash.loopswap.value is True:
	                	command +="modprobe loop\n"                                 
	                	command +="losetup /dev/loop8 %s/swapfile\n" % config.plugins.dflash.backuplocation.value                                
	                	command +="swapon /dev/loop8\n"                                 
			else:
                		command +="swapon %s/swapfile\n" % config.plugins.dflash.backuplocation.value                                 
		if os.path.exists("/etc/init.d/openvpn"):
			command +="/etc/init.d/openvpn stop\n"
		#		
		# secondstage loader ...
		#		
		command +="%s/nanddump -n -o -b -c -f %s/s.bin %s\n" % (dflash_bin,config.plugins.dflash.backuplocation.value,mtdev)
		
		if config.plugins.dflash.backuptool.value != "nanddump":
			command +="umount /tmp/boot\n"
			command +="mkdir /tmp/boot\n"
			# mount /boot if not mounted ...
        	        if not os.path.exists("/boot/autoexec.bat"):                                           
			        os.system("mount -t jffs2 /dev/mtdblock2 /boot")               
				
			command +="umount /tmp/boot\n"
			command +="rm -r /tmp/boot\n"
			command +="mkdir /tmp/boot\n"
			if self.boxtype == "dm7025" or self.boxtype =="dm800":
				if os.path.exists("/dev/mtdblock2"):
					command +="mount -t jffs2 /dev/mtdblock2 /tmp/boot\n"
				else:
					command +="mount -t jffs2 /dev/mtdblock/2 /tmp/boot\n"
			else:
				command +="cp /boot/* /tmp/boot; cd /tmp/boot; ln -sfn vmlinux-3.2-%s.gz vmlinux\n" % self.boxtype
				command +="ln -sfn /usr/share/bootlogo.mvi bootlogo.mvi; ln -sfn bootlog.mvi backdrop.mvi; ln -sfn bootlogo.mvi bootlogo_wait.mvi; cd /\n"
		                if config.plugins.dflash.backuptool.value == "mkfs.ubifs":
					# here comes autoexec for ubifs if it is currently jffs2
					command +="sed -ie s!\"root=/dev/mtdblock3 rootfstype=jffs2\"!\"ubi.mtd=root root=ubi0:rootfs rootfstype=ubifs\"!g /tmp/boot/autoexec*.bat\n"
				else:
					# here comes autoexec for jffs2 if it is currently ubifs
					command +="sed -ie s!\"ubi.mtd=root root=ubi0:rootfs rootfstype=ubifs\"!\"root=/dev/mtdblock3 rootfstype=jffs2\"!g /tmp/boot/autoexec*.bat\n"
        	        	if config.plugins.dflash.console.value:
					command +="sed -ie s!\"console=null\"!\"console=ttyS0,115200\"!g /tmp/boot/autoexec*.bat\n"
					command +="sed -ie s!\"quiet\"!\"\"!g /tmp/boot/autoexec*.bat\n"
				else:
					command +="sed -ie s!\"console=ttyS0,115200\"!\"console=null\"!g /tmp/boot/autoexec*.bat\n"
				
			# make boot filesystem ...
                        if config.plugins.dflash.jffs2compression.value == "lzo" or config.plugins.dflash.jffs2compression.value == "none" or content.find("lzo deflate") is not -1 or content.find("2_lzo") is not -1:
				command +="mkfs.jffs2 --root=/tmp/boot --disable-compressor=lzo --compression-mode=none --output=%s/b.img %s\n" % (config.plugins.dflash.backuplocation.value,self.jffs2options)
			else:
				command +="mkfs.jffs2 --root=/tmp/boot --disable-compressor=lzo --compression-mode=size --output=%s/b.img %s\n" % (config.plugins.dflash.backuplocation.value,self.jffs2options)
				
			if config.plugins.dflash.summary.value is True:
				command +="%s/sumtool --input=%s/b.img --output=%s/bs.img %s\n" % (dflash_bin,config.plugins.dflash.backuplocation.value,config.plugins.dflash.backuplocation.value,self.jffs2options)
				command +="cp %s/bs.img %s/b.img\n" % (config.plugins.dflash.backuplocation.value,config.plugins.dflash.backuplocation.value)
				command +="rm %s/bs.img\n" % (config.plugins.dflash.backuplocation.value)
			command +="umount /tmp/boot\n"
			command +="rm -r /tmp/boot\n"
			
			# make root filesystem ...
			
			command +="umount /tmp/root\n"
			command +="rm -r /tmp/root\n"
			command +="mkdir /tmp/root\n"
			if self.boxtype == "dm7025":
				if os.path.exists("/dev/mtdblock3"):
					command +="mount -t jffs2 /dev/mtdblock3 /tmp/root\n"
				else:
					command +="mount -t jffs2 /dev/mtdblock/3 /tmp/root\n"
			else:
				command +="mount -o bind / /tmp/root\n"
			if config.plugins.dflash.usr.value:
				command +="mount -o bind /usr /tmp/root/usr\n"
			if config.plugins.dflash.squashfs.value:
		        	for name in os.listdir("/media/squashfs-images"):                          
					if name.endswith("-img"):
						command +="mkdir /tmp/root/media/squashfs-images/%s\n" % (name)
						command +="mount -o bind /media/squashfs-images/%s /tmp/root/media/squashfs-images/%s\n" % (name,name)
			if config.plugins.dflash.restart.value is True or (self.swappable is False and self.ownswap is False and config.plugins.dflash.loopswap.value is False):
				command +="wget http://localhost/web/powerstate?newstate=3\n"
				command +="sleep 3\n"
				command +="init 4\n"
				
                        if config.plugins.dflash.backuptool.value == "mkfs.jffs2":
	                        if config.plugins.dflash.jffs2compression.value == "lzo" or content.find("lzo deflate") is not -1 or content.find("2_lzo") is not -1:
					command +="mkfs.jffs2 --root=/tmp/root --enable-compressor=lzo --compression-mode=priority --output=%s/r.img %s\n" % (config.plugins.dflash.backuplocation.value,self.jffs2options)
	                        elif config.plugins.dflash.jffs2compression.value == "none":
					command +="mkfs.jffs2 --root=/tmp/root --disable-compressor=lzo --disable-compressor=zlib --compression-mode=none --output=%s/r.img %s\n" % (config.plugins.dflash.backuplocation.value,self.jffs2options)
				else:
					command +="mkfs.jffs2 --root=/tmp/root --disable-compressor=lzo --compression-mode=size --output=%s/r.img %s\n" % (config.plugins.dflash.backuplocation.value,self.jffs2options)
					if config.plugins.dflash.summary.value is True:
						command +="%s/sumtool --input=%s/r.img --output=%s/rs.jffs2 %s\n" % (dflash_bin,config.plugins.dflash.backuplocation.value,config.plugins.dflash.backuplocation.value,self.jffs2options)
						command +="cp %s/rs.jffs2 %s/r.img\n" % (config.plugins.dflash.backuplocation.value,config.plugins.dflash.backuplocation.value)
						command +="rm %s/rs.jffs2\n" % (config.plugins.dflash.backuplocation.value)
			else:
                		if config.plugins.dflash.ubifsrootcompression.value == "none":
					command +="chattr -R -c /tmp/root\n"
				command +="touch %s/r.ubi\n" % (config.plugins.dflash.backuplocation.value)
				command +="chmod 777 %s/r.ubi\n" % (config.plugins.dflash.backuplocation.value)
				if not os.path.exists("/tmp/root/data") and self.boxtype.startswith("dm7020hd"):
					command +="mkdir /tmp/root/data\n"
				command +="%s/mkfs.ubifs %s -x %s -r /tmp/root  -o %s/r.ubi\n" % (dflash_bin,self.ubifsrootoptions, config.plugins.dflash.ubifsrootcompression.value, config.plugins.dflash.backuplocation.value)
		
				if config.plugins.dflash.databackup.value and self.boxtype.startswith("dm7020hd"):  
					# make data filesystem ...
					command +="umount /tmp/data\n"
					command +="mkdir /tmp/data\n"
					command +="mount -o bind /data /tmp/data\n"
    		   	         	if config.plugins.dflash.ubifsdatacompression.value == "none":
						command +="chattr -R -c /tmp/data\n"
					command +="touch %s/d.ubi\n" % (config.plugins.dflash.backuplocation.value)
					command +="chmod 777 %s/d.ubi\n" % (config.plugins.dflash.backuplocation.value)
					command +="%s/mkfs.ubifs %s -x %s -r /tmp/data  -o %s/d.ubi\n" % (dflash_bin,self.ubifsdataoptions, config.plugins.dflash.datacompression.value, config.plugins.dflash.backuplocation.value)
					command +="umount /tmp/data\n"
					command +="rmdir /tmp/data\n"
		
				command +="cat /tmp/ubinize.cfg\n"
				command +="%s/ubinize -o %s/r.img %s /tmp/ubinize.cfg\n" % (dflash_bin,config.plugins.dflash.backuplocation.value,self.ubinizeoptions)
					
			if config.plugins.dflash.usr.value:
				command +="umount /tmp/root/usr\n"
			if config.plugins.dflash.squashfs.value:
		        	for name in os.listdir("/media/squashfs-images"):                          
					if name.endswith("-img"):
						command +="umount /tmp/root/media/squashfs-images/%s\n" % (name)
			command +="umount /tmp/root\n"
			command +="rmdir /tmp/root\n"
		else:
			if os.path.exists("/dev/mtd2"):
				command +="%s/nanddump -n -o -b -q -f %s/b.img /dev/mtd2\n" % (dflash_bin,config.plugins.dflash.backuplocation.value)
				command +="%s/nanddump -n -o -b -q -f %s/r.img /dev/mtd3\n" % (dflash_bin,config.plugins.dflash.backuplocation.value)
			else:
				command +="%s/nanddump -n -o -b -q -f %s/b.img /dev/mtd/2\n" % (dflash_bin,config.plugins.dflash.backuplocation.value)
				command +="%s/nanddump -n -o -b -q -f %s/r.img /dev/mtd/3\n" % (dflash_bin,config.plugins.dflash.backuplocation.value)
		if os.path.exists("/etc/init.d/openvpn"):
			command +="/etc/init.d/openvpn start\n"
			
		command +="chmod 777 %s/s.bin\n" % config.plugins.dflash.backuplocation.value
		command +="chmod 777 %s/b.img\n" % config.plugins.dflash.backuplocation.value
		command +="chmod 777 %s/r.img\n" % config.plugins.dflash.backuplocation.value
		command +=self.buildoptions
		if not config.plugins.dflash.keep.value:
			command +="rm %s/s.bin\n" % config.plugins.dflash.backuplocation.value
			command +="rm %s/b.img\n" % config.plugins.dflash.backuplocation.value
			command +="rm %s/r.img\n" % config.plugins.dflash.backuplocation.value
			command +="rm %s/r.ubi\n" % config.plugins.dflash.backuplocation.value
			if config.plugins.dflash.databackup.value:  
				command +="rm %s/d.ubi\n" % config.plugins.dflash.backuplocation.value
		command +="chmod 777 %s/%s.nfi\n" % (config.plugins.dflash.backuplocation.value,self.backupname)
		if not self.ownswap and not config.plugins.dflash.keep.value:
			if config.plugins.dflash.loopswap.value is True:
                		command +="swapoff /dev/loop8\n"
                		command +="losetup -d /dev/loop8\n"                        
			else:
                		command +="swapoff %s/swapfile\n" % config.plugins.dflash.backuplocation.value                        
                	command +="rm %s/swapfile\n" % config.plugins.dflash.backuplocation.value                        
		if config.plugins.dflash.restart.value is True or (self.swappable is False and self.ownswap is False):
			command +="init 3\n"
		nfo="%s/%s.nfo" % (config.plugins.dflash.backuplocation.value,self.backupname)
		if self.imagetype == "exp":
			command +="echo \"Enigma2: experimental\" > %s\n" % (nfo)
		else:
			command +="echo \"Enigma2: release\" > %s\n" % (nfo)
		command +="echo \"Machine: Dreambox %s\" >> %s\n" % (self.boxtype,nfo)
		command +="echo \"Date: %s\" >> %s\n" % (datetime.date.today(),nfo)
                command +="echo \"Issuer: %s\" >> %s\n" % (self.creator,nfo)
	        command +="echo \"Feed: local\" >> %s\n" % nfo
                command +="echo \"Image: local\" >> %s\n" %nfo
		command +="MD5SUM=`md5sum %s/%s.nfi | cut -d\" \" -f 1`\n" % (config.plugins.dflash.backuplocation.value,self.backupname)
		command +="echo \"MD5: $MD5SUM\" >> %s\n" % nfo
		command +="echo >> %s\n" % nfo
		command +="chmod 777 %s/%s.nfo\n" % (config.plugins.dflash.backuplocation.value,self.backupname)
		command +="ls -alh %s/%s.*\n" % (config.plugins.dflash.backuplocation.value,self.backupname)
		command +="du -h %s/%s.nfi > %s\n" % (config.plugins.dflash.backuplocation.value,self.backupname,dflash_backup)
		if os.path.exists("/usr/bin/zip") and config.plugins.dflash.zip.value:
			command +="/usr/bin/zip %s/%s.nfi.zip %s/%s.nfi\n" % (config.plugins.dflash.backuplocation.value,self.backupname,config.plugins.dflash.backuplocation.value,self.backupname)
		command +="df -h\n"
		command +="rm %s\n" % dflash_busy
		command +="exit 0\n"
		print command
		b=open(dflash_backupscript,"w")
		b.write(command)
		b.close()
		os_chmod(dflash_backupscript, 0777)

		# here comes my ONE and ONLY container
		self.TimerBackup = eTimer()                                       
		self.TimerBackup.stop()                                           
		self.TimerBackup.timeout.get().append(self.backupFinishedCheck)
		self.TimerBackup.start(10000,True)                                 
		os.system("start-stop-daemon -S -b -x %s" % (dflash_backupscript))
# 		here comes my ONE and ONLY container
#		self.container = eConsoleAppContainer()
#              	self.container.execute("%s > %s 2>&1" % (dflash_backupscript,dflash_backuplog))

        def backupFinishedCheck(self):
		if not os.path.exists(dflash_backup):
			# not finished - continue checking ...
 			print "[dFLASH] checked if backup is finished ..."
			self.TimerBackup.start(5000,True)                                 
		else:
 			print "[dFLASH] found finished backup ..."
			self.TimerBackup = eTimer()                                       
			self.TimerBackup.stop()                                           
			if os.path.exists(dflash_busy):
				os.remove(dflash_busy)
			if os.path.exists(dflash_backupscript) and not config.plugins.dflash.keep.value:
				os.remove(dflash_backupscript)
			f=open(dflash_backup)
			line=f.readline()
			f.close()
			os.remove(dflash_backup)
			sp=[]
			sp=line.split("	")
			print sp
			length=len(sp)
			size=""
			image=""
			path=""
			if length > 0:
				size=sp[0].rstrip().lstrip()
				sp2=[]
				sp2=sp[length-1].split("/")
				print sp2
				length=len(sp2)
				if length > 0:
					image=sp2[length-1]
					path=line.replace(size,"").replace(image,"")
					image=image.replace(".nfi\n","")
					image=image.rstrip().lstrip()
			print "[dFLASH] found backup %s" % line
			if self.session:
				if config.plugins.dflash.fade.value:
	        	        	f=open("/proc/stb/video/alpha","w")
        	        		f.write("%i" % (config.osd.alpha.getValue()))
                			f.close()
				self.session.open(MessageBox,size+"B "+_("Flash Backup to %s finished with imagename:\n\n%s.nfi") % (path,image),  MessageBox.TYPE_INFO)                 
			else:
				print "[dFLASH] finished webif backup"

###############################################################################
# dFlash Check by gutemine
###############################################################################

class dFlashChecking(Screen):
    skin = """
        <screen position="center,80" size="680,440" title="choose NAND Flash Check" >
        <widget name="menu" position="10,60" size="660,370" scrollbarMode="showOnDemand" />
	<widget name="logo" position="10,10" size="100,40" transparent="1" alphatest="on" />
	<widget name="buttonred" position="120,10" size="130,40" backgroundColor="red" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
	<widget name="buttongreen" position="260,10" size="130,40" backgroundColor="green" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
	<widget name="buttonyellow" position="400,10" size="130,40" backgroundColor="yellow" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
	<widget name="buttonblue" position="540,10" size="130,40" backgroundColor="blue" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
        </screen>"""
        
    def __init__(self, session, args = 0):
        self.skin = dFlashChecking.skin
        self.session = session
        Screen.__init__(self, session)
        self.menu = args
        self.onShown.append(self.setWindowTitle)
        flashchecklist = []
	self["buttonred"] = Label(_("Cancel"))
	self["buttonyellow"] = Label(_("Info"))
	self["buttongreen"] = Label(_("OK"))
	self["buttonblue"] = Label(_("About"))
	self["logo"] = Pixmap()
        if os.path.exists("/dev/mtd0") is True:
        	flashchecklist.append((_("check /dev/mtd0 = entire Flash"), "/dev/mtd0"))
        else:
        	flashchecklist.append((_("check /dev/mtd/0 = entire Flash"), "/dev/mtd/0"))
        if os.path.exists("/dev/mtd1") is True:
        	flashchecklist.append((_("check /dev/mtd1 = secondstage loader"), "/dev/mtd1"))
        else:
        	flashchecklist.append((_("check /dev/mtd/1 = secondstage loader"), "/dev/mtd/1"))
        if os.path.exists("/dev/mtd2") is True:
        	flashchecklist.append((_("check /dev/mtd2 = boot"), "/dev/mtd2"))
        else:
        	flashchecklist.append((_("check /dev/mtd/2 = boot"), "/dev/mtd/2"))
        if os.path.exists("/dev/mtd3") is True:
	        flashchecklist.append((_("check /dev/mtd3 = root"), "/dev/mtd3"))
        else:
	        flashchecklist.append((_("check /dev/mtd/3 = root"), "/dev/mtd/3"))
        if os.path.exists("/dev/mtd4") is True:
           flashchecklist.append((_("check /dev/mtd4 = home"), "/dev/mtd4"))
        if os.path.exists("/dev/mtd/4") is True:
           flashchecklist.append((_("check /dev/mtd/4 = home"), "/dev/mtd/4"))
        if os.path.exists("/dev/mtd5") is True:
           flashchecklist.append((_("check /dev/mtd5 = unused"), "/dev/mtd5"))
        if os.path.exists("/dev/mtd/5") is True:
           flashchecklist.append((_("check /dev/mtd/5 = unused"), "/dev/mtd/5"))
        if os.path.exists("/dev/mtd6") is True:
           flashchecklist.append((_("check /dev/mtd6 = unused"), "/dev/mtd6"))
        if os.path.exists("/dev/mtd/6") is True:
           flashchecklist.append((_("check /dev/mtd/6 = unused"), "/dev/mtd/6"))
        self["menu"] = MenuList(flashchecklist)
	self["actions"] = ActionMap([ "ColorActions", "dFlashActions" ],
		{
		"ok": self.go,
		"green": self.go,
		"red": self.close,
		"yellow": self.legend,
		"blue": self.about,
		"cancel": self.close,
		})
        
    def go(self):
        returnValue = self["menu"].l.getCurrentSelection()[1]
        if returnValue is not None:
        	self.session.open(Console,_("checking %s - be patient (up to 1 min)" % returnValue),["%s/bin/nand_check %s\n" % (dflash_plugindir,returnValue) ])

    def setWindowTitle(self):
	self["logo"].instance.setPixmapFromFile("%s/dflash.png" % dflash_plugindir)
	self.setTitle(flashing_string+" & "+backup_string+" V%s " % dflash_version + checking_string)

    def legend(self):
        title=_("B Bad block\n. Empty block\n- Partially filled block\n= Full block, no summary node\nS Full block, summary node\nIgnore B at the end of Flash")
        self.session.open(MessageBox, title,  MessageBox.TYPE_INFO)

    def about(self):
       	self.session.open(dFlashAbout)

class dFlashConfiguration(Screen, ConfigListScreen):
    skin = """
        <screen position="center,80" size="680,440" title="dFlash Configuration" >
	<widget name="logo" position="10,10" size="100,40" transparent="1" alphatest="on" />
        <widget name="config" position="10,60" size="660,370" scrollbarMode="showOnDemand" />
        <widget name="buttonred" position="120,10" size="130,40" backgroundColor="red" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
        <widget name="buttongreen" position="260,10" size="130,40" backgroundColor="green" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
        <widget name="buttonyellow" position="400,10" size="130,40" backgroundColor="yellow" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
        <widget name="buttonblue" position="540,10" size="130,40" backgroundColor="blue" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;12"/>
        </screen>"""

    def __init__(self, session, args = 0):
	Screen.__init__(self, session)
	f=open("/proc/stb/info/model")
	self.boxtype=f.read()
	f.close()
	f=open("/proc/mounts")
	self.mounts=f.read()
	f.close()
	self.boxtype=self.boxtype.replace("\n","").replace("\l","")
       	self.list = []
        self.list.append(getConfigListEntry(backupdirectory_string, config.plugins.dflash.backuplocation))
	if self.boxtype != "dm7025":
        	self.list.append(getConfigListEntry(_("Fading"), config.plugins.dflash.fade))
        self.list.append(getConfigListEntry(_("Swapsize [MB]"), config.plugins.dflash.swapsize))
       	self.list.append(getConfigListEntry(_("Flashtool"), config.plugins.dflash.flashtool))
       	self.list.append(getConfigListEntry(_("Backuptool"), config.plugins.dflash.backuptool))
     	self.list.append(getConfigListEntry(_("jffs2 compression"), config.plugins.dflash.jffs2compression))
	if self.boxtype != "dm7025" and self.boxtype !="dm800":
		if self.boxtype == "dm7020hd" or self.boxtype =="dm8000":
			self.list.append(getConfigListEntry(_("jffs2 erase block summary"), config.plugins.dflash.summary))
		if self.boxtype =="dm8000":
			if os.path.exists("/sbin/rambo"):
			       	self.list.append(getConfigListEntry(_("Root Volume Size [59-%iMB]") % rambo_maxflash, config.plugins.dflash.volsize))
			else:
			       	self.list.append(getConfigListEntry(_("Root Volume Size [59-248MB]"), config.plugins.dflash.volsize))
		elif self.boxtype.startswith("dm7020hd"):
			if os.path.exists("/sbin/rambo"):
			       	self.list.append(getConfigListEntry(_("Root Volume Size [59-%iMB]") % rambo_maxflash, config.plugins.dflash.volsize))
			else:
			       	self.list.append(getConfigListEntry(_("Root Volume Size [59-960MB]"), config.plugins.dflash.volsize))
		else:
			if os.path.exists("/sbin/rambo"):
			       	self.list.append(getConfigListEntry(_("Root Volume Size [40-%iMB]") % rambo_maxflash, config.plugins.dflash.volsize))
			else:
			       	self.list.append(getConfigListEntry(_("Root Volume Size [40-59MB]"), config.plugins.dflash.volsize))
		if self.boxtype =="dm8000":
		       	self.list.append(getConfigListEntry(_("ubifs subpages [Flash=")+_("yes")+_(", rambo=")+_("no")+"]", config.plugins.dflash.subpage))
	     	self.list.append(getConfigListEntry(_("ubifs root compression"), config.plugins.dflash.ubifsrootcompression))
		if self.boxtype.startswith("dm7020hd"):
		      	self.list.append(getConfigListEntry(_("ubifs data backup"), config.plugins.dflash.databackup))
		     	self.list.append(getConfigListEntry(_("ubifs data compression"), config.plugins.dflash.ubifsdatacompression))
 	      	self.list.append(getConfigListEntry(_("Console output"), config.plugins.dflash.console))
       	self.list.append(getConfigListEntry(_("loop swap over network"), config.plugins.dflash.loopswap))
       	if self.mounts.find("/usr") is not -1:
		self.list.append(getConfigListEntry(_("include /usr mount in backup"), config.plugins.dflash.usr))
	if self.boxtype == "dm500hd" or self.boxtype == "dm800se":
		self.list.append(getConfigListEntry(_("include squashfs directories in backup"), config.plugins.dflash.squashfs))
       	if os.path.exists("/usr/bin/zip"):
      		self.list.append(getConfigListEntry(_("zip backups"), config.plugins.dflash.zip))
#      	self.list.append(getConfigListEntry(_("use ramfs for flashing"), config.plugins.dflash.ramfs))
#     	self.list.append(getConfigListEntry(_("overwrite only image "), config.plugins.dflash.overwrite))
#     	self.list.append(getConfigListEntry(_("keep temporary files"), config.plugins.dflash.keep))
      	self.list.append(getConfigListEntry(_("restart enigma2"), config.plugins.dflash.restart))
#      	self.list.append(getConfigListEntry(_("sort alphabetic"), config.plugins.dflash.sort))
      	self.list.append(getConfigListEntry(_("show in Extensions Menu"), config.plugins.dflash.extension))

        self.onShown.append(self.setWindowTitle)
       	ConfigListScreen.__init__(self, self.list)

        # explizit check on every entry
	self.onChangedEntry = []

	self["logo"] = Pixmap()
       	self["buttonred"] = Label(_("Cancel"))
       	self["buttongreen"] = Label(_("OK"))
       	self["buttonyellow"] = Label(checking_string)
	self["buttonblue"] = Label(_("Disclaimer"))
        self["actions"] = ActionMap(["dFlashActions", "ColorActions"],
       	{
       		"green": self.save,
        	"red": self.cancel,
	       	"yellow": self.checking,
        	"blue": self.disclaimer,
            	"save": self.save,
            	"cancel": self.cancel,
            	"ok": self.save,
       	})
    def setWindowTitle(self):
	self["logo"].instance.setPixmapFromFile("%s/dflash.png" % dflash_plugindir)
	f=open("/proc/mounts","r")
	mm=f.read()
	f.close()
	if mm.find("/ ubifs") is not -1:
		flashfs="UBIFS"
	else:
		flashfs="JFFS2"
	self.setTitle(flashing_string+" & "+backup_string+" V%s " % dflash_version + setup_string+": %s" % flashfs)

    def save(self):
	if config.plugins.dflash.backuptool.value != "nanddump" and config.plugins.dflash.swapsize.value < 128: 
		config.plugins.dflash.swapsize.value=128 
        for x in self["config"].list:
           x[1].save()
        self.close(True)

    def cancel(self):
        for x in self["config"].list:
           x[1].cancel()
        self.close(False)

    def checking(self):      
        self.session.open(dFlashChecking)

    def disclaimer(self):
	self.session.openWithCallback(self.about,MessageBox, disclaimer_string, MessageBox.TYPE_WARNING)

    def about(self,answer):
       	self.session.open(dFlashAbout)

class dFlashAbout(Screen):
    skin = """
        <screen position="center,80" size="680,440" title="About dFlash" >
        <ePixmap position="290,10" size="100,100" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/dFlash/g3icon_dflash.png" transparent="1" alphatest="on" />                                              
        <widget name="buttonred" position="10,10" size="130,40" backgroundColor="red" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
        <widget name="buttongreen" position="540,10" size="130,40" backgroundColor="green" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
        <widget name="aboutdflash" position="10,120" size="660,100" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;24"/>
        <widget name="freefilesystem" position="130,230" size="180,200" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;24"/>
        <widget name="freememory" position="380,230" size="180,200" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;24"/>
        </screen>"""

    def __init__(self, session, args = 0):
	Screen.__init__(self, session)
        self.onShown.append(self.setWindowTitle)
        st = os.statvfs("/")                                                                           
        free = st.f_bavail * st.f_frsize/1024/1024                                                               
        total = st.f_blocks * st.f_frsize/1024/1024                                                
        used = (st.f_blocks - st.f_bfree) * st.f_frsize/1024/1024 
	freefilesystem=_("Root Filesystem\n\ntotal: %s MB\nused:  %s MB\nfree:  %s MB") % (total,used,free)		

      	memfree=0
      	memtotal=0
      	memused=0
	fm=open("/proc/meminfo")
      	line = fm.readline()
      	sp=line.split()
      	memtotal=int(sp[1])/1024
      	line = fm.readline()
      	sp=line.split()
      	memfree=int(sp[1])/1024
	fm.close()
	memused=memtotal-memfree
	freememory=_("Memory\n\ntotal: %i MB\nused: %i MB\nfree: %i MB") % (memtotal,memused,memfree)		

       	self["buttonred"] = Label(_("Cancel"))
       	self["buttongreen"] = Label(_("OK"))
       	self["aboutdflash"] = Label(plugin_string+"\n\nDon't Take Me For Granted!")
       	self["freefilesystem"] = Label(freefilesystem)
       	self["freememory"] = Label(freememory)
        self["actions"] = ActionMap(["dFlashActions", "ColorActions"],
       	{
       		"green": self.cancel,
        	"red": self.cancel,
	       	"yellow": self.cancel,
        	"blue": self.cancel,
            	"save": self.cancel,
            	"cancel": self.cancel,
            	"ok": self.cancel,
       	})
    def setWindowTitle(self):
        self.setTitle( _("About")+" dFlash")

    def cancel(self):
        self.close(False)


