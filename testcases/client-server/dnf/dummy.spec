Summary:        This is a dummy rpm-test 
Name:           dummy-rpm
Version:        1.0
#Release:        %(echo `date '+%%Y%%m%%d.%%H%%M%%S'`)
Release:	1
Epoch:          0
Group:          Development/Interpreters
License:        GPL+
BuildArch:      noarch

BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root

%prep

%build

%install

#mkdir -p %buildroot
touch dummy-file

%clean

%files
%doc dummy-file

%description

This rpm contains a dummy file /usr/doc/%name-%version/file.
It means the whole rpm is also dummy.

