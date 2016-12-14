%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

# Required platform version
%global platform_version 2.8


Name: pulp-ostree
Version: 1.2.0
Release: 1%{?dist}
Summary: Support for OSTree content in the Pulp platform
Group: Development/Languages
License: GPLv2
URL: http://pulpproject.org
Source0: https://fedorahosted.org/releases/p/u/%{name}/%{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: noarch
BuildRequires: python2-devel
BuildRequires: python-setuptools
BuildRequires: rpm-python

%description
Provides a collection of platform plugins and admin client extensions to
provide OSTree support.

%prep
%setup -q

%build
pushd common
%{__python} setup.py build
popd

pushd extensions_admin
%{__python} setup.py build
popd

pushd plugins
%{__python} setup.py build
popd

%install
rm -rf %{buildroot}

mkdir -p %{buildroot}/%{_sysconfdir}/pulp/
mkdir -p %{buildroot}/%{_var}/lib/pulp/published/ostree/
mkdir -p %{buildroot}/%{_bindir}

pushd common
%{__python} setup.py install --skip-build --root %{buildroot}
popd

pushd extensions_admin
%{__python} setup.py install --skip-build --root %{buildroot}
popd

pushd plugins
%{__python} setup.py install --skip-build --root %{buildroot}
popd

cp -R plugins/etc %{buildroot}

%clean
rm -rf %{buildroot}


# ---- Common ----------------------------------------------------------------

%package -n python-pulp-ostree-common
Summary: Pulp OSTree support common library
Group: Development/Languages
Requires: python-pulp-common >= %{platform_version}
Requires: python-setuptools

%description -n python-pulp-ostree-common
Common libraries for OSTree support.

%files -n python-pulp-ostree-common
%defattr(-,root,root,-)
%dir %{python_sitelib}/pulp_ostree
%dir %{python_sitelib}/pulp_ostree/extensions
%{python_sitelib}/pulp_ostree/__init__.py*
%{python_sitelib}/pulp_ostree/common/
%{python_sitelib}/pulp_ostree/extensions/__init__.py*
%{python_sitelib}/pulp_ostree_common*.egg-info

%doc COPYRIGHT LICENSE AUTHORS


# ---- Plugins ---------------------------------------------------------------

%package plugins
Summary: Pulp OSTree plugins
Group: Development/Languages
Requires: python-pulp-common >= %{platform_version}
Requires: python-pulp-ostree-common = %{version} 
Requires: pulp-server >= %{platform_version}
Requires: python-setuptools
Requires: ostree >= 2015.8
Requires: python-gnupg
Requires: gnupg
Requires: pygobject3

%description plugins
Provides a collection of platform plugins that extend the Pulp platform
to provide OSTree specific support.

%files plugins
%defattr(-,root,root,-)
%{python_sitelib}/pulp_ostree/plugins/
%config(noreplace) %{_sysconfdir}/httpd/conf.d/pulp_ostree.conf
%config(noreplace) %{_sysconfdir}/pulp/server/plugins.conf.d/ostree_*.json
%{python_sitelib}/pulp_ostree_plugins*.egg-info
%defattr(-,apache,apache,-)
%{_var}/lib/pulp/published/ostree/

%doc COPYRIGHT LICENSE AUTHORS


# ---- Admin Extensions ------------------------------------------------------

%package admin-extensions
Summary: The Pulp OSTree admin client extensions
Group: Development/Languages
Requires: python-pulp-common >= %{platform_version}
Requires: python-pulp-ostree-common = %{version}
Requires: pulp-admin-client >= %{platform_version}
Requires: python-setuptools

%description admin-extensions
pulp-admin extensions for OSTree support.

%files admin-extensions
%defattr(-,root,root,-)
%{python_sitelib}/pulp_ostree/extensions/admin/
%{python_sitelib}/pulp_ostree_extensions_admin*.egg-info

%doc COPYRIGHT LICENSE AUTHORS


%changelog
* Wed Dec 14 2016 Patrick Creech <pcreech@redhat.com> 1.2.0-1
- Bumping version to 1.2.0-1 (pcreech@redhat.com)

* Fri Dec 09 2016 Patrick Creech <pcreech@redhat.com> 1.2.0-0.4.rc
- Bumping version to 1.2.0-0.4.rc (pcreech@redhat.com)

* Wed Nov 23 2016 Sean Myers <sean.myers@redhat.com> 1.2.0-0.3.beta
- Bumping version to 1.2.0-0.3.beta (sean.myers@redhat.com)

* Thu Nov 03 2016 Sean Myers <sean.myers@redhat.com> 1.2.0-0.2.beta
- Bumping version to 1.2.0-0.2.beta (sean.myers@redhat.com)
- 1.2.0 release notes. (jortel@redhat.com)

