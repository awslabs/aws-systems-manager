require 'rbconfig'
is_windows = (RbConfig::CONFIG['host_os'] =~ /mswin|mingw|cygwin/)
if is_windows
  describe port(3389) do
    it { should be_listening }
    its('addresses') {should_not include '0.0.0.0'}
  end
end
