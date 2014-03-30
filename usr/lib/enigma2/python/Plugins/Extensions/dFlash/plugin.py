# -*- coding: utf-8 -*-
#
# dFlash Plugin by gutemine
#
dflash_version="12.6 MOD for ATV"
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
from Components.Slider import Slider       
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

if os.path.exists("/usr/lib/enigma2/python/Plugins/Bp/geminimain/lib/libgeminimain.so"):
	from Plugins.Bp.geminimain.lib import libgeminimain

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
	
yes_no_descriptions = {False: _("no"), True: _("yes")}    

config.plugins.dflash = ConfigSubsection()
config.plugins.dflash.backuplocation = ConfigText(default = "/media/hdd/backup", fixed_size=True, visible_width=20)
config.plugins.dflash.sort = ConfigBoolean(default = True, descriptions=yes_no_descriptions)
config.plugins.dflash.keep = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
config.plugins.dflash.restart = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
config.plugins.dflash.loopswap = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
config.plugins.dflash.swapsize = ConfigInteger(default = 250, limits = (0, 2047))
config.plugins.dflash.ramfs = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
config.plugins.dflash.usr = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
config.plugins.dflash.squashfs = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
config.plugins.dflash.summary = ConfigBoolean(default = True, descriptions=yes_no_descriptions)
config.plugins.dflash.zip = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
config.plugins.dflash.switchversion = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
config.plugins.dflash.nfo = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
if boxtype != "dm8000" and boxtype != "dm7020hd":
	config.plugins.dflash.summary.value = False
compression=[]
config.plugins.dflash.extension = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
flashtools=[]
flashtools.append(( "nfiwrite", _("nfiwrite") ))
if boxtype != "dm800":
	flashtools.append(( "recovery", _("recovery") ))
#flashtools.append(( "writenfi", _("writenfi") ))
#flashtools.append(( "nandwrite", _("nandwrite") ))
#flashtools.append(( "rawdevice", _("rawdevice") ))

writesize="512"
if os.path.exists("/sys/devices/virtual/mtd/mtd0/writesize"):
	w=open("/sys/devices/virtual/mtd/mtd0/writesize","r")
	writesize=w.read()
	w.close()
	writesize=writesize.replace("\n","").replace("\l","")
else:
	flashdev="/dev/mtd/0"
        if os.path.exists("/dev/mtd0"):
       		flashdev="/dev/mtd0"
        fd=open(flashdev)
        mtd_info = array('c',"                                ")
        memgetinfo=0x40204D01
        ioctl(fd.fileno(), memgetinfo, mtd_info)
        fd.close()
        tuple=unpack('HLLLLLLL',mtd_info)
        writesize="%s" % tuple[4]
	print "[dFlash] %s" % writesize

if os.path.exists("/sbin/rambo"):
	flashtools.append(( "rambo", _("rambo") ))
	config.plugins.dflash.flashtool = ConfigSelection(default = "rambo", choices = flashtools)
elif os.path.exists("/sbin/flodder") and os.path.exists("/usr/sbin/nfidump"):
	flashtools.append(( "flodder", _("flodder") ))
	config.plugins.dflash.flashtool = ConfigSelection(default = "flodder", choices = flashtools)
else:
	config.plugins.dflash.flashtool = ConfigSelection(default = "nfiwrite", choices = flashtools)
if boxtype == "dm8000":
	config.plugins.dflash.volsize = ConfigInteger(default = 248, limits = (59, rambo_maxflash))
elif boxtype == "dm7020hd" and writesize=="4096" and not config.plugins.dflash.switchversion.value:
	config.plugins.dflash.volsize = ConfigInteger(default = 397, limits = (59, rambo_maxflash))
elif (boxtype == "dm7020hd" and writesize=="2048") or boxtype == "dm800sev2" or boxtype == "dm500hdv2":
	config.plugins.dflash.volsize = ConfigInteger(default = 402, limits = (59, rambo_maxflash))
else:
	config.plugins.dflash.volsize = ConfigInteger(default = 59, limits = (40, rambo_maxflash))
config.plugins.dflash.console = ConfigBoolean(default = True, descriptions=yes_no_descriptions)
config.plugins.dflash.subpage = ConfigBoolean(default = True, descriptions=yes_no_descriptions)
config.plugins.dflash.debug = ConfigInteger(default = 0, limits = (0, 3))

bcompression=[]                    
bcompression.append(( "zlib", _("zlib") ))
bcompression.append(( "none", _("none") ))
config.plugins.dflash.jffs2bootcompression = ConfigSelection(default = "zlib", choices = bcompression)


jcompression=[]                    
jcompression.append(( "zlib", _("zlib") ))
jcompression.append(( "none", _("none") ))
config.plugins.dflash.jffs2rootcompression = ConfigSelection(default = "zlib", choices = jcompression)

ucompression=[]                    
ucompression.append(( "none", _("none") ))
ucompression.append(( "lzo", _("lzo") ))
ucompression.append(( "favor_lzo", _("favor_lzo") ))
ucompression.append(( "zlib", _("zlib") ))
if boxtype == "dm8000" or boxtype.startswith("dm7020hd") or boxtype == "dm800sev2" or boxtype == "dm500hdv2":
	config.plugins.dflash.ubifsrootcompression = ConfigSelection(default = "favor_lzo", choices = ucompression)
	config.plugins.dflash.ubifsdatacompression = ConfigSelection(default = "favor_lzo", choices = ucompression)
else:
	config.plugins.dflash.ubifsrootcompression = ConfigSelection(default = "zlib", choices = ucompression)
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
#backuptools.append(( "nanddump", _("nanddump") ))
f=open("/proc/mounts","r")
mm=f.read()
f.close()
if mm.find("/ ubifs") is not -1 and boxtype != "dm800" and boxtype != "dm7025":
	config.plugins.dflash.backuptool = ConfigSelection(default = "mkfs.ubifs", choices = backuptools)
else:
	config.plugins.dflash.backuptool = ConfigSelection(default = "mkfs.jffs2", choices = backuptools)
config.plugins.dflash.overwrite = ConfigBoolean(default = False, descriptions=yes_no_descriptions)

exectools=[]
exectools.append(( "daemon", _("daemon") ))
exectools.append(( "system", _("system") ))
exectools.append(( "container", _("container") ))
config.plugins.dflash.exectool = ConfigSelection(default = "system", choices = exectools)

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
dflash_backuping +="<br><form method=\"GET\">"
dflash_backuping +="<input name=\"command\" type=\"submit\" size=\"100px\" title=\"%s\" value=\"%s\">" % (refresh_string,"Refresh")
dflash_backuping +="</form>"                        

global dflash_progress
dflash_progress=0

