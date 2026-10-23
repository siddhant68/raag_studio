# Attach to the existing idle Sonic Pi instance; do not boot another engine.
require 'open3'
require_relative '/Applications/Sonic Pi.app/Contents/Resources/app/server/ruby/lib/sonicpi/osc/osc'
root=File.dirname(File.realpath(__FILE__))
lines,_=Open3.capture2('/bin/ps','-axo','args=')
line=lines.lines.find { |l| l.include?('/spider-server.rb -u ') }
abort 'No active UDP Sonic Pi server found' unless line
args=line.split('/spider-server.rb ',2).last.split
server_port=args[1].to_i
engine_port=args[4].to_i
token=args[6].to_i
control=SonicPi::OSC::UDPClient.new('127.0.0.1',server_port)
out=File.join(root,'Sonic_Pi_Backing_Native.wav')
abort 'Recording already exists; choose a new project folder' if File.exist?(out)
puts 'Attached to active Sonic Pi. Starting a 54-second backing recording.'
STDOUT.flush
begin
  control.send('/start-recording',token)
  sleep 0.25
  control.send('/run-code',token,File.read(File.join(root,'backing.rb')))
  sleep 54
ensure
  control.send('/stop-recording',token)
end
sleep 2
control.send('/save-recording',token,out)
sleep 1
abort 'No Sonic Pi audio was recorded' unless File.exist?(out) && File.size(out)>10000
puts "Recorded #{File.size(out)} bytes. Existing Sonic Pi engine left running."
