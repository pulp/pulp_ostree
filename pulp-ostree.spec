%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

# Required platform version
%global platform_version 2.7.0


Name: pulp-ostree
Version: 1.0.0
Release: 0.7.rc%{?dist}
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
mkdir -p %{buildroot}/%{_usr}/lib/pulp/plugins/types
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
cp -R plugins/types/* %{buildroot}/%{_usr}/lib/pulp/plugins/types/

# Remove tests
rm -rf %{buildroot}/%{python_sitelib}/test

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
Requires: pulp-server >= 2.7
Requires: python-setuptools
Requires: ostree >= 2015.8
Requires: python-gnupg
Requires: pygobject3

%description plugins
Provides a collection of platform plugins that extend the Pulp platform
to provide OSTree specific support.

%files plugins
%defattr(-,root,root,-)
%{python_sitelib}/pulp_ostree/plugins/
%config(noreplace) %{_sysconfdir}/httpd/conf.d/pulp_ostree.conf
%config(noreplace) %{_sysconfdir}/pulp/server/plugins.conf.d/ostree_*.json
%{_usr}/lib/pulp/plugins/types/ostree.json
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