* Tue Oct 25 2016 Sean Myers <sean.myers@redhat.com> 1.2.0-0.1.beta
- Bumping version to 1.2.0-0.1.beta (sean.myers@redhat.com)
- Build latest plugin upstream version for f24 (sean.myers@redhat.com)
- Support tree traversal depth. closes #2205 (jortel@redhat.com)
- Fix proxy URL construction in remote configuration. closes #2213
  (jortel@redhat.com)
- Removing fc22 from the list of supported platforms. (ipanova@redhat.com)
- Add basic mention-bot config (jeremy@jcline.org)
- pin to flake8-2.6.2 for py2.6 support (asmacdo@gmail.com)
- Bumping version to 1.1.4-0.1.alpha (sean.myers@redhat.com)
- Bumping version to 1.1.3-0.1.alpha (sean.myers@redhat.com)
- Automatic commit of package [pulp-ostree] release [1.1.3-0.1.beta].
  (sean.myers@redhat.com)
- Bumping version to 1.1.3-0.1.beta (sean.myers@redhat.com)
- Automatic commit of package [pulp-ostree] release [1.1.2-1].
  (sean.myers@redhat.com)
- Bumping version to 1.1.2-1 (sean.myers@redhat.com)
- Remove intersphinx and enable Strict mode (bbouters@redhat.com)
- Bumping version to 1.1.3-0.1.alpha (sean.myers@redhat.com)
- Automatic commit of package [pulp-ostree] release [1.1.2-0.1.beta].
  (sean.myers@redhat.com)
- Bumping version to 1.1.2-0.1.beta (sean.myers@redhat.com)
- Add gnupg as dependency (ipanova@redhat.com)
- Reverting strict mode so that Koji can build RPMs again (bbouters@redhat.com)
- Enables strict mode for sphinx docs builds (bbouters@redhat.com)
- Bumping version to 1.1.1-1 (sean.myers@redhat.com)
- Automatic commit of package [pulp-ostree] release [1.1.1-1].
  (sean.myers@redhat.com)
- Bumping version to 1.1.1-1 (sean.myers@redhat.com)
- Automatic commit of package [pulp-ostree] release [1.1.1-0.4.rc]. (pulp-
  infra@redhat.com)
- Bumping version to 1.1.1-0.4.rc (pulp-infra@redhat.com)
- Configures Sphinx docs config to not look for static media
  (bbouters@redhat.com)
- Automatic commit of package [pulp-ostree] release [1.1.1-0.3.rc].
  (sean.myers@redhat.com)
- Bumping version to 1.1.1-0.3.rc (sean.myers@redhat.com)
- adding release note for 1.1.1 (mhrivnak@redhat.com)
- Automatic commit of package [pulp-ostree] release [1.1.1-0.2.beta].
  (sean.myers@redhat.com)
- Bumping version to 1.1.1-0.2.beta (sean.myers@redhat.com)
- Automatic commit of package [pulp-ostree] release [1.1.1-0.1.beta].
  (sean.myers@redhat.com)
- Bumping version to 1.2.0-0.1.beta (dkliban@redhat.com)
- Ensure unique relative path at validation time (asmacdo@gmail.com)
- Automatic commit of package [pulp-ostree] release [1.1.0-1].
  (dkliban@redhat.com)
- Bumping version to 1.1.0-1 (dkliban@redhat.com)
- Automatic commit of package [pulp-ostree] release [1.1.0-0.9.rc].
  (dkliban@redhat.com)
- Bumping version to 1.1.0-0.9.rc (dkliban@redhat.com)
- Bumping version to 1.1.1-0.1.beta (dkliban@redhat.com)
- Automatic commit of package [pulp-ostree] release [1.1.0-0.8.beta].
  (dkliban@redhat.com)
- Bumping version to 1.1.0-0.8.beta (dkliban@redhat.com)

* Thu Mar 03 2016 Dennis Kliban <dkliban@redhat.com> 1.1.0-0.7.beta
- Bumping version to 1.1.0-0.7.beta (dkliban@redhat.com)

* Wed Mar 02 2016 Dennis Kliban <dkliban@redhat.com> 1.1.0-0.6.beta
- Better handling of GLib.Error raised when fetching the summary. closes #1722
  (jortel@redhat.com)
- Merge pull request #63 from jortel/issue-1720 (jortel@redhat.com)
- Better handling of sync without feed URL specified. closes #1720
  (jortel@redhat.com)
- Merge pull request #62 from seandst/413 (sean.myers@redhat.com)
- Bumping version to 1.1.0-0.6.beta (dkliban@redhat.com)
- Block attempts to load server.conf when running tests (sean.myers@redhat.com)

* Fri Feb 19 2016 Dennis Kliban <dkliban@redhat.com> 1.1.0-0.5.beta
- This uniqueness contstraint is now enforced by the platform for all content
  units. (dkliban@redhat.com)
