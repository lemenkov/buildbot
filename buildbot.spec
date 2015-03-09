%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

%{!?_pkgdocdir: %global _pkgdocdir %{_docdir}/%{name}-%{version}}

%global do_tests 1

# The master and slave packages have (in theory) an independent versioning
%global slaveversion %{version}

Name:           buildbot
Version:        0.8.10
Release:        5%{?dist}

Summary:        Build/test automation system
Group:          Development/Tools
License:        GPLv2
URL:            http://buildbot.net
Source0:	https://github.com/buildbot/buildbot/archive/v%{version}/%{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python-devel
BuildRequires:  python-sphinx

# Needed for tests
%if %do_tests
BuildRequires:  python-sqlalchemy
BuildRequires:  python-migrate
BuildRequires:  python-mock
BuildRequires:  python-dateutil
BuildRequires:  python-twisted-core
BuildRequires:  python-twisted-web
BuildRequires:  python-twisted-mail
BuildRequires:  python-twisted-words

# Lately, bzr tests fail. I contacted upstream about the issue
# in the meanwhile they are disabled
BuildRequires:  bzr 
BuildRequires:  cvs
BuildRequires:  git
BuildRequires:  mercurial
BuildRequires:  subversion

# darcs available on these archs only
%ifarch %{ix86} x86_64 ppc alpha
BuildRequires:  darcs
%endif
%endif

# Turns former package into a metapackage for installing everything
Requires:       %{name}-master = %{version}
Requires:       %{name}-doc = %{version}
Requires:       %{name}-slave = %{slaveversion}


%description
The BuildBot is a system to automate the compile/test cycle required by
most software projects to validate code changes. By automatically
rebuilding and testing the tree each time something has changed, build
problems are pinpointed quickly, before other developers are
inconvenienced by the failure.


%package master
Summary:        Build/test automation system
Group:          Development/Tools
License:        GPLv2

Requires:       python-twisted-core
Requires:       python-twisted-web
Requires:       python-twisted-mail
Requires:       python-twisted-words
Requires:       python-twisted-conch
Requires:       python-boto
Requires:       python-jinja2
Requires:       python-sqlalchemy
Requires:       python-migrate
Requires:       python-dateutil

Requires(post): info
Requires(preun): info


%description master
The BuildBot is a system to automate the compile/test cycle required by
most software projects to validate code changes. By automatically
rebuilding and testing the tree each time something has changed, build
problems are pinpointed quickly, before other developers are
inconvenienced by the failure.

This package contains only the buildmaster implementation.
The buildbot-slave package contains the buildslave.


%package slave
Version:        %{slaveversion}   
Summary:        Build/test automation system
Group:          Development/Tools
License:        GPLv2

Requires:       python-twisted-core


%description slave
This package contains only the buildslave implementation.
The buildbot-master package contains the buildmaster.


%package doc
Summary:    Buildbot documentation
Group:      Documentation

%description doc
Buildbot documentation


%prep
%setup -q


%build
cd master
%{__python} setup.py build

#TODO create API documentation
pushd docs
make docs.tgz
popd

pushd ../slave
%{__python} setup.py build
popd


%if %do_tests
%check
cd master
trial buildbot.test
%endif


%install
cd master

%{__python} setup.py install -O1 --skip-build --root %{buildroot}

mkdir -p %{buildroot}%{_datadir}/%{name}/ \
         %{buildroot}%{_mandir}/man1/ \
         %{buildroot}%{_pkgdocdir}

cp -R contrib %{buildroot}/%{_datadir}/%{name}/

# install the man page
cp docs/buildbot.1 %{buildroot}%{_mandir}/man1/buildbot.1

# install HTML documentation
tar xf docs/docs.tgz --strip-components=1 -C %{buildroot}%{_pkgdocdir}

