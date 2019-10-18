#!/usr/bin/python
import os, sys, re, syslog, \
       getopt, fcntl, time, \
       ConfigParser

#globals 
rpz_options={}
rpz_options['verbose']=0
rpz_options['verbose_level']=1
rpz_options['rpz_srv']='rpz.example.com'
rpz_options['rpz_zone']='rpz.example.rpz.'
rpz_options['dig_bin']='/usr/bin/dig'
rpz_options['rndc_bin']='/sbin/rndc'
rpz_options['chkconfig_bin']='/sbin/named-checkconf'
rpz_options['chkzone_bin']='/sbin/named-checkzone'
rpz_options['named_dir']='/tmp/rpz-mimic'
rpz_options['named_inc']='rpz_mimic.conf'
rpz_options['zone_dir']='/tmp/rpz-mimic/zones/rpz'
rpz_options['state_file']='/tmp/rpz-mimic.state'
rpz_options['state_file']='/tmp/rpz-mimic.state'
Config=ConfigParser.ConfigParser()
Config.read("/etc/rpz-mimic.conf")
#myself=os.path.basename(sys.argv[0])
#syslog.openlog(myself,logoption=syslog.LOG_PID, facility=syslog.LOG_DAEMON)

#logging utility,
# log if verbose is equal or greater verbose_level
# print to stout too if verbose
def shout(level,message,too=''):
  if level < rpz_options['verbose_level']:
    syslog.syslog(message)
    if rpz_options['verbose'] > 0:
      print (message+' '+too)

#parse config
#take opzion dictonary by ref to keep original not overridden keys
#
def ConfigSectionMap(section,opzioni):
    options=Config.options(section)
    for option in options:
        try:
            #get key
            tmp_opt_val=Config.get(section,option)
            if tmp_opt_val==-1:
              shout(0,'Skipping %s!' % option)
            if option == 'verbose_level' or option == 'verbose':
              opzioni[option]=int(tmp_opt_val)
            else:
               opzioni[option]=tmp_opt_val
        except:
            shout(0,'ConfigSectionMap error parsing %s!' % option)
            opzioni[option]=None
     #return opzioni


#override default wit config
ConfigSectionMap('Global',rpz_options)

#save serial as file for future checks
#
def save_serial(serial,file):
  try:
    serial_fh=open(file+'.tmp','w')
  except EnvironmentError:
    shout(0,'cannot open '+file+'.tmp')
    sys.exit(2)

  #write value into file with newline 
  serial_fh.write("%s\n" % serial)
  serial_fh.close()
  os.rename(file+'.tmp',file)

#load serial from file and return it
#
def load_serial(file):
  if not os.path.exists(file):
    return '0'
  try:
    serial_fh=open(file,'r')
  except EnvironmentError:
    shout(0,'cannot open '+file)
    sys.exit(2)

  #read content and strip newlines
  serial=serial_fh.read().rstrip()
  serial_fh.close()
  return serial

#write a zone file for later pointing it with named_include.conf
#
def zone_write(rpz_path,dstaddr):
  #default parameters
  zone_config={}
  zone_config['master']='ns1.none.rpz.'
  zone_config['hostmaster']='null@example.it'
  zone_config['ttl']='24h'
  zone_config['refresh']='12h'
  zone_config['retry']='15m'
  zone_config['expire']='3w'
  zone_config['minttl']='2h'
  #load config from RPZ_Zone section file
  ConfigSectionMap('RPZ_Zone',zone_config)

  # write a file for each point address
  zone_file=rpz_path+'/bl.'+dstaddr
  try:
    zone_fh=open(zone_file+'.tmp','w')
  except EnvironmentError:
    shout(0,'cannot open '+zone_file+'.tmp')
    sys.exit(2)
  
  #hugly template, maybe better done with other tecniques
  zone_fh.write('$TTL '+zone_config['ttl']+";\n")
  zone_fh.write('@       SOA '+zone_config['master'].rstrip('.')+'. '+zone_config['hostmaster'].replace('@','.').rstrip('.')+". (\n")
  zone_fh.write('        '+time.strftime("%s")+"\n") #undocumented "%s"
  zone_fh.write('        '+zone_config['refresh']+"\n")
  zone_fh.write('        '+zone_config['retry']+"\n")
  zone_fh.write('        '+zone_config['expire']+"\n")
  zone_fh.write('        '+zone_config['minttl']+")\n")
  zone_fh.write(";fake ns list\n")
  zone_fh.write('        NS '+zone_config['master'].rstrip('.')+".\n")
  #zone_fh.write(zone_config['master'].rstrip('.')+'.  IN A 127.0.2.1'+"\n")
  if 'slave' in zone_config:
    zone_fh.write('        NS '+zone_config['slave'].rstrip('.')+".\n")
    #zone_fh.write(zone_config['slave'].rstrip('.')+'. IN A 127.0.2.2'+".\n")
  zone_fh.write(";begin RR definitions\n")
  zone_fh.write("@  IN A "+dstaddr+"\n")
  zone_fh.write("*  IN A "+dstaddr+"\n")
  zone_fh.close()

  chkzone_cmd=rpz_options['chkzone_bin']+' -k fail '+rpz_options['rpz_zone']+' '+zone_file+'.tmp'
  chk_out=' 2>&1 >'+zone_file+'.chkout'

  shout(4,'calling '+chkzone_cmd)
  chk_rc=os.system(chkzone_cmd+chk_out)
  if chk_rc != 0:
    shout(0,'zone check '+chkzone_cmd+' failed')
    sys.exit(2)
  #confirm zone file  
  os.rename(zone_file+'.tmp',zone_file)