- Do not install plugin tests. (rbarlow@redhat.com)
- Do not install tests (pcreech@redhat.com)
- Bumping version to 1.1.0-0.5.beta (dkliban@redhat.com)

* Thu Jan 28 2016 Dennis Kliban <dkliban@redhat.com> 1.1.0-0.4.beta
- Merge branch '2327' (rbarlow@redhat.com)
- Bumping version to 1.1.0-0.4.beta (dkliban@redhat.com)
- Store WSGI scripts in /usr/share/pulp/wsgi instead of /srv.
  (rbarlow@redhat.com)

* Tue Jan 19 2016 Dennis Kliban <dkliban@redhat.com> 1.1.0-0.3.beta
- Bumping version to 1.1.0-0.3.beta (dkliban@redhat.com)

* Wed Jan 13 2016 Dennis Kliban <dkliban@redhat.com> 1.1.0-0.2.beta
- Bumping version to 1.1.0-0.2.beta (dkliban@redhat.com)

* Mon Jan 11 2016 Dennis Kliban <dkliban@redhat.com> 1.1.0-0.1.beta
- Bumping version to 1.1.0-0.1.beta (dkliban@redhat.com)
- 1.1 release notes and docs updates. (jortel@redhat.com)
- Merge pull request #55 from mhrivnak/fixes-for-platform
  (mhrivnak@hrivnak.org)
- adding el6 since there are now el6 packages for ostree (mhrivnak@redhat.com)
- various fixes, mostly due to changes in platform (mhrivnak@redhat.com)
- Convert shebang to python2 (ipanova@redhat.com)
- Removed types/ directory references. (jortel@redhat.com)
- Merge branch '1.0-dev' (dkliban@redhat.com)
- Add fc23 to dist_list.txt config and removes fc21. (dkliban@redhat.com)
- Bumping version to 1.0.1-0.1.beta (dkliban@redhat.com)
- Updates plugin to match platform changes on ContentUnit (ipanova@redhat.com)
- Removes a spec file entry for ostree.json which was removed
  (bbouters@redhat.com)
- Automatic commit of package [pulp-ostree] release [1.0.0-0.7.rc].
  (dkliban@redhat.com)
- Bumping version to 1.0.0-0.7.rc (dkliban@redhat.com)
- Merge branch '1.0-dev' (dkliban@redhat.com)
- Merge branch '1.0-testing' into 1.0-dev (dkliban@redhat.com)
- Automatic commit of package [pulp-ostree] release [1.0.0-0.5.beta].
  (dkliban@redhat.com)
- Bumping version to 1.0.0-0.5.beta (dkliban@redhat.com)
- 1.0.0 release notes. (jortel@redhat.com)
- Bumping version to 1.0.0-0.4.beta (dkliban@redhat.com)
- Automatic commit of package [pulp-ostree] release [1.0.0-0.3.beta]. (pulp-
  infra@redhat.com)
- Bumping version to 1.0.0-0.3.beta (dkliban@redhat.com)
- Merge branch '1.0-testing' into 1.0-dev (dkliban@redhat.com)
- Merge branch '1.0-testing' (jortel@redhat.com)
- Require 2015.8 - contains bug fixes and required features.
  (jortel@redhat.com)
- ref #1235 - add provider to shared storage. (jortel@redhat.com)
- Bumps version to 1.1.0 alpha 1 (dkliban@redhat.com)
- Fix docstring. (jortel@redhat.com)
- ref #1178 - support pull all branches. (jortel@redhat.com)
- ref #897 - fetch and store remote summary information in repo scratchpad.
  (jortel@redhat.com)
- ref #876 - convert to mongoengine model. (jortel@redhat.com)
- Merge pull request #40 from jortel/issue-1162 (jortel@redhat.com)
- ref #897 - support listing remote references. (jortel@redhat.com)
- ref #1162 - replace (.) with (-) in commit metadata keys. (jortel@redhat.com)
- mock < 1.1 in test requirements. (jortel@redhat.com)
- formatting fixed. (jortel@redhat.com)
- Merge branch 'master' into ssl-and-gpg-options (jortel@redhat.com)
- Merge branch '1074' (ipanova@redhat.com)
- Merge branch '1096' (ipanova@redhat.com)
- Auto-publish now default to true. (ipanova@redhat.com)
- Deleting an OSTree repo results in a TypeError on the server.
  (ipanova@redhat.com)
- Fix unit tests that fail against Pulp master (jeremy@jcline.org)
- ref #911 - CLI support for SSL and GPG options. (jortel@redhat.com)
- Merge pull request #31 from jortel/issue-912 (jortel@redhat.com)
- ref #912 - support ssl and gpg options. (jortel@redhat.com)


