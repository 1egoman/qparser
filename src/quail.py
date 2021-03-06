#!/usr/bin/env python
import sys, os, time, atexit, shutil
from signal import SIGTERM

# test for location (only on unix)
if "usr/bin" in os.path.abspath( os.path.dirname(__file__) ):
  os.chdir("/opt/quail")
  PATH = "/opt/quail/src"
else:
  PATH = os.path.join( os.path.abspath( os.path.dirname(__file__) ), "src")

"""
A generic daemon class.
Modified for use with Quail
"""
class QuailDaemon:

  def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
    self.stdin = stdin
    self.stdout = stdout
    self.stderr = stderr
    self.pidfile = pidfile

  def daemonize(self):
    """
    do the UNIX double-fork magic, see Stevens' "Advanced
    Programming in the UNIX Environment" for details (ISBN 0201563177)
    http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
    """
    try:
      pid = os.fork()
      if pid > 0:
        # exit first parent
        sys.exit(0)
    except OSError, e:
      sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
      sys.exit(1)

    # decouple from parent environment
    os.chdir("/")
    os.setsid()
    os.umask(0)

    # do second fork
    try:
      pid = os.fork()
      if pid > 0:
        # exit from second parent
        sys.exit(0)
    except OSError, e:
      sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
      sys.exit(1)

    # redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    si = file(self.stdin, 'r')
    so = file(self.stdout, 'a+')
    se = file(self.stderr, 'a+', 0)
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

    # write pidfile
    atexit.register(self.delpid)
    pid = str(os.getpid())
    file(self.pidfile,'w+').write("%s\n" % pid)

  def delpid(self):
    os.remove(self.pidfile)

  def start(self):
    """
    Start the daemon
    """
    # Check for a pidfile to see if the daemon already runs
    try:
      pf = file(self.pidfile,'r')
      pid = int(pf.read().strip())
      pf.close()
    except IOError:
      pid = None

    if pid:
      message = "pidfile %s already exist. Daemon already running?\n"
      sys.stderr.write(message % self.pidfile)
      sys.exit(1)

    # Start the daemon
    sys.stdout.write("started!\n")
    self.daemonize()
    self.run()

  def stop(self):
    """
    Stop the daemon
    """
    # Get the pid from the pidfile
    try:
      pf = file(self.pidfile,'r')
      pid = int(pf.read().strip())
      pf.close()
    except IOError:
      pid = None

    if not pid:
      message = "pidfile %s does not exist. Daemon not running?\n"
      sys.stderr.write(message % self.pidfile)
      return # not an error in a restart

    # Try killing the daemon process
    try:
      while 1:
        os.kill(pid, SIGTERM)
        time.sleep(0.1)
    except OSError, err:
      err = str(err)
      if err.find("No such process") > 0:
        if os.path.exists(self.pidfile):
          os.remove(self.pidfile)
      else:
        print str(err)
        sys.exit(1)

    sys.stdout.write("stopped!\n")

  def restart(self):
    """
    Restart the daemon
    """
    self.stop()
    self.start()

  def run(self):
    # load src/main.py
    while 1:
      import main
      main.App()


if __name__ == "__main__":
  daemon = QuailDaemon('/tmp/quail-daemon.pid')

  # test for commands
  if len(sys.argv):

    # start daemon
    if 'start' == sys.argv[1]:
      print "pid:", os.getpid()
      daemon.start()

    # stop daemon
    elif 'stop' == sys.argv[1]:
      daemon.stop()

    # restart daemon
    elif 'restart' == sys.argv[1]:
      daemon.restart()

    # start for debugging, with full stdin / stdout / stderr
    elif 'go' == sys.argv[1]:
      # start quail manually
      import main
      main.App()

    # install a plugin
    # quail install 1egoman/qlist
    elif 'install' == sys.argv[1] and len(sys.argv) == 3:
      os.chdir("plugins")
      if sys.argv[2] == "template":
        name = raw_input("Name of template plugin: ")

        if os.system("git clone http://github.com/1egoman/qplugin %s" % name) == 0:
          print "Created template called '%s'." % name
          origin = raw_input("Github plugin origin (blank for none) : ")
          if origin and os.system("git remote set-url origin %s") == 0:
            print "Done! Good luck on your new plugin!"
          elif origin == "":
            print "Done! Good luck on your new plugin!"
          else:
            print "Error!"
        else:
          print "Error!"

      else:
        if os.system("git clone http://github.com/%s" % sys.argv[2]) == 0:
          print "Installed '%s'! Reload or restart any server instances to take effect." % sys.argv[2]
        else:
          print "Error!"

    # remove a plugin
    # quail remove 1egoman/qlist OR quail remove qlist
    elif ('remove' == sys.argv[1] or 'rm' == sys.argv[1]) and len(sys.argv) == 3:
      os.chdir("plugins")
      try:
        shutil.rmtree(sys.argv[2].split("/")[-1])
        print "Removed '%s'! Reload or restart any server instances to take effect." % sys.argv[2]
      except OSError:
        print "No such plugin '%s'!" % sys.argv[2]

    # install quail on a system
    elif 'init' == sys.argv[1] and "posix" in os.name:
      QUAIL_PATH = "/opt/quail"
      quail_old_path = os.getcwd()
      print "Installing in %s" % QUAIL_PATH
      os.system("sudo cp -R %s %s" % (quail_old_path, QUAIL_PATH))
      os.system("sudo cp quail.py /usr/bin/quail")
      os.system("sudo chmod -R 775 /opt/quail")
      os.system("sudo chown -R `whoami`:`whoami` /opt/quail")
      print "done!"

    # remove quail form system
    elif 'deinit' == sys.argv[1] and "posix" in os.name:
      QUAIL_PATH = "/opt/quail"
      quail_old_path = os.getcwd()
      print "Removing from %s" % QUAIL_PATH
      os.system("sudo rm -R %s" % QUAIL_PATH)
      os.system("sudo rm /usr/bin/quail")
      print "done!"

    else:
      print "Unknown Command"
      sys.exit(0)
  else:


    print "usage: %s start|stop|restart" % sys.argv[0]
    sys.exit(2)