class dFlash(Screen):
	skin = """
		<screen position="center,80" size="680,70" title="Flashing" >
		<widget name="logo" position="10,10" size="100,40" transparent="1" alphatest="on" />
		<widget name="buttonred" position="120,10" size="130,40" backgroundColor="red" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
		<widget name="buttongreen" position="260,10" size="130,40" backgroundColor="green" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
		<widget name="buttonyellow" position="400,10" size="130,40" backgroundColor="yellow" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
		<widget name="buttonblue" position="540,10" size="130,40" backgroundColor="blue" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
		<widget name="slider" position="10,55" size="660,5"/>
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
		self.slider = Slider(0, 100)
	        self["slider"] = self.slider
		                         
	       	if not os.path.exists("/usr/bin/zip"):
      			config.plugins.dflash.zip.value=False
		
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
                self.slider.setValue(0)
                
	def leaving(self):
	        if os.path.exists(dflash_busy):
#			os.remove(dflash_busy)
			self.session.openWithCallback(self.forcedexit,MessageBox, running_string, MessageBox.TYPE_WARNING)
		else:
			self.forcedexit(1)
			
	def forcedexit(self,status):
#		print "[dFLASH] status %d\n" % status
		if status != 0:
		        self.doUnhide(0, 0)                                  
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
       				self.session.openWithCallback(self.askForImage,ChoiceBox,fileupload_string,self.getImageList())

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
                        open(dflash_busy, 'a').close()
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
  			
			self.writesize="512"
			if os.path.exists("/sys/devices/virtual/mtd/mtd0/writesize"):
				w=open("/sys/devices/virtual/mtd/mtd0/writesize","r")
				self.writesize=w.read()
				w.close()
				self.writesize=self.writesize.replace("\n","").replace("\l","")
			else:	
				flashdev="/dev/mtd/0"
			        if os.path.exists("/dev/mtd0"):
			       		flashdev="/dev/mtd0"
     			        fd=open(flashdev)
		                mtd_info = array('c',"                                ")
                		memgetinfo=0x40204D01
  		                ioctl(fd.fileno(), memgetinfo, mtd_info)
                		fd.close()
                		tuple=unpack('HLLLLLLL',mtd_info)
                		self.writesize="%s" % tuple[4]
			
			print "[dFLASH] %s %s %i %s %s" % (machine_type,dreambox,loaderversion,header[:4],self.writesize)
			if machine_type.startswith(dreambox) is False and dreambox is not "dm7020":                                        
				print "[dFLASH] wrong header"
				self.session.open(MessageBox, nonfi_string, MessageBox.TYPE_ERROR)
			elif (dreambox == "dm800" or dreambox == "dm800se" or dreambox == "dm500hd" or dreambox == "dm7020hd") and loaderversion < 84 and header[:4] == "NFI2":
				print "[dFLASH] wrong header"
				self.session.open(MessageBox, nonfi_string, MessageBox.TYPE_ERROR)
			elif (dreambox == "dm7020hd") and loaderversion < 87 and header[:4] == "NFI3":
				print "[dFLASH] wrong header"
				self.session.open(MessageBox, nonfi_string, MessageBox.TYPE_ERROR)
			elif (dreambox == "dm800" or dreambox == "dm800se" or dreambox == "dm500hd" or dreambox == "dm800sev2" or dreambox == "dm500hdv2") and loaderversion >= 84 and header[:4] != "NFI2":
				print "[dFLASH] wrong header"
				self.session.open(MessageBox, nonfi_string, MessageBox.TYPE_ERROR)
			elif dreambox == "dm8000" and header[:4] != "NFI1":
				print "[dFLASH] wrong header"
				self.session.open(MessageBox, nonfi_string, MessageBox.TYPE_ERROR)
			elif dreambox == "dm7020hd" and header[:4] == "NFI3" and self.writesize == "4096":
				print "[dFLASH] wrong header"
				self.session.open(MessageBox, nonfi_string, MessageBox.TYPE_ERROR)
			else:
				if config.plugins.dflash.flashtool.value == "rambo":
					self.session.openWithCallback(self.askForDevice,ChoiceBox,_("choose rambo device"),self.getDeviceList())
				elif config.plugins.dflash.flashtool.value == "flodder":
					self.session.openWithCallback(self.askForDevice,ChoiceBox,_("choose flodder device"),self.getDeviceList())
				elif config.plugins.dflash.flashtool.value == "recovery":
					self.session.openWithCallback(self.askForDevice,ChoiceBox,_("choose recovery device"),self.getDeviceList())
				elif config.plugins.dflash.flashtool.value == "rawdevice":
					self.session.openWithCallback(self.askForDevice,ChoiceBox,_("choose raw device"),self.getDeviceList())
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
					if name.endswith(".nfi") or name.endswith(".nfi.zip") and not os.path.exists("/media/%s/autoexec_%s.bat" % (directoy,self.boxtype)) and not os.path.exists("/media/%s/autoexec_%s.none" % (directoy,self.boxtype)):
                 				list.append(( name.replace(".nfi.zip","").replace(".nfi",""), "/media/%s/%s" % (directory,name) ))                         
		if config.plugins.dflash.sort.value:
			list.sort()
        	return list                                                

	def startFlash(self,option):
        	if option is False:
			self.session.open(MessageBox, _("Sorry, Flashing of %s was canceled!") % self.nfifile, MessageBox.TYPE_ERROR)
        	else:
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
				if config.plugins.dflash.flashtool.value == "recovery":
                        		if len(devname) == 8 and mbsize < 36000 and mbsize > 480 and swaps.find(devname) is -1:
						# only sticks from 512 MB up to 32GB are used as recovery sticks
	                        		found=True
        	                                devlist.append(("%s %d %s" % (devname,mbsize,"MB"), devname,mbsize))
				else:
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
			if config.plugins.dflash.flashtool.value == "recovery":
				self.session.openWithCallback(self.strangeFlash,MessageBox,_("Are you sure that you want to FORMAT recovery device %s now for %s ?") % (self.device, self.nfifile), MessageBox.TYPE_YESNO)
			else:
				self.session.openWithCallback(self.strangeFlash,MessageBox,_("Are you sure that you want to flash now %s ?") %(self.nfifile), MessageBox.TYPE_YESNO)
	        
	def strangeFlash(self,option):                                                                            
        	if option is False:
			self.session.open(MessageBox, _("Sorry, Flashing of %s was canceled!") % self.nfifile, MessageBox.TYPE_ERROR)
		else:
                        open(dflash_busy, 'a').close()
                       	if self.boxtype == "dm800se" or self.boxtype == "dm500hd":
	                       	os.system("umount /media/union")                                                            
                        if not os.path.exists("/tmp/strange"):
	                        os.mkdir("/tmp/strange")
	                else:
                        	os.system("umount /tmp/strange")                                                            
			if config.plugins.dflash.flashtool.value == "rawdevice":
                       		self["logo"].instance.setPixmapFromFile("%s/ring.png" % dflash_plugindir)                      
                               	command="%s/nfiwrite -r %s %s" % (dflash_bin, self.device, self.nfifile)                                
                        else:
				if config.plugins.dflash.flashtool.value != "recovery":
	        	                os.system("mount %s /tmp/strange" % self.device)                                                            
	               		f=open("/proc/mounts", "r")
     	  		 	m = f.read()                                                    
       			 	f.close()
       		 		if m.find("/tmp/strange") is not -1 or config.plugins.dflash.flashtool.value == "recovery":
                        		self["logo"].instance.setPixmapFromFile("%s/ring.png" % dflash_plugindir)                      
					if config.plugins.dflash.flashtool.value == "rambo":
		                       		for name in os.listdir("/tmp/strange"):                                                          
			                               	if name.endswith(".nfi"):                                                              
	        		                               	os.remove("/tmp/strange/%s" % name)                                              
	                        	        command="cp %s /tmp/strange/%s.nfi" % (self.nfifile,self.nfiname)                                
					elif config.plugins.dflash.flashtool.value == "recovery":
						if os.path.exists("/usr/lib/enigma2/python/Plugins/Bp/geminimain/lib/libgeminimain.so"):
							libgeminimain.setHWLock(1)
					   	os.system("umount /media/RECOVERY")
					   	os.system("umount /media/recovery")
					   	os.system("umount %s1" % self.device)
					   	os.system("umount %s1" % self.device)
					   	os.system("umount %s2" % self.device)
					   	os.system("umount %s2" % self.device)
					   	os.system("umount %s3" % self.device)
					   	os.system("umount %s3" % self.device)
					   	os.system("umount %s4" % self.device)
					   	os.system("umount %s4" % self.device)
						f=open("/proc/mounts","r")
						lll=f.readline()
						mp=[]
						while (lll):                                                                                                                        
							mp=lll.split()
#							print mp
							if os.path.islink(mp[0]):
			                       			path=os.readlink(mp[0])
			                       			path=path.replace("../../","/dev/")
			                       			if path.find(self.device) is not -1:
			     	                  			print "[dFlash] umounts also path: %s link: %s mount: %s" % (path,mp[0], mp[1])
							   		os.system("umount -f %s" % mp[1])
							lll=f.readline()
						f.close()
					   	# check if umounts failed
						f=open("/proc/mounts","r")
						mm=f.read()
						f.close()
						if mm.find(self.device) is not -1:
							self.session.open(MessageBox, _("umount failed, Sorry!"), MessageBox.TYPE_ERROR)
							if os.path.exists(dflash_busy):
								os.remove(dflash_busy)
							return
						else:
							self.session.open(MessageBox, running_string, MessageBox.TYPE_INFO, timeout=30)
						# let's partition and format now as FAT on 
						# a single primary partition to be sure that device is ONLY for recovery
	   					command ="#!/bin/sh\n"
					   	command +="fdisk %s << EOF\n" % self.device
						command +="d\n" 
						command +="1\n" 
						command +="d\n" 
						command +="2\n" 
						command +="d\n" 
						command +="3\n" 
						command +="d\n" 
						command +="n\n" 
						command +="p\n" 
						command +="1\n" 
						command +="\n" 
						command +="\n" 
						command +="w\n" 
					   	command +="EOF\n"
						command +="partprobe %s\n" % self.device  
				   		command +="fdisk %s << EOF\n" % self.device
					  	command +="t\n"
					  	command +="6\n"
					  	command +="a\n"
					  	command +="1\n"
					  	command +="w\n"
					   	command +="EOF\n"
						command +="partprobe %s\n" % self.device  
		                        	command +="mkdosfs -n RECOVERY %s1\n" % self.device
					   	command +="exit 0\n"
		                        	os.system(command)                                                            
						if os.path.exists("/usr/lib/enigma2/python/Plugins/Bp/geminimain/lib/libgeminimain.so"):
							libgeminimain.setHWLock(0)
		                        	if self.boxtype == "dm800se" or self.boxtype == "dm500hd":
		                        		modules_ipk="dreambox-dvb-modules-sqsh-img"
		                        	else:
		                        		modules_ipk="dreambox-dvb-modules"
		        	                os.system("mount %s1 /tmp/strange" % self.device)                                                            
		        	                # dirty check for read only filesystem
		       		 		os.system("mkdir /tmp/strange/sbin")
		       		 		if not os.path.exists("/tmp/strange/sbin"):
							if os.path.exists(dflash_busy):
								os.remove(dflash_busy)
							self.session.open(MessageBox, _("Sorry, %s device not mounted writeable") % self.device, MessageBox.TYPE_ERROR)
							return
		                       		for name in os.listdir("/tmp/strange"):                                                          
			                               	if name.endswith(".nfi"):                                                              
	        		                               	os.remove("/tmp/strange/%s" % name)                                              
		       		 		if not os.path.exists("/tmp/strange/sbin"):
			       		 		os.mkdir("/tmp/strange/sbin")
		       		 		if not os.path.exists("/tmp/strange/etc"):
			       		 		os.mkdir("/tmp/strange/etc")
		       		 		if not os.path.exists("/tmp/strange/tmp"):
			       		 		os.mkdir("/tmp/strange/tmp")
						if os.path.exists("/tmp/boot"):
							for file in os.listdir("/tmp/boot"):
  								os.remove("/tmp/boot/%s" % file)
  						else:
  							os.mkdir("/tmp/boot")
						if os.path.exists("/tmp/out") is True:
							os.remove("/tmp/out")
						os.system("wget -q http://www.oozoon-dreamboxupdate.de/opendreambox/2.0/experimental/%s -O /tmp/out" % self.boxtype)
						if not os.path.exists("/tmp/out"):
							# use kernel from flash as we seem to be offline ...
		                        	        command="cp %s/nfiwrite /tmp/strange/sbin/nfiwrite; cp /boot/vmlinux*.gz /tmp/strange; cp /boot/bootlogo*elf* /tmp/strange; cp %s/recovery.jpg /tmp/strange; cp %s /tmp/strange/%s.nfi" % (dflash_bin, dflash_bin, self.nfifile,self.nfiname)                                
						else:
							# use kernel from OoZooN feed as we seem to be online ...
		                        	        command="cp %s/nfiwrite /tmp/strange/sbin/nfiwrite; cp /tmp/boot/vmlinux*.gz /tmp/strange; cp /boot/bootlogo*elf* /tmp/strange; cp %s/recovery.jpg /tmp/strange; cp %s /tmp/strange/%s.nfi" % (dflash_bin, dflash_bin, self.nfifile,self.nfiname)                                
					   		f = open("/tmp/out", "r")
							line = f.readline()
   							sp=[]
							sp2=[]
							while (line):
								line = f.readline()
								if line.find("kernel-image") is not -1:
#									print line
									sp = line.split("kernel-image")
									if len(sp) > 0:
#									       	print sp[1]
										sp2= sp[1].split(".ipk")
#								 	        print sp2[0]
										kernel="kernel-image%s.ipk" % sp2[0]
										print "[dFlash] found %s" % kernel
										if os.path.exists("/tmp/kernel.ipk"):
											os.remove("/tmp/kernel.ipk")
										os.system("wget -q http://www.oozoon-dreamboxupdate.de/opendreambox/2.0/experimental/%s/%s -O /tmp/kernel.ipk" % (self.boxtype,kernel))
										if os.path.exists("/tmp/kernel.ipk"):
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/control.tar.gz"):
												os.remove("/tmp/control.tar.gz")
											os.system("cd /tmp; ar -x /tmp/kernel.ipk")
											os.system("tar -xzf /tmp/data.tar.gz -C /tmp")
											os.remove("/tmp/kernel.ipk")
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/control.tar.gz"):
												os.remove("/tmp/control.tar.gz")
       								if line.find(modules_ipk) is not -1:
#     	  								print line
          								sp = line.split(modules_ipk)
									if len(sp) > 0:
#									       	print sp[1]
								          	sp2= sp[1].split(".ipk")
#								  	        print sp2[0]
								          	modules="%s%s.ipk" % (modules_ipk,sp2[0])
    									      	print "[dFlash] found %s ..." % modules
										if os.path.exists("/tmp/modules.ipk"):
											os.remove("/tmp/modules.ipk")
										os.system("wget -q http://www.oozoon-dreamboxupdate.de/opendreambox/2.0/experimental/%s/%s -O /tmp/modules.ipk" % (self.boxtype,modules))
										if os.path.exists("/tmp/modules.ipk"):
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/control.tar.gz"):
												os.remove("/tmp/control.tar.gz")
											os.system("cd /tmp; ar -x /tmp/modules.ipk")
											os.system("tar -xzf /tmp/data.tar.gz -C /tmp/strange")
											os.remove("/tmp/modules.ipk")
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/strange/squashfs-images/dreambox-dvb-modules-sqsh-img"):
	    									      		print "[dFlash] loop mounts %s ..." % modules
												os.system("mount -t squashfs -o ro,loop /tmp/strange/squashfs-images/dreambox-dvb-modules-sqsh-img /media/union")
												os.system("mkdir -p /tmp/strange/lib/modules/3.2-%s/extra" % self.boxtype)
												os.system("cp /media/union/lib/modules/3.2-%s/extra/* /tmp/strange/lib/modules/3.2-%s/extra" % (self.boxtype,self.boxtype))
												os.system("umount /media/union")
												os.remove("/tmp/strange/squashfs-images/dreambox-dvb-modules-sqsh-img")
												os.rmdir("/tmp/strange/squashfs-images")
												os.rmdir("/tmp/strange/media/squashfs-images/dreambox-dvb-modules-sqsh-img")
												os.rmdir("/tmp/strange/media/squashfs-images")
												os.rmdir("/tmp/strange/media")
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/control.tar.gz"):
												os.remove("/tmp/control.tar.gz")
       								if line.find("kernel-module-snd-pcm") is not -1:
#     	  								print line
          								sp = line.split("kernel-module-snd-pcm")
									if len(sp) > 0:
#									       	print sp[1]
								          	sp2= sp[1].split(".ipk")
#								  	        print sp2[0]
								          	modules="kernel-module-snd-pcm%s.ipk" % sp2[0]
    									      	print "[dFlash] found %s ..." % modules
										if os.path.exists("/tmp/modules.ipk"):
											os.remove("/tmp/modules.ipk")
										os.system("wget -q http://www.oozoon-dreamboxupdate.de/opendreambox/2.0/experimental/%s/%s -O /tmp/modules.ipk" % (self.boxtype,modules))
										if os.path.exists("/tmp/modules.ipk"):
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/control.tar.gz"):
												os.remove("/tmp/control.tar.gz")
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
											os.system("cd /tmp; ar -x /tmp/modules.ipk")
											os.system("tar -xzf /tmp/data.tar.gz -C /tmp/strange")
											os.remove("/tmp/modules.ipk")
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/control.tar.gz"):
												os.remove("/tmp/control.tar.gz")
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
       								if line.find("kernel-module-snd-timer") is not -1:
#     	  								print line
          								sp = line.split("kernel-module-snd-timer")
									if len(sp) > 0:
#									       	print sp[1]
								          	sp2= sp[1].split(".ipk")
#								  	        print sp2[0]
								          	modules="kernel-module-snd-timer%s.ipk" % sp2[0]
    									      	print "[dFlash] found %s ..." % modules
										if os.path.exists("/tmp/modules.ipk"):
											os.remove("/tmp/modules.ipk")
										os.system("wget -q http://www.oozoon-dreamboxupdate.de/opendreambox/2.0/experimental/%s/%s -O /tmp/modules.ipk" % (self.boxtype,modules))
										if os.path.exists("/tmp/modules.ipk"):
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/control.tar.gz"):
												os.remove("/tmp/control.tar.gz")
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
											os.system("cd /tmp; ar -x /tmp/modules.ipk")
											os.system("tar -xzf /tmp/data.tar.gz -C /tmp/strange")
											os.remove("/tmp/modules.ipk")
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/control.tar.gz"):
												os.remove("/tmp/control.tar.gz")
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
       								if line.find("kernel-module-snd-page-alloc") is not -1:
#     	  								print line
          								sp = line.split("kernel-module-snd-page-alloc")
									if len(sp) > 0:
#									       	print sp[1]
								          	sp2= sp[1].split(".ipk")
#								  	        print sp2[0]
								          	modules="kernel-module-snd-page-alloc%s.ipk" % sp2[0]
    									      	print "[dFlash] found %s ..." % modules
										if os.path.exists("/tmp/modules.ipk"):
											os.remove("/tmp/modules.ipk")
										os.system("wget -q http://www.oozoon-dreamboxupdate.de/opendreambox/2.0/experimental/%s/%s -O /tmp/modules.ipk" % (self.boxtype,modules))
										if os.path.exists("/tmp/modules.ipk"):
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/control.tar.gz"):
												os.remove("/tmp/control.tar.gz")
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
											os.system("cd /tmp; ar -x /tmp/modules.ipk")
											os.system("tar -xzf /tmp/data.tar.gz -C /tmp/strange")
											os.remove("/tmp/modules.ipk")
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/control.tar.gz"):
												os.remove("/tmp/control.tar.gz")
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
       								if line.find("kernel-module-stv0299") is not -1:
#     	  								print line
          								sp = line.split("kernel-module-stv0299")
									if len(sp) > 0:
#									       	print sp[1]
								          	sp2= sp[1].split(".ipk")
#								  	        print sp2[0]
								          	modules="kernel-module-stv0299%s.ipk" % sp2[0]
    									      	print "[dFlash] found %s ..." % modules
										if os.path.exists("/tmp/modules.ipk"):
											os.remove("/tmp/modules.ipk")
										os.system("wget -q http://www.oozoon-dreamboxupdate.de/opendreambox/2.0/experimental/%s/%s -O /tmp/modules.ipk" % (self.boxtype,modules))
										if os.path.exists("/tmp/modules.ipk"):
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/control.tar.gz"):
												os.remove("/tmp/control.tar.gz")
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
											os.system("cd /tmp; ar -x /tmp/modules.ipk")
											os.system("tar -xzf /tmp/data.tar.gz -C /tmp/strange")
											os.remove("/tmp/modules.ipk")
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/control.tar.gz"):
												os.remove("/tmp/control.tar.gz")
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
							f.close()
							os.system("depmod -b /tmp/strange")
						if os.path.exists("/tmp/strange/lib"):
							bootfile ="/boot/bootlogo-%s.elf.gz filename=/boot/recovery.jpg\n/boot/vmlinux-3.2-%s.gz console=ttyS0,115200 init=/sbin/nfiwrite rootdelay=10 root=LABEL=RECOVERY rootfstype=vfat rw\n" % (self.boxtype,self.boxtype)
	                        	        	a=open("/tmp/strange/autoexec_%s.bat" % self.boxtype, "w")
	                        	        	a.write(bootfile)
	                        	        	a.close()
	                        	        else:
							self.session.open(MessageBox, _("recovery creation failed, Sorry!"), MessageBox.TYPE_ERROR)
							if os.path.exists(dflash_busy):
								os.remove(dflash_busy)
							return
					elif config.plugins.dflash.flashtool.value == "flodder":
			                        if os.path.exists("/tmp/strange/flodder"):
				                        if os.path.exists("/tmp/strange/removed"):
				                        	os.system("rm -r /tmp/strange/removed")
	                        	                os.rename("/tmp/strange/flodder","/tmp/strange/removed")                                              
                                		command="/usr/sbin/nfidump %s --squashfs /tmp/strange/flodder" % (self.nfifile)                                
		                else:
					if os.path.exists(dflash_busy):
						os.remove(dflash_busy)
					self.session.open(MessageBox, _("Sorry, %s device not mounted") % self.device, MessageBox.TYPE_ERROR)
					return
                        print "[dFlash] flash command %s" % command
                        self.container = eConsoleAppContainer()                                                        
                        self.container.appClosed.append(self.strangeDone)                                                                        
                        self.container.execute(command)                                                           

	def strangeDone(self,status):                     
		if os.path.exists(dflash_busy):
			os.remove(dflash_busy)
               	os.system("umount /tmp/strange")                                                            
	        self["logo"].instance.setPixmapFromFile("%s/dflash.png" % dflash_plugindir)
		if config.plugins.dflash.flashtool.value == "rawdevice":
		 	result=_("Copied %s.nfi to %s,\ndon't forget kernel commandline and now\nreboot for activating it ?") % (self.nfiname,self.device)                                    
		elif config.plugins.dflash.flashtool.value == "recovery":
		 	result=_("Copied %s.nfi to %s,\ndon't forget to remove stick\nif you enabled kernel commandline!\nHalt now ?") % (self.nfiname,self.device)                                    
		else:
		 	result=_("Copied %s.nfi to %s,\nreboot for activating it ?") % (self.nfiname,self.device)                                    
	        self.session.openWithCallback(self.doreboot,MessageBox, result, MessageBox.TYPE_YESNO)              
	        
	def doreboot(self,answer):                                                                                                                            
	        if answer is True:                                                                                                                            
			if config.plugins.dflash.flashtool.value == "recovery":
				quitMainloop(1)                 
			else:
				quitMainloop(2)                 

	def doFlash(self,option):
		if option:
			if (eDVBVolumecontrol.getInstance().isMuted()) is False:
				eDVBVolumecontrol.getInstance().volumeToggleMute()
			self.avswitch = AVSwitch()
			if SystemInfo["ScartSwitch"]:
				self.avswitch.setInput("SCART")
			else:
				self.avswitch.setInput("AUX")
			print "[dFLASH] is flashing now %s" % self.nfifile
			FlashingImage(self.nfifile)
		else:
			print "[dFLASH] cancelled flashing %s" % self.nfifile

	def cancel(self):
		self.close(False)

	def backup(self):
		global dflash_progress
		if os.path.exists(dflash_backup):
 			print "[dFLASH] found finished backup ..."
			dflash_progress=0
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
			# checking for IO Errors
			l=""
			if os.path.exists(dflash_backuplog):
				b=open(dflash_backuplog)
				l=b.read()
				b.close()
			if l.find("Input/output err") is not -1:
				self.session.open(MessageBox,size+"B "+_("Flash Backup to %s finished with imagename:\n\n%s.nfi\n\nBUT it has I/O Errors") % (path,image),  MessageBox.TYPE_ERROR)                 
			else:
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
						print "[dFLASH] swappable"
						self.swappable=True
           			m = f.readline()                                                 
			f.close()	
			if not mounted:
 	             		self.session.open(MessageBox,mounted_string % path,  MessageBox.TYPE_ERROR)                 
				return
			path=path.lstrip().rstrip("/").rstrip().replace(" ","")
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
			self.writesize="512"
			if os.path.exists("/sys/devices/virtual/mtd/mtd0/writesize"):
				w=open("/sys/devices/virtual/mtd/mtd0/writesize","r")
				self.writesize=w.read()
				w.close()
				self.writesize=self.writesize.replace("\n","").replace("\l","")
			else:	
				flashdev="/dev/mtd/0"
			        if os.path.exists("/dev/mtd0"):
			       		flashdev="/dev/mtd0"
     			        fd=open(flashdev)
		                mtd_info = array('c',"                                ")
                		memgetinfo=0x40204D01
  		                ioctl(fd.fileno(), memgetinfo, mtd_info)
                		fd.close()
                		tuple=unpack('HLLLLLLL',mtd_info)
                		self.writesize="%s" % tuple[4]
                	if (self.boxtype == "dm7020hd") and (self.writesize == "2048") and not config.plugins.dflash.switchversion.value:
                		self.boxtype="dm7020hdv2"
                	elif (self.boxtype == "dm7020hd") and (self.writesize == "4096") and config.plugins.dflash.switchversion.value:
                		self.boxtype="dm7020hdv2"
                	else:	
                		pass
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
                 self.session.openWithCallback(self.startBackup,MessageBox, _("Press OK for starting backup to") + "\n\n%s.nfi" % self.backupname + "\n\n" + _("Be patient, this takes 5-10min ... ") + action_string, MessageBox.TYPE_INFO)
	      else:
              	 self.session.open(MessageBox,_("not confirmed"),  MessageBox.TYPE_ERROR)                 
		
        def startBackup(self,answer):
              if answer is True:
	         print "[dFLASH] is backuping now ..."
                 self["logo"].instance.setPixmapFromFile("%s/ring.png" % dflash_plugindir)
                 self.doHide()
		 self.TimerBackup = eTimer()                                       
		 self.TimerBackup.stop()                                           
		 self.TimerBackup.timeout.get().append(self.backupFinishedCheck)
		 self.TimerBackup.start(10000,True)                                 
	         BackupImage(self.backupname,self.imagetype,self.creator,self.swappable,self.ownswap)
		 
        def backupFinishedCheck(self):
		global dflash_progress
		if not os.path.exists(dflash_backup):
			# not finished - continue checking ...
			rsize=0
			dsize=0
			bsize=0
			ssize=0
			nsize=0
			bused=0
			rused=0
			dused=0
			sused=0
			
			if os.path.exists("%s/r.ubi" % config.plugins.dflash.backuplocation.value):
				rsize=os.path.getsize("%s/r.ubi" % config.plugins.dflash.backuplocation.value)
			if os.path.exists("%s/d.ubi" % config.plugins.dflash.backuplocation.value):
				dsize=os.path.getsize("%s/d.ubi" % config.plugins.dflash.backuplocation.value)
			if os.path.exists("%s/r.img" % config.plugins.dflash.backuplocation.value):
				rsize=os.path.getsize("%s/r.img" % config.plugins.dflash.backuplocation.value)
			if os.path.exists("%s/b.img" % config.plugins.dflash.backuplocation.value):
				bsize=os.path.getsize("%s/b.img" % config.plugins.dflash.backuplocation.value)
			if os.path.exists("%s/s.bin" % config.plugins.dflash.backuplocation.value):
				ssize=os.path.getsize("%s/s.bin" % config.plugins.dflash.backuplocation.value)
			if os.path.exists("%s/%s.nfi" % (config.plugins.dflash.backuplocation.value,self.backupname)):
				nsize=os.path.getsize("%s/%s.nfi" % (config.plugins.dflash.backuplocation.value,self.backupname))
			total_size=ssize+bsize+rsize+dsize
			st = os.statvfs("/boot")                                                    
			bused = (st.f_blocks - st.f_bfree) * st.f_frsize        
			st = os.statvfs("/")                                                    
			rused = (st.f_blocks - st.f_bfree) * st.f_frsize        
			if config.plugins.dflash.databackup.value and os.path.exists("/data"):  
				st = os.statvfs("/data")                                                    
				dused = (st.f_blocks - st.f_bfree) * st.f_frsize        
			s=open("/proc/swaps")
			swap=s.read()
			s.close()
			if swap.find("/flodder/root") is not -1:
				s=open("/proc/swaps")
				swap=s.readline()
				swap=s.readline()
				s.close()
				sw=[]
				sw=swap.split()
				print "[dFlash] swap %s Bytes\n" % sw[2]
				sused=int(sw[2])*1024
			used=bused+rused+dused-sused
			if used < 0:
				used=used+sused
			# if Flodder it is uncompressed
			if sused > 0:
				used=used/2
			print "[dFlash] total size %d used %d\n" % (total_size,used)
	                dflash_progress=90*total_size/used
			if os.path.exists("%s/%s.nfi" % (config.plugins.dflash.backuplocation.value,self.backupname)):
				dflash_progress=95
			self.slider.setValue(dflash_progress)
 			print "[dFLASH] checked if backup is finished ..."
			self.TimerBackup.start(5000,True)                                 
		else:
 			print "[dFLASH] found finished backup ..."
			dflash_progress=0
	                self.slider.setValue(0)
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
				else:
					image=""
			if config.plugins.dflash.fade.value:
	                	f=open("/proc/stb/video/alpha","w")
        	       		f.write("%i" % (config.osd.alpha.getValue()))
                		f.close()
			print "[dFLASH] found backup %s" % line
			# checking for IO Errors
			l=""
			if os.path.exists(dflash_backuplog):
				b=open(dflash_backuplog)
				l=b.read()
				b.close()
			try:
				if l.find("Input/output err") is not -1:
					self.session.open(MessageBox,"%sB " % (size) +_("Flash Backup to %s finished with imagename:\n\n%s.nfi\n\nBUT it has I/O Errors") % (path,image),  MessageBox.TYPE_ERROR)                 
				else:
					self.session.open(MessageBox,"%sB " % (size) +_("Flash Backup to %s finished with imagename:\n\n%s.nfi") % (path,image),  MessageBox.TYPE_INFO)                 
			except:
				# why crashes even this
#				self.session.open(MessageBox,_("Flash Backup to %s finished with imagename:\n\n%s.nfi") % (path,image),  MessageBox.TYPE_INFO)                 
				self.session.open(MessageBox,_("Flash Backup finished"),  MessageBox.TYPE_INFO)                 

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
		global dflash_progress
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
			dflash_backuping_progress  =""
			dflash_backuping_progress += header_string
			dflash_backuping_progress += "<br>%s<br><br>" % running_string
			dflash_backuping_progress +="<br><img src=\"/web-data/img/ring.png\" alt=\"%s ...\"/><br><br>" % (backup_string)
			if dflash_progress > 0:
				dflash_backuping_progress +="<div style=\"background-color:yellow;width:%dpx;height:20px;border:1px solid #000\"></div> " % (dflash_progress)
			dflash_backuping_progress +="<br><form method=\"GET\">"
			dflash_backuping_progress +="<input name=\"command\" type=\"submit\" size=\"100px\" title=\"%s\" value=\"%s\">" % (refresh_string,"Refresh")
			dflash_backuping_progress +="</form>"                        
			return header_string+dflash_backuping_progress
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
			self.writesize="512"
			if os.path.exists("/sys/devices/virtual/mtd/mtd0/writesize"):
				w=open("/sys/devices/virtual/mtd/mtd0/writesize","r")
				self.writesize=w.read()
				w.close()
				self.writesize=self.writesize.replace("\n","").replace("\l","")
			else:	
				flashdev="/dev/mtd/0"
			        if os.path.exists("/dev/mtd0"):
			       		flashdev="/dev/mtd0"
     			        fd=open(flashdev)
		                mtd_info = array('c',"                                ")
                		memgetinfo=0x40204D01
  		                ioctl(fd.fileno(), memgetinfo, mtd_info)
                		fd.close()
                		tuple=unpack('HLLLLLLL',mtd_info)
                		self.writesize="%s" % tuple[4]
                	if (self.boxtype == "dm7020hd") and (self.writesize == "2048") and not config.plugins.dflash.switchversion.value:
                		self.boxtype="dm7020hdv2"
                	elif (self.boxtype == "dm7020hd") and (self.writesize == "4096") and config.plugins.dflash.switchversion.value:
                		self.boxtype="dm7020hdv2"
                	else:	
                		pass
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
  					
					self.writesize="512"
					if os.path.exists("/sys/devices/virtual/mtd/mtd0/writesize"):
						w=open("/sys/devices/virtual/mtd/mtd0/writesize","r")
						self.writesize=w.read()
						w.close()
						self.writesize=self.writesize.replace("\n","").replace("\l","")
					else:
						flashdev="/dev/mtd/0"
					        if os.path.exists("/dev/mtd0"):
					       		flashdev="/dev/mtd0"
		     			        fd=open(flashdev)
				                mtd_info = array('c',"                                ")
 			               		memgetinfo=0x40204D01
  		        		        ioctl(fd.fileno(), memgetinfo, mtd_info)
     			           		fd.close()
                				tuple=unpack('HLLLLLLL',mtd_info)
                				self.writesize="%s" % tuple[4]
					print "[dFLASH] %s %s %i %s %s" % (machine_type,dreambox,loaderversion,header[:4],self.writesize)

					if machine_type.startswith(dreambox) is False and dreambox is not "dm7020":                                        
						print "[dFLASH] wrong header"
						return header_string+nonfi_string
					elif (dreambox == "dm800" or dreambox == "dm800se" or dreambox == "dm500hd" or dreambox == "dm7020hd") and loaderversion < 84 and header[:4] == "NFI2":
						print "[dFLASH] wrong header"
						return header_string+nonfi_string
					elif dreambox == "dm7020hd" and loaderversion < 87 and header[:4] == "NFI3":
						print "[dFLASH] wrong header"
						return header_string+nonfi_string
					elif (dreambox == "dm800" or dreambox == "dm800se" or dreambox == "dm500hd" or dreambox == "dm800sev2" or dreambox == "dm500hdv2") and loaderversion >= 84 and header[:4] != "NFI2":
						print "[dFLASH] wrong header"
						return header_string+nonfi_string
					elif dreambox == "dm8000" and header[:4] != "NFI1":
						print "[dFLASH] wrong header"
						return header_string+nonfi_string
					elif dreambox == "dm7020hd" and header[:4] == "NFI3" and self.writesize == "4096":
						print "[dFLASH] wrong header"
						return header_string+nonfi_string
					else:
						print "[dFLASH] correct header"
					if (eDVBVolumecontrol.getInstance().isMuted()) is False:
						eDVBVolumecontrol.getInstance().volumeToggleMute()
					self.avswitch = AVSwitch()
					if SystemInfo["ScartSwitch"]:
						self.avswitch.setInput("SCART")
					else:
						self.avswitch.setInput("AUX")
					print "[dFLASH] is flashing now %s" % self.nfifile
					FlashingImage(self.nfifile)
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
			path=path.lstrip().rstrip("/").rstrip().replace(" ","")
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
					self.TimerBackup = eTimer()                                       
					self.TimerBackup.stop()                                           
					self.TimerBackup.timeout.get().append(self.backupFinishedCheck)
					self.TimerBackup.start(10000,True)                                 
                 			BackupImage(self.backupname,self.imagetype,self.creator,self.swappable,self.ownswap)
					return header_string+dflash_backuping
		   else:
			print "[dFLASH] unknown command"
              		return header_string+_("nothing entered")                 

        def backupFinishedCheck(self):
		global dflash_progress
		if not os.path.exists(dflash_backup):
			# not finished - continue checking ...
			rsize=0
			dsize=0
			bsize=0
			ssize=0
			nsize=0
			bused=0
			rused=0
			dused=0
			sused=0
			
			if os.path.exists("%s/r.ubi" % config.plugins.dflash.backuplocation.value):
				rsize=os.path.getsize("%s/r.ubi" % config.plugins.dflash.backuplocation.value)
			if os.path.exists("%s/d.ubi" % config.plugins.dflash.backuplocation.value):
				dsize=os.path.getsize("%s/d.ubi" % config.plugins.dflash.backuplocation.value)
			if os.path.exists("%s/r.img" % config.plugins.dflash.backuplocation.value):
				rsize=os.path.getsize("%s/r.img" % config.plugins.dflash.backuplocation.value)
			if os.path.exists("%s/b.img" % config.plugins.dflash.backuplocation.value):
				bsize=os.path.getsize("%s/b.img" % config.plugins.dflash.backuplocation.value)
			if os.path.exists("%s/s.bin" % config.plugins.dflash.backuplocation.value):
				ssize=os.path.getsize("%s/s.bin" % config.plugins.dflash.backuplocation.value)
			if os.path.exists("%s/%s.nfi" % (config.plugins.dflash.backuplocation.value,self.backupname)):
				nsize=os.path.getsize("%s/%s.nfi" % (config.plugins.dflash.backuplocation.value,self.backupname))
			total_size=ssize+bsize+rsize+dsize+nsize
			st = os.statvfs("/boot")                                                    
			bused = (st.f_blocks - st.f_bfree) * st.f_frsize        
			st = os.statvfs("/")                                                    
			rused = (st.f_blocks - st.f_bfree) * st.f_frsize        
			if config.plugins.dflash.databackup.value and os.path.exists("/data"):  
				st = os.statvfs("/data")                                                    
				dused = (st.f_blocks - st.f_bfree) * st.f_frsize        
			s=open("/proc/swaps")
			swap=s.read()
			s.close()
			if swap.find("/flodder/root") is not -1:
				s=open("/proc/swaps")
				swap=s.readline()
				swap=s.readline()
				s.close()
				sw=[]
				sw=swap.split()
				print "[dFlash] swap %s Bytes\n" % sw[2]
				sused=int(sw[2])*1024
			used=bused+rused+dused-sused
			if used < 0:
				used=used+sused
			# if Flodder it is uncompressed
			if sused > 0:
				used=used/2
			print "[dFlash] total size %d used %d\n" % (total_size,used)
	                dflash_progress=90*total_size/used
                        if os.path.exists("%s/%s.nfi" % (config.plugins.dflash.backuplocation.value,self.backupname)):
				dflash_progress=95
 			print "[dFLASH] checked if backup is finished ..."
			self.TimerBackup.start(5000,True)                                 
		else:
 			print "[dFLASH] found finished backup ..."
			dflash_progress=0
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
			print "[dFLASH] finished webif backup"
			
class FlashingImage(Screen):                                                      
        def __init__(self,flashimage):            
        	print "[dFLASH] does flashing"
                open(dflash_busy, 'a').close()
		b=open("/proc/stb/info/model","r")
		dreambox=b.read().rstrip("\n")
		b.close()
		print "[dFLASH] Dreambox: !%s!" % dreambox
		command  = "#!/bin/sh -x\n"
		command += "init 4\n"
		command += "sleep 3\n"
		if dreambox.startswith("dm500hd"):
			command += "echo FFFFFFFF > /proc/stb/fp/led0_pattern\n" 
		else:
			command += "echo 50 > /proc/progress\n"
		if config.plugins.dflash.ramfs.value:
			command += "mkdir /tmp/ramfs\n"
			command += "mount -t ramfs ramfs /tmp/ramfs\n"
			command += "cp \"%s\" /tmp/ramfs/flash.nfi\n" % flashimage
			if config.plugins.dflash.flashtool.value == "writenfi":
				command += "/tmp/dFlash/bin/nfiwrite -w -l -b -r -s -f /tmp/ramfs/flash.nfi\n"
			elif config.plugins.dflash.flashtool.value == "nandwrite":
				command += "/tmp/dFlash/bin/nfiwrite -n -l -b -r -s -f /tmp/ramfs/flash.nfi\n"
			else:
				command += "/tmp/dFlash/bin/nfiwrite -l -b -r -s -f /tmp/ramfs/flash.nfi\n"
		else:
			if config.plugins.dflash.flashtool.value == "writenfi":
				command += "/tmp/dFlash/bin/nfiwrite -w -l -b -r -s -f \"%s\"\n" % flashimage
			elif config.plugins.dflash.flashtool.value == "nandwrite":
				command += "/tmp/dFlash/bin/nfiwrite -n -l -b -r -s -f \"%s\"\n" % flashimage
			else:
				command += "/tmp/dFlash/bin/nfiwrite -l -b -r -s -f \"%s\"\n" % flashimage
		command += "exit 0\n"
		b=open(dflash_script,"w")
		b.write(command)
		b.close()
		os.system("chmod 755 %s" % dflash_script)
		print "[dFLASH] %s created and now flashing %s\n" % (dflash_script,flashimage)
		os.system("start-stop-daemon -S -b -n dflash.sh -x %s" % dflash_script)

class BackupImage(Screen):                                                      
        def __init__(self,backupname,imagetype,creator,swappable,ownswap):            
        	print "[dFLASH] does backup"
                open(dflash_busy, 'a').close()
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
	        print "[dFLASH] loaderversion: %i" % (loaderversion) 
		
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
                self.blocksize=512
                
		self.writesize="512"	
		if os.path.exists("/sys/devices/virtual/mtd/mtd0/writesize"):
			w=open("/sys/devices/virtual/mtd/mtd0/writesize","r")
			self.writesize=w.read()
			w.close()
			self.writesize=self.writesize.replace("\n","").replace("\l","")
		else:
			flashdev="/dev/mtd/0"
		        if os.path.exists("/dev/mtd0"):
		       		flashdev="/dev/mtd0"
		        fd=open(flashdev)
		        mtd_info = array('c',"                                ")
 			memgetinfo=0x40204D01
  		        ioctl(fd.fileno(), memgetinfo, mtd_info)
     			fd.close()
                	tuple=unpack('HLLLLLLL',mtd_info)
                	self.writesize="%s" % tuple[4]
		if self.boxtype == "dm8000":
			self.subpagesize=512
		     	self.eraseblocksize=131072        
		        self.minimumiosize=2048       
		        self.lebsize=129024
			self.flashsize="10000000"
			self.loadersize="100000"
			self.bootsize="700000"
			self.rootsize="F800000"
	                self.blocksize=2048
		elif self.boxtype == "dm800sev2":
			self.subpagesize=2048
		     	self.eraseblocksize=131072        
		        self.minimumiosize=2048       
			self.lebsize=126976
			self.flashsize="40000000"
			self.loadersize="100000"
			self.bootsize="700000"
			self.rootsize="3F800000"
	                self.offset=2048
	                self.blocksize=2048
		elif self.boxtype == "dm500hdv2":
			self.subpagesize=2048
		     	self.eraseblocksize=131072        
		        self.minimumiosize=2048       
			self.lebsize=126976
			self.flashsize="40000000"
			self.loadersize="100000"
			self.bootsize="700000"
			self.rootsize="3F800000"
	                self.offset=2048
	                self.blocksize=2048
		elif self.boxtype == "dm7020hd":
			if self.writesize=="4096":
				if not config.plugins.dflash.switchversion.value:  
					self.subpagesize=4096
					self.eraseblocksize=262144       
				        self.lebsize=253952
				        self.minimumiosize=4096      
				        self.offset=4096
			                self.blocksize=4096
			        else:
					self.subpagesize=2048
				     	self.eraseblocksize=131072  
					self.lebsize=126976
					self.minimumiosize=2048       
				        self.offset=2048
	        	 	    	self.blocksize=2048
		        else:
				if not config.plugins.dflash.switchversion.value:  
					self.subpagesize=2048
				     	self.eraseblocksize=131072  
					self.lebsize=126976
					self.minimumiosize=2048       
			        	self.offset=2048
		        	        self.blocksize=2048
		        	else:
					self.subpagesize=4096
					self.eraseblocksize=262144       
				        self.lebsize=253952
				        self.minimumiosize=4096      
				        self.offset=4096
			                self.blocksize=4096
			self.flashsize="10000000"
			self.loadersize="100000"
			self.bootsize="700000"
			self.rootsize="3F800000"
			# ubifs uses full flash on dm7020hd
		      	if config.plugins.dflash.backuptool.value == "mkfs.ubifs":
				self.flashsize="40000000"
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
		c +="image=%s/r.ubi\n" % config.plugins.dflash.backuplocation.value.rstrip("/")
		c +="vol_id=0\n"
		c +="vol_name=rootfs\n"
		c +="vol_type=dynamic\n"
		if self.boxtype.startswith("dm7020hd") or self.boxtype == "dm800sev2" or self.boxtype == "dm500hdv2":
			v=int(config.plugins.dflash.volsize.value)
			c +="vol_size=%dMiB\n" % v
			c +="[data]\n"
			c +="mode=ubi\n"
			if config.plugins.dflash.databackup.value:  
				c +="image=%s/d.ubi\n" % config.plugins.dflash.backuplocation.value.rstrip("/")
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
		command +="%s/nanddump --noecc --omitoob --bb=skipbad --truncate --file %s/s.bin %s\n" % (dflash_bin,config.plugins.dflash.backuplocation.value,mtdev)
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
                        if config.plugins.dflash.jffs2bootcompression.value == "none":
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
	                        if config.plugins.dflash.jffs2rootcompression.value == "none":
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
				command +="%s/mkfs.ubifs %s -x %s -v --debug=%d -r /tmp/root -o %s/r.ubi\n" % (dflash_bin,self.ubifsrootoptions, config.plugins.dflash.ubifsrootcompression.value,  config.plugins.dflash.debug.value, config.plugins.dflash.backuplocation.value)
		
				if config.plugins.dflash.databackup.value and (self.boxtype.startswith("dm7020hd") or self.boxtype=="dm500hdv2" or self.boxtype=="dm800sev2"):  
					# make data filesystem ...
					command +="umount /tmp/data\n"
					command +="mkdir /tmp/data\n"
					command +="mount -o bind /data /tmp/data\n"
    		   	         	if config.plugins.dflash.ubifsdatacompression.value == "none":
						command +="chattr -R -c /tmp/data\n"
					command +="touch %s/d.ubi\n" % (config.plugins.dflash.backuplocation.value)
					command +="chmod 777 %s/d.ubi\n" % (config.plugins.dflash.backuplocation.value)
					command +="%s/mkfs.ubifs %s -x %s -v --debug=%d -r /tmp/data -o %s/d.ubi\n" % (dflash_bin,self.ubifsdataoptions, config.plugins.dflash.ubifsdatacompression.value, config.plugins.dflash.debug.value, config.plugins.dflash.backuplocation.value)
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
				command +="%s/nanddump --noecc --omitoob --bb=skipbad --quiet --file %s/b.img /dev/mtd2\n" % (dflash_bin,config.plugins.dflash.backuplocation.value)
				command +="%s/nanddump --noecc --omitoob --bb=skipbad --quiet --file %s/r.img /dev/mtd3\n" % (dflash_bin,config.plugins.dflash.backuplocation.value)
			else:
				command +="%s/nanddump --noecc --omitoob --bb=skipbad --quiet --file %s/b.img /dev/mtd/2\n" % (dflash_bin,config.plugins.dflash.backuplocation.value)
				command +="%s/nanddump --noecc --omitoob --bb=skipbad --quiet --file %s/r.img /dev/mtd/3\n" % (dflash_bin,config.plugins.dflash.backuplocation.value)
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
		if config.plugins.dflash.nfo.value:
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
                self.container = eConsoleAppContainer()                                                        
		start_cmd="start-stop-daemon -K -n dbackup.sh -s 9; start-stop-daemon -S -b -n dbackup.sh -x %s" % (dflash_backupscript)
		if config.plugins.dflash.exectool.value == "daemon":
			print "[dFlash] daemon %s" % dflash_backupscript
	               	self.container.execute(dflash_backupscript)                                                           
		elif config.plugins.dflash.exectool.value == "system":
			print "[dFlash] system %s" % start_cmd
			os.system(start_cmd)
		if config.plugins.dflash.exectool.value == "container":
			print "[dFlash] container %s" % start_cmd
	               	self.container.execute(start_cmd)                                                           

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
	f=open("/proc/mounts","r")
	mm=f.read()
	f.close()
	if mm.find("/ ubifs"):
	   if os.path.exists("/usr/sbin/ubinfo"):
              flashchecklist.append((_("ubinfo"), "ubinfo -a"))
        else:
	   if os.path.exists("/usr/sbin/mtdinfo"):
              flashchecklist.append((_("ubinfo"), "mtdinfo -a"))
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
        	if returnValue.startswith("/dev"):
        		self.session.open(Console,_("checking %s - be patient (up to 1 min)") % returnValue,["%s/nand_check %s\n" % (dflash_bin,returnValue) ])
        	else:
        		self.session.open(Console,returnValue,[returnValue])

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
        <screen position="center,80" size="680,480" title="dFlash Configuration" >
	<widget name="logo" position="10,10" size="100,40" transparent="1" alphatest="on" />
        <widget name="config" position="10,60" size="660,410" scrollbarMode="showOnDemand" />
        <widget name="buttonred" position="120,10" size="130,40" backgroundColor="red" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
        <widget name="buttongreen" position="260,10" size="130,40" backgroundColor="green" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
        <widget name="buttonyellow" position="400,10" size="130,40" backgroundColor="yellow" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
        <widget name="buttonblue" position="540,10" size="130,40" backgroundColor="blue" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;12"/>
        </screen>"""

    def __init__(self, session, args = 0):
	Screen.__init__(self, session)

        self.onShown.append(self.setWindowTitle)
        # explizit check on every entry
	self.onChangedEntry = []
	
        self.list = []                                                  
       	ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)
       	self.createSetup()       

	self["logo"] = Pixmap()
       	self["buttonred"] = Label(_("Cancel"))
       	self["buttongreen"] = Label(_("OK"))
       	self["buttonyellow"] = Label(checking_string)
	self["buttonblue"] = Label(_("Disclaimer"))
	self["actions"] = ActionMap([ "ColorActions", "dFlashActions" ],
       	{
       		"green": self.save,
        	"red": self.cancel,
	       	"yellow": self.checking,
        	"blue": self.disclaimer,
            	"save": self.save,
            	"cancel": self.cancel,
            	"ok": self.save,
       	})
       	
    def createSetup(self):                                                  
	f=open("/proc/stb/info/model")
	self.boxtype=f.read()
	f.close()
	f=open("/proc/mounts")
	self.mounts=f.read()
	f.close()
	self.boxtype=self.boxtype.replace("\n","").replace("\l","")
       	self.list = []
	self.list.append(getConfigListEntry(_("create nfo"), config.plugins.dflash.nfo))
	self.list.append(getConfigListEntry(_("Flashtool"), config.plugins.dflash.flashtool))
       	self.list.append(getConfigListEntry(_("Backuptool"), config.plugins.dflash.backuptool))
     	self.list.append(getConfigListEntry(_("jffs2 boot compression"), config.plugins.dflash.jffs2bootcompression))
	if config.plugins.dflash.backuptool.value == "mkfs.jffs2": 
	     	self.list.append(getConfigListEntry(_("jffs2 root compression"), config.plugins.dflash.jffs2rootcompression))
	if self.boxtype != "dm7025" and self.boxtype !="dm800":
		if config.plugins.dflash.backuptool.value == "mkfs.jffs2": 
			if self.boxtype == "dm7020hd" or self.boxtype =="dm8000":
				self.list.append(getConfigListEntry(_("jffs2 erase block summary"), config.plugins.dflash.summary))
		else:
		     	self.list.append(getConfigListEntry(_("ubifs root compression"), config.plugins.dflash.ubifsrootcompression))
			if self.boxtype.startswith("dm7020hd") or self.boxtype=="dm500hdv2" or self.boxtype == "dm800sev2":
			      	self.list.append(getConfigListEntry(_("ubifs data backup"), config.plugins.dflash.databackup))
				if config.plugins.dflash.databackup.value: 
				     	self.list.append(getConfigListEntry(_("ubifs data compression"), config.plugins.dflash.ubifsdatacompression))
			if self.boxtype =="dm8000":
				self.list.append(getConfigListEntry(_("Root Volume Size [59-%iMB]") % rambo_maxflash, config.plugins.dflash.volsize))
			elif self.boxtype.startswith("dm7020hd") or self.boxtype == "dm500hdv2" or self.boxtype == "dm800sev2":
				self.list.append(getConfigListEntry(_("Root Volume Size [59-%iMB]") % rambo_maxflash, config.plugins.dflash.volsize))
			else:
			       	self.list.append(getConfigListEntry(_("Root Volume Size [40-%iMB]") % rambo_maxflash, config.plugins.dflash.volsize))