# clean up Windows contribs.
sed -i 's/\r//' %{buildroot}/%{_datadir}/%{name}/contrib/windows/*
chmod -x %{buildroot}/%{_datadir}/%{name}/contrib/windows/*

# install slave files
cd ../slave
%{__python} setup.py install -O1 --skip-build --root %{buildroot}

# fix rpmlint E: script-without-shebang
sed -i '1i#!/usr/bin/python' %{buildroot}%{_datadir}/%{name}/contrib/bk_buildbot.py

cd ../master
# Create working directory for buildbot
install -d -m 0755 %{buildroot}%{_localstatedir}/lib/%{name}
# Install default buildbot tac-file
install -p -m 0644 buildbot.tac.sample %{buildroot}%{_localstatedir}/lib/%{name}/%{name}.tac
# Install default buildbot config - master.cfg.sample
install -p -m 0600 ./buildbot/scripts/sample.cfg %{buildroot}%{_localstatedir}/lib/%{name}/master.cfg
# Install default buildbot web-resources
install -d -m 0755 %{buildroot}%{_localstatedir}/lib/%{name}/public_html
for i in bg_gradient.jpg default.css favicon.ico robots.txt
do
	install -p -m 0644 ./buildbot/status/web/files/${i} %{buildroot}%{_localstatedir}/lib/%{name}/public_html/${i}
done

# Make room for buildbot templates
install -d -m 0755 %{buildroot}%{_localstatedir}/lib/%{name}/templates
install -p -m 0644 ./buildbot/status/web/files/templates_readme.txt %{buildroot}%{_localstatedir}/lib/%{name}/templates/README.txt

# Create sample buildbot SQLite DB
/bin/sqlite3 %{buildroot}%{_localstatedir}/lib/%{name}/state.sqlite < buildbot.sqlite.sample

# Install buildbot systemd service file
install -D -p -m 0644 contrib/systemd/buildbot.service %{buildroot}%{_unitdir}/buildbot.service

cd ../slave
# Create working directory for buildslave
install -d -m 0755 %{buildroot}%{_localstatedir}/lib/buildslave

# Install default buildslave tac-file
install -p -m 0644 buildslave.tac.sample %{buildroot}%{_localstatedir}/lib/buildslave/%{name}.tac

# Install buildslave resources
install -d -m 0755 %{buildroot}%{_localstatedir}/lib/buildslave/info
echo "Your Name Here <admin@youraddress.invalid>" > %{buildroot}%{_localstatedir}/lib/buildslave/info/admin
echo "Please put a description of this build host here" > %{buildroot}%{_localstatedir}/lib/buildslave/info/host

# Install buildslave systemd service file
install -D -p -m 0644 contrib/systemd/buildslave.service %{buildroot}%{_unitdir}/buildslave.service

%pre master
getent group %{name} >/dev/null || groupadd -r %{name}
getent passwd %{name} >/dev/null || useradd -r -g %{name} -d %{_localstatedir}/lib/%{name} \
	-s /sbin/nologin -c "Buildbot master user" %{name}

%pre slave
getent group buildslave >/dev/null || groupadd -r buildslave
getent passwd buildslave >/dev/null || useradd -r -g buildslave -d %{_localstatedir}/lib/buildslave \
	-s /sbin/nologin -c "Buildbot slave user" buildslave

%post master
%systemd_post %{name}.service

%preun master
%systemd_preun %{name}.service

%postun master
%systemd_postun %{name}.service

%post slave
%systemd_post buildslave.service

%preun slave
%systemd_preun buildslave.service

%postun slave
%systemd_postun buildslave.service

%files

%files master
%doc master/COPYING master/CREDITS master/README master/UPGRADING
%doc %{_mandir}/man1/buildbot.1.gz
%{_bindir}/buildbot
%{python_sitelib}/buildbot
%{python_sitelib}/buildbot-*egg-info
%{_datadir}/%{name}
%{_unitdir}/buildbot.service

%dir %attr(0755, %{name}, %{name}) %{_localstatedir}/lib/%{name}
%dir %attr(0755, %{name}, %{name}) %{_localstatedir}/lib/%{name}/public_html
%dir %attr(0755, %{name}, %{name}) %{_localstatedir}/lib/%{name}/templates

%config(noreplace) %attr(0644, %{name}, %{name}) %{_localstatedir}/lib/%{name}/buildbot.tac
%config(noreplace) %attr(0600, %{name}, %{name}) %{_localstatedir}/lib/%{name}/master.cfg
%config(noreplace) %attr(0644, %{name}, %{name}) %{_localstatedir}/lib/%{name}/public_html/bg_gradient.jpg
%config(noreplace) %attr(0644, %{name}, %{name}) %{_localstatedir}/lib/%{name}/public_html/default.css
%config(noreplace) %attr(0644, %{name}, %{name}) %{_localstatedir}/lib/%{name}/public_html/favicon.ico
%config(noreplace) %attr(0644, %{name}, %{name}) %{_localstatedir}/lib/%{name}/public_html/robots.txt
%config(noreplace) %attr(0644, %{name}, %{name}) %{_localstatedir}/lib/%{name}/state.sqlite
%config(noreplace) %attr(0644, %{name}, %{name}) %{_localstatedir}/lib/%{name}/templates/README.txt

%files slave
%doc slave/COPYING slave/README slave/UPGRADING
%{_bindir}/buildslave
%{python_sitelib}/buildslave
%{python_sitelib}/buildbot_slave-*egg-info
%{_unitdir}/buildslave.service

%dir %attr(0755, buildslave, buildslave) %{_localstatedir}/lib/buildslave
%dir %attr(0755, buildslave, buildslave) %{_localstatedir}/lib/buildslave/info

%config(noreplace) %attr(0600, buildslave, buildslave) %{_localstatedir}/lib/buildslave/buildbot.tac
%config(noreplace) %attr(0644, buildslave, buildslave) %{_localstatedir}/lib/buildslave/info/admin
%config(noreplace) %attr(0644, buildslave, buildslave) %{_localstatedir}/lib/buildslave/info/host

%files doc
%{_pkgdocdir}


%changelog
* Fri Feb 27 2015 Peter Lemenkov <lemenkov@gmail.com> - 0.8.10-5
- Fixed systemd service
- Added support for git tags

* Thu Feb 19 2015 Peter Lemenkov <lemenkov@gmail.com> - 0.8.10-4
- Fixed systemd service files

* Thu Feb 19 2015 Peter Lemenkov <lemenkov@gmail.com> - 0.8.10-3
- Updated systemd service files

* Wed Feb 18 2015 Peter Lemenkov <lemenkov@gmail.com> - 0.8.10-2
- Install base files for master and slave
- Install systemd files for master and slave

* Fri Dec 19 2014 Gianluca Sforna <giallu@gmail.com> - 0.8.10-1
- new upstream release
- remove upstreamed patch

* Mon Sep 29 2014 Gianluca Sforna <giallu@gmail.com> - 0.8.9-1
- new upstream release
- use packages from PyPI

* Tue Jun 24 2014 Yaakov Selkowitz <yselkowi@redhat.com> - 0.8.8-3
- Fix FTBFS due to changes in sphinx and twisted (#1106019)
- Cleanup spec

* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.8.8-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Fri Aug 23 2013 Gianluca Sforna <giallu@gmail.com> - 0.8.8-1
- new upstream release

* Mon Aug 05 2013 Gianluca Sforna <giallu@gmail.com> - 0.8.7p1-2
- Install docs to %%{_pkgdocdir} where available.

* Sun Jul 28 2013 Gianluca Sforna <giallu@gmail.com> - 0.8.7p1-1
- New upstream release
- Require python-dateutil

* Wed Feb 13 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.8.6p1-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Wed Jul 18 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.8.6p1-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Wed Jul 18 2012 Gianluca Sforna <giallu@gmail.com> - 0.8.6p1-2
- Add missing require for slave subpackage

* Thu Apr 05 2012 Gianluca Sforna <giallu@gmail.com> - 0.8.6p1-1
- New upstream release

* Mon Mar 12 2012 Gianluca Sforna <giallu@gmail.com> - 0.8.6-2
- New upstream release
- Enable tests again
- Don't test deprecated tla
- Correctly populate -slave subpackage (#736875)
- Fix fetching from git > 1.7.7 (#801209)

* Thu Jan 12 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.8.5p1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Fri Dec 02 2011 Dan Radez <dan@radez.net> - 0.8.5p1-1
- New Upstream Release
- updated make for the docs
- removed the buildbot.info refs added the man page

* Wed Jun 22 2011 Gianluca Sforna <giallu@gmail.com> - 0.8.4p1-2
- Upgrade to 0.8.x
- Add -master and -slave subpackages
- Split html docs in own package

* Mon May 30 2011 Gianluca Sforna <giallu@gmail.com> - 0.7.12-6
- Properly install texinfo files #694199
- Disable tests for now, need to investigate some failures

* Tue Feb 08 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.7.12-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Sat Jul 31 2010 Thomas Spura <tomspur@fedoraproject.org> - 0.7.12-4
- Rebuild for https://fedoraproject.org/wiki/Features/Python_2.7/MassRebuild

* Thu Jul 22 2010 Gianluca Sforna <giallu gmail com> - 0.7.12-3
- Remove BR:bazaar (fixes FTBS)

* Wed Jul 21 2010 David Malcolm <dmalcolm@redhat.com> - 0.7.12-2
- Rebuilt for https://fedoraproject.org/wiki/Features/Python_2.7/MassRebuild

* Sun Feb  7 2010 Gianluca Sforna <giallu gmail com>
- Require python-boto for EC2 support
- Require python-twisted-conch for manhole support
- Silence rpmlint

* Fri Jan 22 2010 Gianluca Sforna <giallu gmail com> - 0.7.12-1
- New upstream release

* Mon Aug 17 2009 Steve 'Ashcrow' Milner <stevem@gnulinux.net> - 0.7.11p3-1
- Update for another XSS vuln from upstream

* Thu Aug 13 2009 Steve 'Ashcrow' Milner <stevem@gnulinux.net> - 0.7.11p2-1
- Update for XSS vuln from upstream

* Fri Jul 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.7.11p1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Fri Jul 17 2009 Gianluca Sforna <giallu gmail com> - 0.7.11p1-1
- New upstream release
- Change Source0 URI
- Make tests optional

* Tue Mar  3 2009 Gianluca Sforna <giallu gmail com> - 0.7.10p1-2
- New upstream release
- darcs only avaliable on ix86 platforms 

* Thu Feb 26 2009 Gianluca Sforna <giallu gmail com> - 0.7.10-1
- New upstream release
- Drop upstreamed patch
- Add %%check section and needed BR

* Mon Feb 23 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.7.7-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Sat Nov 29 2008 Ignacio Vazquez-Abrams <ivazqueznet+rpm@gmail.com> - 0.7.7-3
- Rebuild for Python 2.6

* Thu Apr  3 2008 Gianluca Sforna <giallu gmail com> - 0.7.7-2
- Fix upgrade path

* Mon Mar 31 2008 Gianluca Sforna <giallu gmail com> - 0.7.7-1
- new upstream release

* Thu Jan  3 2008 Gianluca Sforna <giallu gmail com> - 0.7.6-2
- pick up new .egg file 

* Mon Oct 15 2007 Gianluca Sforna <giallu gmail com> - 0.7.6-1
- new upstream release
- refreshed Patch0
- requires clean up
- License tag update (GPLv2)

* Sat Mar 17 2007 Gianluca Sforna <giallu gmail com>
- Silence rpmlint

* Thu Mar 01 2007 Gianluca Sforna <giallu gmail com> - 0.7.5-1
- new upstream release
- minor spec tweaks
- Removed (unmantained and orphaned) python-cvstoys Require

* Sat Sep 09 2006 Michael J. Knox <michael[AT]knox.net.nz> - 0.7.4-2
- cleanup %%files

* Fri Sep 08 2006 Michael J. Knox <michael[AT]knox.net.nz> - 0.7.4-1
- Upstream update
- don't ghost pyo files

* Fri Jul 28 2006 Michael J. Knox <michael[AT]knox.net.nz> - 0.7.3-3
- move contribs to %%{_datadir}/%%{name}

* Fri Jul 07 2006 Michael J. Knox <michael[AT]knox.net.nz> - 0.7.3-2
- fixes for review
- added patch to remove #! where its not needed (shutup rpmlint)

* Fri Jun 02 2006 Michael J. Knox <michael[AT]knox.net.nz> - 0.7.3-1
- Inital build for FE
