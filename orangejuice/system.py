import json,os,platform,shutil,subprocess,time,threading
import psutil

class Monitor:
    def __init__(self):self.lock=threading.RLock();self.cached={};self.at=0;self.service_cache=[];self.service_at=0
    def snapshot(self):
        with self.lock:
            if time.time()-self.at<3:return self.cached
            mem=psutil.virtual_memory();swap=psutil.swap_memory();disks=[];seen=set()
            for partition in psutil.disk_partitions(all=False):
                if partition.device in seen:continue
                seen.add(partition.device)
                try:
                    d=psutil.disk_usage(partition.mountpoint);disks.append({'mount':partition.mountpoint,'device':partition.device,'total':d.total,'used':d.used,'free':d.free,'percent':d.percent})
                except (OSError,PermissionError):pass
            if not disks:
                d=shutil.disk_usage(os.path.abspath(os.sep));disks=[{'mount':os.path.abspath(os.sep),'total':d.total,'used':d.used,'free':d.free,'percent':round(d.used/d.total*100,1)}]
            net=psutil.net_io_counters();boot=psutil.boot_time()
            self.cached={'cpuPercent':psutil.cpu_percent(interval=0.2),'cores':psutil.cpu_count(),'memory':{'total':mem.total,'used':mem.used,'available':mem.available,'percent':mem.percent},'swap':{'total':swap.total,'used':swap.used,'percent':swap.percent},'disks':disks,'network':{'sent':net.bytes_sent,'received':net.bytes_recv},'uptime':int(time.time()-boot),'platform':platform.system(),'architecture':platform.machine(),'host':platform.node(),'load':list(os.getloadavg()) if hasattr(os,'getloadavg') else [],'timestamp':time.time()};self.at=time.time();return self.cached
    def services(self):
        with self.lock:
            if time.time()-self.service_at<20:return self.service_cache
            docker=[]
            if shutil.which('docker'):
                try:
                    result=subprocess.run(['docker','ps','-a','--format','{{json .}}'],capture_output=True,text=True,timeout=5)
                    for line in result.stdout.splitlines():
                        try:
                            item=json.loads(line);docker.append({'name':item.get('Names'),'image':item.get('Image'),'state':item.get('State'),'status':item.get('Status')})
                        except ValueError:pass
                except subprocess.TimeoutExpired:pass
            processes=[]
            for p in psutil.process_iter(['pid','name','memory_info']):
                try:processes.append({'pid':p.info['pid'],'name':p.info['name'],'memory':p.info['memory_info'].rss})
                except (psutil.Error,AttributeError):pass
            self.service_cache={'containers':docker,'processes':sorted(processes,key=lambda x:x['memory'],reverse=True)[:20],'timestamp':time.time()};self.service_at=time.time();return self.service_cache