def rollback_file_and_die(file,extension):
   
  if os.path.exists(file+extension):
    shout(0,'rolling back '+file+extension)
    os.rename(file,file+'.fail'+extension)
  else:
    shout(0,'critical error rollback file missing '+file+extension)

  shout(0,'saving err to '+file+'.fail'+extension)
  os.rename(file+extension,file)
  sys.exit(2)

#main
#
def main(myself,argv):
  myself=os.path.basename(myself)
  syslog.openlog(myself,logoption=syslog.LOG_PID, facility=syslog.LOG_DAEMON)
  lock_name='/tmp/'+myself+'.lock'
  #avoid multiple concurrent run
  lock_fh=open(lock_name,'a+')
  try:
    fcntl.flock(lock_fh.fileno(),fcntl.LOCK_EX | fcntl.LOCK_NB)
  except IOError:
    shout(0,myself+' aborting other istance running' )
    sys.exit(2)
  #log running
  shout(1,myself+' starting')

  #init serial checks
  old_serial=load_serial(rpz_options['state_file'])
  new_serial='-1'

  #runnig dig axfr of zone against server
  dig_cmd=rpz_options['dig_bin']+' -t axfr '+rpz_options['rpz_zone']+' @'+rpz_options['rpz_srv']
  shout(4,'calling '+dig_cmd)
  dig_out = os.popen(dig_cmd).read()

  #keep state for later zone and named_inc writing this implies all blacklist is kept in memory
  entire_blacklist={}
  landing_ip_list={}

  #utility vars
  space = re.compile('\s+')
  rcnt=0

  # parsing dig output/zone file
  for linea in dig_out.splitlines():
    rcnt+=1
    #clean row and skip comments/useless/dirty
    linea.rstrip().rstrip('\r\n')
    if (re.match('^(#.*|;.*|)$',linea)):
      continue

    #search for serial
    #split SOA content by spaces and keep serial
    #die on error
    campi=re.search('^.*\s+IN\s+SOA\s+(.+)$',linea)
    if campi != None:
      soa_rec=space.split( campi.group(1) )
      if soa_rec == None or len (soa_rec) != 7:
        shout(0,'malformed soa '+riga+"\n")
        sys.exit(2)
      new_serial=soa_rec[2]

      #check if serial is changed from last run
      if old_serial == new_serial:
        shout(1,'serial %s:%s already applied' % (new_serial,rpz_options['rpz_zone']) )
        sys.exit(0)
      else:
        shout(1,'serial %s:%s moved to %s' % (old_serial,rpz_options['rpz_zone'],new_serial) )
    
    #parse IN A rows 
    campi=re.search('^(\S+)\s+\d+\s+IN\s+A\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$',linea)
    if campi == None:
      continue
    #strip rpz zone from record name
    dominio=campi.group(1).replace(rpz_options['rpz_zone'],'')
    landing_ip=campi.group(2)
    entire_blacklist[dominio]=landing_ip
    landing_ip_list[landing_ip]=1

  #catch error parsing and die to avoid blank blacklists
  if new_serial == '-1':
    shout(0,'failed retriving zone %s serial not found %s' % (rpz_options['rpz_zone'],new_serial))
    sys.exit(2)
  
  #prep spool making dir
  if not os.path.exists(rpz_options['named_dir']):
    os.makedirs(rpz_options['named_dir'])
  if not os.path.exists(rpz_options['zone_dir']):
    os.makedirs(rpz_options['zone_dir'])

  # write zone files (landing ip content)
  for indirizzo in landing_ip_list.keys():
    zone_file=rpz_options['zone_dir']+'/bl.'+indirizzo
    shout(2,'writing zone file %s' % zone_file)
    zone_write(rpz_options['zone_dir'],indirizzo)

  #write out named include file 
  named_inc=rpz_options['named_dir']+'/'+rpz_options['named_inc']
  try:
    named_inc_fh=open(named_inc+'.tmp','w')
  except EnvironmentError:
    shout(0,'cannot open '+named_inc+'.tmp')
    sys.exit(2)

  for dominio in entire_blacklist.keys():
    zone_file=rpz_options['zone_dir']+'/bl.'+entire_blacklist[dominio]
    named_inc_fh.write('zone "%s" { type master; file "%s"; };\n' % (dominio,zone_file) )

  #ruotating old files for history and rollback
  named_inc_fh.close()
  named_saved_suff=time.strftime(".%s")

  if os.path.exists(named_inc):
    os.rename(named_inc,named_inc+named_saved_suff)
  os.rename(named_inc+'.tmp',named_inc)

  #abort if named-checkconf fails
  shout(4,'calling '+rpz_options['chkconfig_bin'])
  chk_rc=os.system(rpz_options['chkconfig_bin'])
  if chk_rc != 0:
    shout(0,'conf check '+rpz_options['chkconfig_bin']+' failed')
    rollback_file_and_die(named_inc,named_saved_suff)

  #call rndc reconfig,and rollback+abort if fails
  shout(4,'calling '+rpz_options['rndc_bin']+' reconfig')
  rndc_rc=os.system(rpz_options['rndc_bin']+' reconfig')
  if rndc_rc != 0:
    shout(0,'conf reload '+rpz_options['chkconfig_bin']+' failed')
    rollback_file_and_die(named_inc,named_saved_suff)

  #all is done, save state
  save_serial(new_serial,rpz_options['state_file'])

  #release lock
  fcntl.flock(lock_fh.fileno(),fcntl.LOCK_UN);
  lock_fh.close()
  os.remove(lock_name)


main(sys.argv[0],sys.argv[1:])