#			if self.boxtype =="dm8000":
#			       	self.list.append(getConfigListEntry(_("ubifs subpages [Flash=")+_("yes")+_(", rambo=")+_("no")+"]", config.plugins.dflash.subpage))
	       		self.list.append(getConfigListEntry(_("ubifs debug level"), config.plugins.dflash.debug))
 	      	self.list.append(getConfigListEntry(_("Console output"), config.plugins.dflash.console))
	if self.boxtype != "dm7025":
        	self.list.append(getConfigListEntry(_("Fading"), config.plugins.dflash.fade))
        self.list.append(getConfigListEntry(_("Swapsize [MB]"), config.plugins.dflash.swapsize))
       	self.list.append(getConfigListEntry(_("loop swap over network"), config.plugins.dflash.loopswap))
       	if self.mounts.find("/usr") is not -1:
		self.list.append(getConfigListEntry(_("include /usr mount in backup"), config.plugins.dflash.usr))
	if (self.boxtype == "dm500hd" or self.boxtype == "dm800se") and os.path.exists("/sbin/squeezeout"):
		self.list.append(getConfigListEntry(_("include squashfs directories in backup"), config.plugins.dflash.squashfs))
       	if os.path.exists("/usr/bin/zip"):
      		self.list.append(getConfigListEntry(_("zip backups"), config.plugins.dflash.zip))
      	else:
      		config.plugins.dflash.zip.value=False
	if self.boxtype == "dm7020hd":
      		self.list.append(getConfigListEntry(_("switch boxversion for backup"), config.plugins.dflash.switchversion))
      	self.list.append(getConfigListEntry(_("show in Extensions Menu"), config.plugins.dflash.extension))
#      	self.list.append(getConfigListEntry(_("use ramfs for flashing"), config.plugins.dflash.ramfs))
#     	self.list.append(getConfigListEntry(_("overwrite only image "), config.plugins.dflash.overwrite))
#     	self.list.append(getConfigListEntry(_("keep temporary files"), config.plugins.dflash.keep))
#      	self.list.append(getConfigListEntry(_("restart enigma2"), config.plugins.dflash.restart))
#      	self.list.append(getConfigListEntry(_("sort alphabetic"), config.plugins.dflash.sort))
      	self.list.append(getConfigListEntry(_("execute tool"), config.plugins.dflash.exectool))

        self["config"].list = self.list                                 
        self["config"].l.setList(self.list)         
       	
    def changedEntry(self):                                                 
       	self.createSetup()       
		
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


