#!/usr/bin/env python
"""
 +---------------------------------------------------------------------------+
 |   A munin node, using Python                                              |
 |                                                                           |
 |   Copyright (C) 2013, Oliver White                                        |
 +---------------------------------------------------------------------------+
 |                                                                           |
 |  This program is free software: you can redistribute it and/or modify     |
 |  it under the terms of the GNU General Public License as published by     |
 |  the Free Software Foundation, either version 3 of the License, or        |
 |  (at your option) any later version.                                      |
 |                                                                           |
 |  This program is distributed in the hope that it will be useful,          |
 |  but WITHOUT ANY WARRANTY; without even the implied warranty of           |
 |  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the            |
 |  GNU General Public License for more details.                             |
 |                                                                           |
 |  You should have received a copy of the GNU General Public License        |
 |  along with this program.  If not, see <http://www.gnu.org/licenses/>.    |
 +---------------------------------------------------------------------------+
"""
import psutil
import socket
import SocketServer
import os
import sys
import time
import re
import signal

#============================================================================#
#                                                                            #
#                      The data-gathering bit                                #
#                                                                            #
#============================================================================#
#                                                                            #
#  To add a new graph                                                        #
#   *  create an update_xxx function.  It will be automatically called       #
#   *  populate some data: self.d[data_name] = value                         #
#   *  list the data: self.g[graph_name] = [data_names]                      #
#   *  specify the config: self.c[data_name] = ["array","of","lines","."]    #
#                                                                            #
#============================================================================#
class info:
  def __init__(self):
    self.d = {} # Data
    self.g = {} # Graphs
    self.c = {} # Configs
    self.f = {} # Format-string for data (default %d)
    self.name = socket.gethostname()
    self.sent_config = False
    self.version = "0.1.0"
  
  #---------------------------------------------------------------------------
  # CPU usage
  #---------------------------------------------------------------------------
  def update_cpu(self, name, config):
    self.c[name] =[
      "graph_title CPU usage",
      #"graph_args --base 1000 -r --lower-limit 0 --upper-limit 200",
      "graph_vlabel %",
      "graph_category system",
      "graph_period second"]

    self.g[name] = []
    for n in range (psutil.NUM_CPUS):
      dname = "cpu%d" % n
      self.d[dname] = psutil.cpu_percent(interval=0)
      self.g[name].append(dname)
      self.c[name].append("%s.label %s" % (dname,dname))
      self.c[name].append("%s.min 0" % (dname,))
      self.c[name].append("%s.type GAUGE" % (dname,))
      self.c[name].append("%s.draw AREASTACK" % (dname,))
      self.c[name].append("%s.info %s" % (dname,dname))
    self.c[name].append(".")
      
  #---------------------------------------------------------------------------
  # CPU times
  #---------------------------------------------------------------------------
  def update_times(self, name, config):
    ct = psutil.cpu_times()
    self.g[name] = []
    for t in ("system", "irq", "softirq", "user", "iowait", "nice", "idle"):
      fn = getattr(ct, t)
      if(fn):
        self.d[t] = fn
        self.g[name].append(t)
            
    self.c[name] =[
      "graph_title CPU times",
      "graph_order " + " ".join(self.g[name]),
      "graph_category system",
      "graph_period second"]
    
    drawstyle = "AREA"
    for t in self.g[name]:
      self.c[name].append("%s.label %s" % (t,t))
      self.c[name].append("%s.min 0" % (t,))
      self.c[name].append("%s.type COUNTER" % (t,))
      self.c[name].append("%s.draw %s" % (t,drawstyle))
      self.c[name].append("%s.info CPU time spent in %s mode" % (t,t))
      drawstyle = "STACK" # for subsequent ones
    self.c[name].append(".")

  #---------------------------------------------------------------------------
  # Load average
  #---------------------------------------------------------------------------
  def update_load_avg(self, name, config):
    (min1,min5,min15) = os.getloadavg() # values averaged over 1,5,15 minutes
    self.g[name] = ["load_avg_1min", "load_avg_15min"]
    self.d["load_avg_1min"] = min1
    self.d["load_avg_15min"] = min15
    self.f["load_avg_1min"] = "%1.2f"
    self.f["load_avg_15min"] = "%1.2f"
    self.c[name] =[
      "graph_title Load average",
      "graph_category system",
      "load_avg_1min.label load_average",
      "load_avg_1min.min 0",
      "load_avg_1min.type GAUGE",
      "load_avg_1min.draw AREA",
      "load_avg_1min.info Number of processes waiting to run",
      "load_avg_15min.label load_average",
      "load_avg_15min.min 0",
      "load_avg_15min.type GAUGE",
      "load_avg_15min.draw LINE",
      "."]
      
  #---------------------------------------------------------------------------
  # Memory
  #---------------------------------------------------------------------------
  def update_memory(self, name, config):
    
    self.g[name] = ["memory_used","memory_available"]

    if("virtual_memory" in dir(psutil)): # new style function call
      data = psutil.virtual_memory() 
      self.d["memory_used"] = data.used
      self.d["memory_available"] = data.available
    else:
      self.d["memory_used"] = psutil.used_phymem()
      self.d["memory_available"] = psutil.avail_phymem()
        
    self.c[name] =[
      "graph_title Memory",
      "graph_order memory_used memory_available",
      "graph_category system",
      "graph_period second",
      "memory_used.label in use",
      "memory_used.min 0",
      "memory_used.type GAUGE",      
      "memory_used.draw AREA",      
      "memory_available.label available",
      "memory_available.type GAUGE",
      "memory_available.draw STACK",
      "."]

  #---------------------------------------------------------------------------
  # IO counters
  #---------------------------------------------------------------------------
  def update_disk_io(self, name, config):
    self.c[name] =[
      "graph_title Disk I/O",
      "graph_category storage",
      "graph_period second"]
    self.g[name] = []
    disk_data = psutil.disk_io_counters()
    for field in ("read_bytes", "write_bytes"):
      dname = "disk_" + field
      self.g[name].append(dname)
      self.d[dname] = getattr(disk_data, field)
      self.c[name].append("%s.label %s" % (dname, dname))
      self.c[name].append("%s.type COUNTER" % (dname, ))
      self.c[name].append("%s.draw AREA" % (dname, ))
      if(field.startswith("read")):
        self.c[name].append("%s.cdef 0,%s,-" % (dname,dname, ))
    self.c[name].append(".")

  #---------------------------------------------------------------------------
  # Disk uage
  #---------------------------------------------------------------------------
  def update_disk_usage(self, name, config):
    self.c[name] =[
      "graph_title Disk usage",
      "graph_category storage",
      "graph_period second"]
    self.g[name] = []
    disk_usage = psutil.disk_usage('/')
    for field in ("used", "free"):
      dname = "disk_" + field
      self.g[name].append(dname)
      self.d[dname] = getattr(disk_usage, field)
      self.c[name].append("%s.label %s" % (dname, dname))
      self.c[name].append("%s.min 0" % (dname, ))
      self.c[name].append("%s.type COUNTER" % (dname, ))
      self.c[name].append("%s.draw AREASTACK" % (dname, ))
    self.c[name].append(".")

  #---------------------------------------------------------------------------
  # Processes
  #---------------------------------------------------------------------------
  def update_processes(self, name, config):
    self.c[name] =[
      "graph_title Number of processes",
      "graph_args --base 1000 -r --lower-limit 0 --upper-limit 200",
      "graph_category system",
      "graph_period second",
      "processes.label num_processes",
      "processes.type GAUGE",
      "."]
    self.g[name] = ["processes"]
    self.d["processes"] = len(psutil.get_pid_list())

  #---------------------------------------------------------------------------
  # Uptime
  #---------------------------------------------------------------------------
  def update_uptime(self, name, config):
    self.c[name] =[
      "graph_title Uptime",
      "graph_category system",
      "graph_period second",
      "uptime.label uptime",
      "uptime.type GAUGE",
      "."]
    self.g[name] = ["uptime"]
    self.d["uptime"] = time.time() - psutil.BOOT_TIME

  #---------------------------------------------------------------------------
  # Network
  #---------------------------------------------------------------------------
  def update_network(self, name, config):
    self.c[name] =[
      "graph_title Network",
      "graph_category network",
      "graph_period second"]
    self.g[name] = []
    net_data = psutil.network_io_counters(pernic=True)
    for (interface_name, stats) in net_data.items():
      for field in ("bytes_sent", "bytes_recv"):
        dname = "%s_%s" % (field, interface_name)
        self.g[name].append(dname)
        self.d[dname] = getattr(stats, field)
        self.c[name].append("%s.label %s" % (dname, dname))
        self.c[name].append("%s.type COUNTER" % (dname, ))
        self.c[name].append("%s.draw LINE2" % (dname, ))
        if(field.endswith("recv")):
          self.c[name].append("%s.cdef 0,%s,-" % (dname,dname, ))
    self.c[name].append(".")
  
  
  def update(self):
    for function_name in dir(self):
      if(function_name.startswith("update_")):
        name = function_name[7:]
        print " - updating \"%s\"" % name
        function = getattr(self, function_name)
        function(name, True)


  def handle(self, command):
    """ Handle commands (except quit) 
        Return a list of lines to reply with (including the dot at end of lists) """
        
    # list of computers that we're reporting about - just ourselves
    if(command == "nodes"):
      return([self.name])

    # version number (to match format used by munin-node)
    if(command == "version"):
      return(["muinins node on %s version: %s" % (self.name, self.version)])

    # List of graphs (not list of data)
    if(command.startswith("list")):
      return([" ".join(self.g.keys())])

    # Capabilities.
    if(command.startswith("cap")):
      r = "cap multigraph"
      if(not self.sent_config):
        r += " dirtyconfig" # TODO: we want it to download config just once not every time?
      return([r])
   
    # Retrieve all data for a graph
    if(command.startswith("fetch")):
      (fetch, graph_name) = command.split(" ")
      r = []
      for data_name in self.g[graph_name]:
        format_string = "%s.value " + self.f.get(data_name, "%d")
        r.append(format_string % (data_name, self.d.get(data_name, 0)))
      r.append(".")
      return(r)

    if(command.startswith("config")):
      (config, graph_name) = command.split(" ")
      self.sent_config = True
      return(self.c[graph_name])
      

