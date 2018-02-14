control 'Linux instance check' do
  title 'SSH access'
  desc 'SSH port should not be open to the world'
  impact 0.9
  require 'rbconfig'
  is_windows = (RbConfig::CONFIG['host_os'] =~ /mswin|mingw|cygwin/)
  if ! is_windows
    describe port(22) do
      it { should be_listening }
      its('addresses') {should_not include '0.0.0.0'}
    end
  end
end