#============================================================================#
#                                                                            #
#                    What to do with logfile data                            #
#                                                                            #
#============================================================================#
def logfile(text):
  print text


#============================================================================#
#                                                                            #
#                           Handle requests                                  #
#                                                                            #
#============================================================================#
class munin_node(SocketServer.StreamRequestHandler):
  def handle(self):
    logfile("connection")
    newline = "\n"
    self.wfile.write("# munin node at " + info.name + newline)
    info.update()
    while(True):
      command = self.rfile.readline().strip()
      if(command == "" or command == "quit"):
       logfile("Closed connection")
       return
      #logfile("RX: "+ command)
      response = info.handle(command)
      for line in response:
        #logfile("  - "+ line)
        self.wfile.write(line + newline)


#============================================================================#
#                                                                            #
# The main program: run a TCP server on port 4949 and serve munin requests   #
#                                                                            #
#============================================================================#
if(__name__ == "__main__"):
  info = info()

  server = SocketServer.TCPServer(("127.0.0.1", 4949), munin_node)
  server.allow_reuse_address = True

  def shutdown(signal, frame):
    logfile("Shutting down")
    server.server_close() 
    logfile("Stopped server") 
    sys.exit(0) 
    
  signal.signal(signal.SIGINT, shutdown)
  server.serve_forever()


